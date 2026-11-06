import asyncio
import datetime
import hashlib
import ipaddress
import os
import re
import socket
import time
import uuid
import types
import traceback
from urllib.parse import urlsplit

from django.apps import apps
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder
from django.core.files.uploadhandler import TemporaryFileUploadHandler
from django.core.signals import setting_changed

from django.utils.datastructures import MultiValueDict
from django.utils.html import escape
from django.utils.translation import gettext as _f
from django.contrib.auth import get_user_model
from channels.generic.websocket import WebsocketConsumer, AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from asgiref.sync import async_to_sync, sync_to_async
import json

from sdc_core.sdc_extentions.models import SdcModel, SDCSerializer, all_models, sanitize_filter_query, resolve_form
from sdc_core.sdc_extentions.response import sdc_link_factory, sdc_link_obj_factory
from sdc_core.sdc_extentions.import_manager import import_function
from sdc_core.sdc_extentions.search import handle_search_form
from sdc_core.sdc_extentions.views import SdcAccessMixin, is_valid_server_call

import logging

logger = logging.getLogger(__name__)
# One JSON record per model request / action round of the AI assistant (see ``SDCAiConsumer._log_metrics``)
metrics_logger = logging.getLogger('sdc_core.ai_metrics')
User = get_user_model()

importlist = []
ALL_MODELS = all_models()


class MsgManager:
    _messages = None
    _msg_filepath = os.path.abspath(settings.BASE_DIR / 'templates/sdc_strings.json')

    @property
    def messages(self):
        if self._messages is None:
            self._messages = {}
            if os.path.exists(self._msg_filepath):
                with open(self._msg_filepath, 'r') as f:
                    self._messages = json.loads(f.read())
            else:
                for model in ALL_MODELS.keys():
                    self._messages[model] = self._get_empty_msg(model)
                self._write_to_file()

        return self._messages

    def get_msg(self, instance, event_type):
        model = instance.__class__.__name__
        if model not in self.messages:
            self._messages[model] = self._get_empty_msg(model)
            self._write_to_file()
        return {key: _f(text).format(instance.__str__()) for key, text in
                self._messages[model].get(event_type, {}).items()}

    def _write_to_file(self):
        if settings.DEBUG:
            with open(self._msg_filepath, 'w+') as f:
                f.write(json.dumps(self._messages))

    def _get_empty_msg(self, model):
        return {'save': {'header': f'{model} saved', 'msg': '{0} was successfully saved'},
                'on_change': {'header': f'{model} was changed', 'msg': '{0} was changed'},
                'create': {'header': f'{model} created', 'msg': '{0} was successfully created'},
                'delete': {'header': f'{model} was deleted', 'msg': '{0} was deleted'}}


class SDCConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        await self.accept()
        self.group_list = []
        self.queryset = None

    async def websocket_disconnect(self, close_code):
        for group in self.group_list:
            await self.channel_layer.group_discard(
                group,
                self.channel_name
            )
        await super().websocket_disconnect(close_code)

    async def state_sdc_event(self, event):
        await self.send(text_data=json.dumps({
            'type': 'sdc_event',
            'event': event.get('event', False),
            'msg': event.get('msg', False),
            'header': event.get('header', False),
            'payload': event.get('payload', False),
            'is_error': False
        }))

    async def state_redirect(self, event):
        if 'controller' in event:
            event['link'] = sdc_link_factory(event.get('controller'), event.get('args'))

        await self.send(text_data=json.dumps({
            'type': 'sdc_redirect',
            'msg': event.get('msg', False),
            'header': event.get('header', False),
            'link': sdc_link_obj_factory(event.get('link', False)),
            'is_error': False
        }))

    async def state_error(self, event, id=None):
        await self.send(text_data=json.dumps({
            'type': 'error',
            'id': id,
            'is_error': True,
            'msg': event.get('msg', ''),
            'header': event.get('header', ''),
        }, cls=DjangoJSONEncoder))

    @staticmethod
    def to_camel_case(snake_str):
        components = snake_str.split('-')
        # We capitalize the first letter of each component except the first one
        # with the 'title' method and join them together.
        return ''.join(x.title() for x in components)

    async def receive(self, text_data=None, bytes_data=None):
        json_data = {}
        try:
            json_data = json.loads(text_data)
            if json_data['event'] == 'sdc_call':
                app_name = json_data['app']
                func_name = json_data['function']
                # Reject client-controlled imports of non-installed apps and any
                # private/framework method name before resolving the controller.
                if not apps.is_installed(app_name) or not is_valid_server_call(func_name):
                    raise PermissionDenied()
                controller_name = self.to_camel_case(json_data['controller'])
                controller = import_function("%s.sdc_views.%s" % (app_name, controller_name))
                c_instance = controller()
                if isinstance(c_instance, SdcAccessMixin):
                    if not await c_instance.async_check_requirements(self.scope['user']):
                        raise PermissionDenied()
                method = getattr(controller(), func_name)

                logger.info(f"SDC call Socket received: {json_data['app']}.{controller_name}.{json_data['function']}")
                if asyncio.iscoroutinefunction(method):
                    return_vals = await method(self, **json_data.get('args', {}))
                else:
                    # Sync methods run in a worker thread, so they may use the Django ORM.
                    return_vals = await sync_to_async(method)(self, **json_data.get('args', {}))

                return_vals_generator = []
                if isinstance(return_vals, types.GeneratorType):
                    return_vals_generator = return_vals
                    return_vals = next(return_vals, None)

                # {'is_error': True, 'msg': ..., 'header': ...} rejects the serverCall promise.
                if isinstance(return_vals, dict) and return_vals.get('is_error'):
                    await self.state_error(return_vals, json_data['id'])
                    return

                await self.send(text_data=json.dumps({
                    'id': json_data['id'],
                    'type': 'sdc_recall',
                    'data': return_vals,
                    'is_error': False
                }, cls=DjangoJSONEncoder))
                for x in return_vals_generator: pass
            else:
                raise ValueError("event must be sdc_call")

        except PermissionDenied:
            await self.state_error({
                'msg': _f('403 Not allowed!'),
                'header': _f('Upps!!')
            }, json_data.get('id'))

        except Exception as e:
            extracted_list = traceback.extract_tb(e.__traceback__)
            e_text = [e.__str__()] + [item for item in traceback.StackSummary.from_list(extracted_list).format()]
            logger.error('\n'.join(e_text))
            if not settings.DEBUG:
                e_text = _f('Something went wrong')
            await self.state_error({
                'msg': e_text,
                'header': _f('Upps!!')
            }, json_data.get('id'))


class SDCModelConsumer(WebsocketConsumer):
    msg_manager = MsgManager()

    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.model_name = None
        self.model = None
        self.queryset = {}
        # Filter of the last full load (connect, load, list_view, named_view). Live updates
        # (on_create) are checked against it, independent of later form or detail requests.
        self.live_query = {}
        # Primary keys of the rows the client has received; on_update/on_delete are only
        # forwarded for these.
        self.ids = []
        self.model_id = None
        self._upload_handler = {}
        self._group_names = []

    def connect(self):
        self.model_name = self.scope['url_route']['kwargs']['model_name']
        # sdc_ws/model/<model_name>/<model_id> restricts the connection to one object.
        model_id = self.scope['url_route']['kwargs'].get('model_id')
        self.model_id = int(model_id) if model_id else None
        self.model = ALL_MODELS.get(self.model_name)
        if self.model is None or not hasattr(self.model, '__is_sdc_model__'):
            raise ValueError(f'{self.model_name} is not a SDC model')
        self.scope["session"]["channel_name"] = self.channel_name
        self.scope["session"].save()
        self.accept()

    def websocket_disconnect(self, close_code):
        try:
            for group in self._group_names:
                async_to_sync(self.channel_layer.group_discard)(group, self.channel_name)
            on_disconnected = getattr(self.model.SdcMeta, 'on_disconnected', None) if self.model else None
            if callable(on_disconnected):
                on_disconnected(self._load_model('disconnect', self.live_query))
        except Exception:
            logger.exception("Error while closing the SDC model connection")
        finally:
            super().websocket_disconnect(close_code)

    def on_update(self, data):
        if data['pk'] in self.ids:
            self.send(text_data=json.dumps(data))

    def on_delete(self, data):
        if data['pk'] in self.ids:
            self.ids.remove(data['pk'])
            self.send(text_data=json.dumps(data))

    def on_create(self, data):
        # Forward only rows the user may see and that match the filter of the last full load.
        try:
            rows = self._load_model('load', self.live_query)
            if hasattr(rows, 'filter'):
                visible = rows.filter(pk=data['pk']).exists()
            else:
                visible = data['pk'] in self._pks(rows)
        except Exception:
            logger.exception("Error while checking a created %s for live updates", self.model_name)
            visible = False
        if visible:
            self._track_ids([data['pk']])
            self.send(text_data=json.dumps(data))

    def state_error(self, event):
        self.send(text_data=json.dumps({
            'type': event.get('type', 'error'),
            'is_error': True,
            'msg': event.get('msg', ''),
            'event_id': event.get('event_id'),
            'header': event.get('header', ''),
        }))

    def receive(self, text_data=None, bytes_data=None):
        msg_type = 'error'
        json_data = {}
        try:
            json_data = json.loads(text_data)
            self.scope['request'] = json_data
            msg_type = json_data.get('event_type', msg_type)
            self.scope['event_type'] = msg_type
            event_type = "%s_%s" % (json_data['event'], json_data['event_type'])
            logger.debug("Socket received: " + event_type)
            self.queryset = json_data['args'].get('model_query', {})
            if not self.model.is_authorised(self.scope['user'], msg_type, self.queryset):
                raise PermissionDenied
            if event_type == 'model_connect':
                self._init_connection(json_data)
            elif event_type == 'model_edit_form':
                self._load_edit_form(json_data)
            elif event_type == 'model_named_form':
                self._load_named_form(json_data)
            elif event_type == 'model_named_view':
                self._load_named_view(json_data)
            elif event_type == 'model_create_form':
                self._load_create_form(json_data)
            elif event_type == 'model_list_view':
                self._load_list_view(json_data)
            elif event_type == 'model_detail_view':
                self._load_detail_view(json_data)
            elif event_type == 'model_save':
                self._save_element(json_data)
            elif event_type == 'model_create':
                self._create_element(json_data)
            elif event_type == 'model_upload':
                self._upload_file(json_data)
            elif event_type == 'model_delete':
                self._delete_element(json_data)
            elif event_type == 'model_load':
                self._load(json_data)
            else:
                raise ValueError(
                    f"{json_data['event']} must be 'model' and {json_data['event_type']} must be in [load, delete, upload, create, save, detail_view, 'connect', 'edit_form', 'create_form', 'list_view']")
        except PermissionDenied as e:
            logger.error("403 Not allowed!")
            self.state_error({
                'type': msg_type,
                'msg': _f('403 Not allowed!'),
                'event_id': json_data.get('event_id'),
                'header': _f('Upps!!')
            })

        except Exception as e:
            extracted_list = traceback.extract_tb(e.__traceback__)
            e_text = [e.__str__()] + [item for item in traceback.StackSummary.from_list(extracted_list).format()]

            if settings.DEBUG:
                logger.error(e_text[0])
                traceback.print_tb(e.__traceback__)
            else:
                logger.error(e_text)
                # Do not leak internal exception details to the client in production.
                e_text = _f('Something went wrong!')

            self.state_error({
                'type': msg_type,
                'msg': e_text,
                'event_id': json_data.get('event_id'),
                'header': _f('Upps!!')
            })

    def _prepare_loaded_data(self, data=None):
        if data is None:
            data = self._load_model()
        model_data = SDCSerializer().serialize(data)
        return {
            'data': model_data,
            'media_url': settings.MEDIA_URL or '/'
        }

    def _add_to_class(self):
        self._group_names.append(self.model_name)
        async_to_sync(self.channel_layer.group_add)(
            self.model_name,
            self.channel_name
        )

    def _load_model(self, event_type=None, query=None):
        """
        Returns the rows for ``query`` (default: the filter of the current message):
        ``get_queryset()`` of the model, filtered with the sanitised query, or the
        result of the model's ``data_load()`` hook if it returns one.
        """
        if event_type is None:
            event_type = self.scope['event_type']
        if query is None:
            query = self.queryset
        clean_query = sanitize_filter_query(self.model, query)
        if self.model_id is not None:
            clean_query['pk'] = self.model_id
        queryset = self.model.get_queryset(self.scope['user'], event_type, query)

        data_load_result = self.model.data_load(self.scope['user'], queryset, clean_query)
        if data_load_result is not None:
            return data_load_result
        return queryset.filter(**clean_query)

    @staticmethod
    def _pks(rows):
        if hasattr(rows, 'values_list'):
            return list(rows.values_list('pk', flat=True))
        return [row.pk for row in rows]

    def _track_ids(self, pks, replace=False):
        """Remembers which rows the client has received (for on_update/on_delete)."""
        if replace:
            self.ids = list(pks)
        else:
            self.ids += [pk for pk in pks if pk not in self.ids]

    def _full_load(self, limit=None):
        """
        Loads with the current filter and makes it the filter for live updates. With ``limit`` only the first
        ``limit`` rows are loaded (and tracked for live updates).
        """
        self.live_query = dict(self.queryset)
        rows = self._load_model()
        if limit is not None:
            rows = rows[:limit]
        self._track_ids(self._pks(rows), replace=True)
        return rows

    @staticmethod
    def _load_limit(json_data):
        """The optional ``limit`` of a load request (``SdcQuerySet.load(query, {limit})``): a positive integer."""
        limit = json_data['args'].get('limit')
        if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 1):
            raise ValueError('limit must be a positive integer')
        return limit

    def _load(self, json_data):
        # queryset.update({item}) loads a single row with {"id": <pk>}: that row is added to
        # the known rows; any other load replaces them and the live filter.
        limit = self._load_limit(json_data)
        if set(self.queryset.keys()) in ({'id'}, {'pk'}):
            rows = self._load_model()
            self._track_ids(self._pks(rows))
        else:
            rows = self._full_load(limit)
        self.send(text_data=json.dumps({
            'type': json_data['event_type'],
            'event_id': json_data['event_id'],
            'args': self._prepare_loaded_data(rows),
            'is_error': False
        }))

    def _init_connection(self, json_data):
        self._full_load()
        self._add_to_class()
        # self.model_description =  {field.name: field.__class__.__name__ for field in self.model._meta.fields}
        self.send(text_data=json.dumps({
            'type': json_data['event_type'],
            'event_id': json_data['event_id'],
            'is_error': False
        }))

    def _load_create_form(self, json_data):
        instance: SdcModel = self.model()
        instance.scope = self.scope
        return self._load_form(json_data, self.model.SdcMeta.create_form, instance)

    def _load_edit_form(self, json_data):
        instance = self._load_model().get(pk=json_data['args']['pk'])
        instance.scope = self.scope
        return self._load_form(json_data, self.model.SdcMeta.edit_form, instance)

    def _load_named_form(self, json_data):
        instance = self._load_model().get(pk=json_data['args']['pk'])
        instance.scope = self.scope
        form_name = json_data['args']['form_name']
        if not hasattr(self.model.SdcMeta, form_name):
            raise NotImplementedError()

        return self._load_form(json_data, getattr(self.model.SdcMeta, form_name), instance)

    def _load_form(self, json_data, form_attr, instance=None):
        form = resolve_form(form_attr)

        self.send(text_data=json.dumps({
            'type': json_data['event_type'],
            'event_id': json_data['event_id'],
            'html': self._render(self.model.SdcMeta.html_form_template,
                                 {'instance': instance, 'form': form(instance=instance)},
                                 json_data),
            'is_error': False
        }))

    def _create_element(self, json_data):
        instance: SdcModel = self.model()
        instance.scope = self.scope
        return self._submit_element(json_data, self.model.SdcMeta.create_form, instance)

    def _save_element(self, json_data):
        instance = self._load_model().get(pk=json_data['args']['pk'])
        instance.scope = self.scope
        key = str(json_data['args'].get('form_name', 'edit_form'))
        if not hasattr(self.model.SdcMeta, key):
            key = 'edit_form'
        form_element = getattr(self.model.SdcMeta, key)
        return self._submit_element(json_data, form_element, instance)

    def _upload_file(self, json_data):
        file_data = json_data['args']
        if json_data['event_id'] in self._upload_handler:
            (handler, number_of_chunks) = self._upload_handler.get(json_data['event_id'])
        else:
            (handler, number_of_chunks) = (TemporaryFileUploadHandler(), int(file_data['number_of_chunks']))

            handler.new_file(file_name=file_data['file_name'],
                             field_name=file_data['field_name'],
                             content_type=file_data['content_type'],
                             content_length=file_data['content_length'], )
        if isinstance(file_data['chunk'], list):
            data = bytes(file_data['chunk'])
        else:
            data = file_data['chunk'].encode()
        handler.receive_data_chunk(data, int(file_data['idx']))
        number_of_chunks = number_of_chunks - 1
        self._upload_handler[json_data['event_id']] = (handler, number_of_chunks)
        if number_of_chunks == 0:
            handler.upload_complete()
            self.send(text_data=json.dumps({
                'type': json_data['event_type'],
                'event_id': json_data['event_id'],
                'is_error': False
            }))

    def _submit_element(self, json_data, form_attr, instance=None):
        data = json_data['args']['data']
        files = json_data['args'].get('files')
        form = resolve_form(form_attr)
        uploads = MultiValueDict()
        if files is not None:
            for (key, val) in files.items():
                uploads[key] = self._upload_handler[val['id']][0].file_complete(val['content_length'])
                del self._upload_handler[val['id']]

        form_instance = form(instance=instance, data=data, files=uploads)
        is_valid = form_instance.is_valid()
        new_instance = None

        if is_valid:
            form_instance.save()
            new_instance = SDCSerializer().serialize(self._load_model().filter(pk=form_instance.instance.pk))
            self._track_ids([form_instance.instance.pk])
            msg = self.msg_manager.get_msg(form_instance.instance, json_data['event_type'])
        else:
            msg = {'header': 'Upss!',
                   'msg': "<ul>%s</ul>" % "\n".join(
                       ["<li>%s: %s</li>" % (escape(k), escape(v[0])) for k, v in form_instance.errors.items()])
                   }

        self.send(text_data=json.dumps(msg | {
            'type': json_data['event_type'],
            'event_id': json_data['event_id'],
            'data': {'instance': new_instance},
            'html': self._render(self.model.SdcMeta.html_form_template,
                                 {'instance': form_instance.instance, 'form': form_instance},
                                 json_data),
            'is_error': not is_valid
        }))

    def _load_list_view(self, json_data):
        if self.model.SdcMeta.html_list_template is None:
            raise NotImplementedError()
        filter = self.queryset.pop('__search_values', {})
        loaded_data = self._full_load()
        self.send(text_data=json.dumps({
            'type': json_data['event_type'],
            'event_id': json_data['event_id'],
            'html': self._render(self.model.SdcMeta.html_list_template, {'instances': loaded_data, 'filter': filter}, json_data),
            'args': self._prepare_loaded_data(loaded_data),
            'is_error': False
        }))

    def _load_named_view(self, json_data):
        loaded_data = self._full_load()
        view_name = json_data['args']['view_name']
        if not hasattr(self.model.SdcMeta, view_name):
            text = f'"{view_name}" is not implemented in "{loaded_data.__class__.__name__}.SdcMeta".'
            raise Exception(text)
        self.send(text_data=json.dumps({
            'type': json_data['event_type'],
            'event_id': json_data['event_id'],
            'html': self._render(getattr(self.model.SdcMeta, view_name), {'instances': loaded_data}, json_data),
            'args': self._prepare_loaded_data(loaded_data),
            'is_error': False
        }))

    def _load_detail_view(self, json_data):
        if self.model.SdcMeta.html_detail_template is None:
            raise NotImplementedError()
        instance = self._load_model().get(pk=json_data['args']['pk'])
        instance.scope = self.scope
        self._track_ids([instance.pk])
        self.send(text_data=json.dumps({
            'type': json_data['event_type'],
            'event_id': json_data['event_id'],
            'html': self._render(self.model.SdcMeta.html_detail_template, {'instance': instance}, json_data),
            'args': self._prepare_loaded_data([instance]),
            'is_error': False
        }))

    def _delete_element(self, json_data):
        instance = self._load_model().get(pk=json_data['args']['pk'])
        instance.scope = self.scope
        instance.delete()
        self.send(text_data=json.dumps({
            'type': json_data['event_type'],
            'event_id': json_data['event_id'],
            'is_error': False
        }))

    def _render(self, template_name, context: dict, json_data: dict):
        context = self.scope | json_data.get('args', {}) | context
        return self.model.render(template_name, context)


# Claude models that accept the server-side refusal fallback `fallbacks: "default"`
AI_FALLBACK_MODELS = {'claude-fable-5-1', 'claude-opus-5-5', 'claude-opus-5', 'claude-sonnet-5-5'}
# Rounds of client actions per answer (default of ``SDC_AI_MAX_ACTION_ROUNDS``); after that the model has to answer
# without further actions
AI_MAX_ACTION_ROUNDS = 5
# Values a user may choose in the assistant's settings menu (``set_config``)
AI_PROVIDERS = ('anthropic', 'openai-compatible')
AI_EFFORTS = ('low', 'medium', 'high', 'xhigh', 'max')
AI_MAX_TOKENS_LIMIT = 128000
# Knowledge about the website in the system prompt (``SDC_AI_SKILL_SOURCE``): 'auto' = the skill file
# (``SDC_AI_SKILL_FILE``) if it exists, else the apps' SDC_SKILL.json; 'full' = only the skill file (an error if it
# is missing); 'apps' = only the apps' SDC_SKILL.json; 'none' = no knowledge (e.g. as baseline of an evaluation)
AI_SKILL_SOURCES = ('auto', 'full', 'apps', 'none')
# Added to the system prompt instead of the knowledge if there is none (``SDC_AI_NO_SKILL_NOTE``, '' disables it):
# the default prompt refers to a context below
AI_NO_SKILL_NOTE = ('No generated description of the views and data models of this website is available. Explore '
                    'it with `read_page` and the links on the page.')


def round_ms(seconds):
    return int(round(seconds * 1000))


class AiConfigError(ValueError):
    """An invalid value in the user's AI settings; the message is shown to the user."""


# System prompt of the assistant, built once per process (see ``SDCAiConsumer._cached_system_prompt``)
_ai_system_prompt = None


def _ai_reset_system_prompt(**kwargs):
    global _ai_system_prompt
    _ai_system_prompt = None


# Tests that override settings get a new prompt
setting_changed.connect(_ai_reset_system_prompt)


async def _ai_public_addresses(host, port):
    """
    Resolves ``host`` and returns its addresses; raises ``AiConfigError`` if it cannot be resolved or any of its
    addresses is not a public internet address (loopback, private networks, link-local incl. cloud metadata, ...).
    """
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError):
        raise AiConfigError(_f('The host of the API URL cannot be resolved.'))
    addresses = []
    for info in infos:
        address = info[4][0].split('%')[0]
        if not ipaddress.ip_address(address).is_global:
            raise AiConfigError(_f('The API URL must point to a public internet address.'))
        addresses.append(address)
    if not addresses:
        raise AiConfigError(_f('The host of the API URL cannot be resolved.'))
    return addresses


async def _ai_check_public_url(url):
    """
    Raises ``AiConfigError`` unless ``url`` is https and its host resolves only to public addresses. The server
    sends the requests (incl. the API key) to this URL, so it must not reach internal services (SSRF).
    This check gives the user an early error when saving the settings; the requests themselves go through
    ``_ai_public_http_client``, which checks the addresses again on every connection (DNS may change).
    """
    parts = urlsplit(url)
    if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password:
        raise AiConfigError(_f('The API URL must be an https URL without credentials.'))
    await _ai_public_addresses(parts.hostname, parts.port or 443)


def _ai_public_http_client(timeout):
    """
    HTTP client (``httpx2``, used by the anthropic and openai SDKs) for API URLs entered by users: every new
    connection resolves the host, rejects non-public addresses and connects to exactly the checked address, so a
    host whose DNS answer changes after ``_ai_check_public_url`` (DNS rebinding) cannot reach internal services.
    TLS still verifies the certificate of the host name. No proxies from the environment, no redirects.
    """
    import httpcore2
    import httpx2

    class PublicOnlyBackend(httpcore2.AsyncNetworkBackend):
        def __init__(self, backend=None):
            self.backend = backend or httpcore2.AnyIOBackend()

        async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
            try:
                addresses = await _ai_public_addresses(host, port)
            except AiConfigError as e:
                raise httpcore2.ConnectError(str(e))
            return await self.backend.connect_tcp(addresses[0], port, timeout=timeout,
                                                  local_address=local_address, socket_options=socket_options)

        async def connect_unix_socket(self, path, timeout=None, socket_options=None):
            raise httpcore2.ConnectError('Unix sockets are not allowed')

        async def sleep(self, seconds):
            await self.backend.sleep(seconds)

    transport = httpx2.AsyncHTTPTransport(trust_env=False)
    # httpx2 has no option for the network backend: replace the transport's pool with one that uses it
    transport._pool = httpcore2.AsyncConnectionPool(ssl_context=httpx2.create_ssl_context(),
                                                    network_backend=PublicOnlyBackend())
    return httpx2.AsyncClient(transport=transport, timeout=timeout, follow_redirects=False, trust_env=False)


def _ai_origin_allowed(scope):
    """
    False if the WebSocket was opened by a page of another site: browsers always send ``Origin``, and it must
    match ``ALLOWED_HOSTS`` (like ``channels.security.websocket.AllowedHostsOriginValidator``). Otherwise any page
    could use the assistant with the visitor's session (and the server's API key). Connections without
    ``Origin`` (no browser, so no session cookie of a victim) are allowed.
    """
    from channels.security.websocket import OriginValidator
    from urllib.parse import urlparse
    origin = next((value for name, value in scope.get('headers', []) if name == b'origin'), None)
    if origin is None:
        return True
    allowed_hosts = settings.ALLOWED_HOSTS or (['localhost', '127.0.0.1', '[::1]'] if settings.DEBUG else [])
    try:
        return OriginValidator(None, allowed_hosts).validate_origin(urlparse(origin.decode('latin1')))
    except ValueError:
        return False


class AiLimitError(Exception):
    """The user reached ``SDC_AI_MAX_REQUESTS_PER_USER``."""

AI_DEFAULT_SYSTEM_PROMPT = """You are the assistant of this website and help the user to use it. The website is built \
with SimpleDomControl (SDC); its documentation is at https://simpledomcontrol.readthedocs.io/en/latest/ - point the \
user there for questions about the framework itself.

Your knowledge about this website comes from the context below: its views (controllers), how to navigate between them \
and its data models (SdcModels).

You can act on the page with your tools. They run in the user's browser with the user's own permissions:
- `navigate` opens a view, using the `/~view~child~&key=value` paths ("How to read SDC URLs" in the context).
- `read_page` returns an outline of the current page: its text with `[#id label]` for buttons and links, its \
lists (first rows, total, search form and next/prev buttons), forms with their fields and current values, and its \
buttons and links (`elements`) with the resolved target of every SDC link. Ask for `mode: "html"` only for one \
part (`scope`), and for more rows of a list with `scope` and `rows`.
- `fill_form` enters values into the fields of a form of the current page. It does not submit or save the form. \
Fields that update their view on change (`updates_on_change`, e.g. the search bar of a list) filter the list at once.
- When the result of `navigate`, `click` or `fill_form` contains `page`, it is the outline of the page afterwards: \
use it instead of calling `read_page` again.
- `click` presses a button or link of the current page, like the user. Form submit buttons and links that leave the \
app cannot be clicked. Buttons that may delete, save or send data (`needs_confirmation`) are only clicked after the \
user allowed it in the chat.
- `model_get` and `model_load` read SdcModel records. There are no tools to create, change or delete records.

Rules:
- Answer briefly in the user's language. Say what you did after you used a tool.
- Only use views, arguments, models and fields that appear in the context or on the page. If something is not there, \
say so instead of guessing.
- Read the page before you answer questions about it or fill a form; load records before you answer questions about data.
- A form with the attributes `SdcModelName` and `SdcModelPK` edits a record of that SdcModel (`SdcModelPK` -1: a new \
record). To create or change records, navigate to the right form, fill it and ask the user to check the values and \
submit or save it.
- Only enter values the user asked for or clearly agreed to, never passwords.
- Only click buttons that the user's request needs. The context describes what buttons do ("Buttons", "Button \
actions"); if a button's effect is unknown, ask before clicking it. Read the page again after a click.
- To search a list, fill its search bar with `fill_form` and read the page; use the list's "Next"/"Prev" buttons to \
page through the results.
- If a tool returns an error, explain it to the user and do not retry the same call more than once."""

_AI_MODEL = {'type': 'string', 'description': 'Name of the SdcModel, as listed in the context'}
_AI_ID = {'type': 'integer', 'description': 'Primary key (id) of the record'}
# Client tools: the server forwards the calls to the browser, which runs them and sends the results back.
# SdcModels are read-only for the assistant: there are no tools to create, change or delete records.
AI_TOOLS = [
    {'name': 'navigate',
     'description': 'Open a view of this website in the browser, e.g. "/~main-view~book-edit~&pk=3". Paths and '
                    'arguments follow the SDC navigation rules described in the context; ".." goes one view up.',
     'input_schema': {'type': 'object', 'additionalProperties': False, 'required': ['path'],
                      'properties': {'path': {'type': 'string', 'description': 'SDC path, starting with "/~", or '
                                              'relative to the current path (".", "..", "..~view")'}}}},
    {'name': 'read_page',
     'description': 'Read the current page. Default: an outline - URL, title, the visible text with one line per '
                    'block ("## " before headings, "[#<id> label]" for buttons and links), lists, forms and '
                    'elements. Lists (tables and repeated rows) are summarised: rows_in_page, the first 20 rows '
                    '(text and their buttons/links) and, for lists with a search bar, search {form, range, total, '
                    'next, prev}. Forms: id, SdcModelName/SdcModelPK of SdcModel forms, fields with name, type, '
                    'label, current value and options; fields outside a <form> are one extra form per view '
                    '(form_element false, controller tag; updates_on_change for search bars). Elements: id, kind, '
                    'text, controller, href of links resolved by the sdc-navigator, sdc_click handlers, '
                    'needs_confirmation, clickable false with a reason. Ids stay the same while the element is on '
                    'the page. Password values are never returned.',
     'input_schema': {'type': 'object', 'additionalProperties': False, 'properties': {
         'mode': {'type': 'string', 'enum': ['outline', 'html'],
                  'description': '"outline" (default) or "html": also the simplified HTML (large; use it with a '
                                 'scope)'},
         'scope': {'type': ['integer', 'string'],
                   'description': 'Only this part of the page: the id of an element, form or list, or a controller '
                                  'tag'},
         'rows': {'type': 'array', 'items': {'type': 'integer'}, 'minItems': 2, 'maxItems': 2,
                  'description': '[from, to] (1-based): the rows of the lists to show, e.g. [21, 40]'}}}},
    {'name': 'fill_form',
     'description': 'Enter values into the fields of a form of the current page (input, textarea, select, '
                    'checkbox, radio), like the user typing them. The form is not submitted and nothing is saved. '
                    'Passwords, hidden and file fields cannot be filled. Returns the values that were set.',
     'input_schema': {'type': 'object', 'additionalProperties': False, 'required': ['form', 'values'],
                      'properties': {
                          'form': {'type': 'integer', 'description': 'Id of the form as returned by read_page '
                                                                     '(forms[].id)'},
                          'values': {'type': 'object', 'description': 'Field name -> value; true/false for '
                                     'checkboxes, the option value or text for selects and radios, a list for '
                                     'multiple selects'}}}},
    {'name': 'click',
     'description': 'Click a button or link of the current page like the user: SDC links open the view, buttons '
                    'run their action (e.g. "Next" of a search bar, opening a modal). Submit buttons of forms and '
                    'links leaving the app cannot be clicked; buttons that may delete, save or send data are only '
                    'clicked if the user allows it in the chat. Returns the URL afterwards; use read_page to see '
                    'the result.',
     'input_schema': {'type': 'object', 'additionalProperties': False, 'required': ['element'],
                      'properties': {
                          'element': {'type': 'integer', 'description': 'Id of the element as returned by read_page '
                                                                        '(elements[].id)'},
                          'text': {'type': 'string', 'description': 'Optional: the text of the element as read; the '
                                                                    'click is refused if the element changed'}}}},
    {'name': 'model_get',
     'description': 'Read one record of an SdcModel by its id, if the user is allowed to see it.',
     'input_schema': {'type': 'object', 'additionalProperties': False, 'required': ['model', 'id'],
                      'properties': {'model': _AI_MODEL, 'id': _AI_ID}}},
    {'name': 'model_load',
     'description': 'Load records of an SdcModel that the user is allowed to see. Returns at most 50 records.',
     'input_schema': {'type': 'object', 'additionalProperties': False, 'required': ['model'],
                      'properties': {'model': _AI_MODEL,
                                     'filter': {'type': 'object', 'description': 'Django field lookups, '
                                                'e.g. {"author__name": "Jane"}; omit to load all records'}}}},
]
_AI_JSON_TYPES = {'string': str, 'integer': int, 'object': dict, 'array': list}


def _ai_type_ok(value, json_type):
    """``value`` matches the JSON schema ``type`` (a name or a list of names); booleans are no integers."""
    types = json_type if isinstance(json_type, list) else [json_type]
    return not isinstance(value, bool) and any(isinstance(value, _AI_JSON_TYPES[t]) for t in types)


def _ai_tool_input_error(name, tool_input):
    """Validates a tool call against ``AI_TOOLS`` (inputs may arrive truncated while streaming); None if valid."""
    tool = next((t for t in AI_TOOLS if t['name'] == name), None)
    if tool is None:
        return f'Unknown tool {name}'
    if not isinstance(tool_input, dict):
        return 'INVALID_JSON: the tool input is not a JSON object'
    schema = tool['input_schema']
    # Tools without arguments (read_page) have no 'required' list
    missing = [k for k in schema.get('required', []) if k not in tool_input]
    unknown = [k for k in tool_input if k not in schema['properties']]
    wrong = [k for k, v in tool_input.items()
             if k in schema['properties'] and not _ai_type_ok(v, schema['properties'][k]['type'])]
    if missing or unknown or wrong:
        return f'INVALID_JSON: missing {missing}, unknown {unknown}, wrong type {wrong}'
    return None


def _ai_resolve_model(name, tool_input):
    """
    ``model_get`` / ``model_load``: replaces the model name with the exact name of the SdcModel (names are matched
    case-insensitively, ``author`` -> ``Author``). Returns an error text for an unknown model, else None. Without
    this, the browser would wait for a model WebSocket that is never opened.
    """
    if name not in ('model_get', 'model_load'):
        return None
    model = ALL_MODELS.get(tool_input['model'])
    if model is None:
        return (f'Unknown SdcModel "{tool_input["model"]}". Available models: '
                f'{", ".join(sorted(m.__name__ for m in ALL_MODELS.values()))}')
    tool_input['model'] = model.__name__
    return None


class SDCAiConsumer(AsyncWebsocketConsumer):
    """
    WebSocket of the ``<sdc-ai-assistant>``: receives prompts from the user and streams the model's answer.

    Client -> server (JSON):

    - ``{"event": "prompt", "id": <id>, "prompt": "..."}``: ask; the conversation is kept per connection
    - ``{"event": "set_config", "provider", "token", "base_url", "model", "effort", "max_tokens"}``: the user's
      own connection settings (all optional; empty = project setting), only if ``SDC_AI_TOKEN_FROM_SYSTEM`` is
      False. Kept in memory for this connection only; a new provider starts a new conversation. ``base_url`` must be https and resolve to a public address, and is only
      accepted with ``SDC_AI_ALLOW_USER_BASE_URL``.
    - ``{"event": "reset"}``: forget the conversation
    - ``{"event": "action_results", "id": <id>, "results": [{"tool_use_id", "content", "is_error"}]}``: the
      outcome of the actions of an ``ai_actions`` message, one result per action

    Server -> client: ``{"type": "ai_config", ...}`` after connecting and after ``set_config``: the connection
    settings in use and what the user may change (never the key itself).
    ``{"type": "ai_delta", "id", "text"}`` while the answer is generated. If the model wants to
    act on the page: ``{"type": "ai_actions", "id", "text", "actions": [{"tool_use_id", "name", "input"}]}``
    (tools in ``AI_TOOLS``); the client runs them in order and replies with ``action_results``, then the answer
    continues. It ends with ``{"type": "ai_answer", "id", "text", "stop_reason"}``. Errors as
    ``{"type": "error", "id", "msg", ...}`` like ``SDCConsumer``; an error after ``ai_delta`` messages means the
    partial answer must be discarded.

    The system prompt is the ``AI_DEFAULT_SYSTEM_PROMPT`` setting (default: ``AI_DEFAULT_SYSTEM_PROMPT`` of this
    module) followed by the skill file of the project (``SDC_SKILL.md`` written by ``sdc_teach``, else the apps'
    ``SDC_SKILL.json``) and the files of ``SDC_AI_ADDITIONAL_SKILL_FILE`` (one path or a list; relative to
    ``BASE_DIR``), e.g. hand-written knowledge about the project. ``SDC_AI_SKILL_SOURCE`` (see
    ``AI_SKILL_SOURCES``) and ``SDC_AI_SKILL_FILE`` select the knowledge; without any, ``SDC_AI_NO_SKILL_NOTE`` is
    used instead.

    With ``SDC_AI_METRICS_FILE`` (JSON lines) or ``SDC_AI_METRICS = True`` (logger ``sdc_core.ai_metrics``) every
    model request and every round of action results is recorded: duration, token usage, tool calls and a hash of
    the system prompt, e.g. to evaluate the assistant (``manage.py sdc_eval_ai``).
    """

    async def connect(self):
        await self.accept()
        self.messages = []
        # The user's own connection settings (set_config): provider, token, base_url, model, effort, max_tokens
        self.config = {}
        self.client = None
        self.system_prompt = None
        # Index in ``messages`` where the current answer's turn starts (to drop it on errors/refusals)
        self.turn_start = 0
        # All text the model wrote in the current turn (it may be spread over several action rounds)
        self.turn_text = ''
        # Actions sent to the client and not answered yet: {'id', 'round', 'tool_use_ids', 'results'}
        self.pending = None
        # Identifies the connection in the metrics log
        self.connection_id = uuid.uuid4().hex
        if not _ai_origin_allowed(self.scope):
            await self.close(code=4403)
            return
        error = await self._access_error()
        if error:
            await self.state_error({'msg': error, 'header': _f('AI assistant')})
            await self.close(code=4403)
            return
        await self._send_config()

    @staticmethod
    def _setting(name, default=None):
        return getattr(settings, name, default)

    @classmethod
    def _max_action_rounds(cls):
        rounds = cls._setting('SDC_AI_MAX_ACTION_ROUNDS', AI_MAX_ACTION_ROUNDS)
        if not isinstance(rounds, int) or isinstance(rounds, bool) or rounds < 0:
            raise ImproperlyConfigured('SDC_AI_MAX_ACTION_ROUNDS must be a non-negative integer')
        return rounds

    def _config(self, key):
        """A connection setting: the user's own value (``set_config``) or the project's ``SDC_AI_<KEY>``."""
        defaults = {'provider': 'anthropic', 'model': 'claude-opus-5-5', 'max_tokens': 16000, 'effort': '',
                    'base_url': ''}
        value = self.config.get(key)
        return value if value not in (None, '') else self._setting(f'SDC_AI_{key.upper()}', defaults[key])

    def _uses_system_token(self):
        return self._setting('SDC_AI_TOKEN_FROM_SYSTEM', False)

    async def _send_config(self):
        editable = not self._uses_system_token()
        await self.send(text_data=json.dumps({
            'type': 'ai_config',
            'editable': editable,
            'allow_base_url': editable and bool(self._setting('SDC_AI_ALLOW_USER_BASE_URL', True)),
            'provider': self._config('provider'),
            'providers': list(AI_PROVIDERS) if editable else [],
            'model': self._config('model'),
            'effort': self._config('effort'),
            'max_tokens': self._config('max_tokens'),
            # The project's own URL (e.g. an internal proxy) is not shown to users
            'base_url': self.config.get('base_url', ''),
            'has_token': bool(self.config.get('token')) or not editable,
            # navigate, click and fill_form return the outline of the changed page (saves a read_page round)
            'page_in_results': bool(self._setting('SDC_AI_PAGE_IN_RESULTS', True)),
            'is_error': False,
        }))

    async def _set_config(self, data):
        if self._uses_system_token():
            raise PermissionDenied()
        config = {}
        provider = str(data.get('provider') or '').strip()
        if provider:
            if provider not in AI_PROVIDERS:
                raise AiConfigError(_f('Provider must be one of %(providers)s.') % {'providers': ', '.join(AI_PROVIDERS)})
            config['provider'] = provider
        token = str(data.get('token') or '').strip()
        if token:
            config['token'] = token
        elif self.config.get('token') and not data.get('clear_token'):
            config['token'] = self.config['token']  # an empty field keeps the key that is already set
        model = str(data.get('model') or '').strip()
        if model:
            if len(model) > 100 or not re.fullmatch(r'[\w.:@/-]+', model):
                raise AiConfigError(_f('Invalid model name.'))
            config['model'] = model
        effort = str(data.get('effort') or '').strip()
        if effort:
            if effort not in AI_EFFORTS:
                raise AiConfigError(_f('Effort must be one of %(efforts)s.') % {'efforts': ', '.join(AI_EFFORTS)})
            config['effort'] = effort
        if data.get('max_tokens') not in (None, ''):
            try:
                max_tokens = int(data['max_tokens'])
            except (TypeError, ValueError):
                max_tokens = 0
            if not 1 <= max_tokens <= AI_MAX_TOKENS_LIMIT:
                raise AiConfigError(_f('Max tokens must be between 1 and %(max)s.') % {'max': AI_MAX_TOKENS_LIMIT})
            config['max_tokens'] = max_tokens
        base_url = str(data.get('base_url') or '').strip()
        if base_url:
            if not self._setting('SDC_AI_ALLOW_USER_BASE_URL', True):
                raise AiConfigError(_f('Changing the API URL is not allowed.'))
            await _ai_check_public_url(base_url)
            config['base_url'] = base_url
        if config.get('provider', self._setting('SDC_AI_PROVIDER', 'anthropic')) != self._config('provider'):
            # The conversation is stored in the provider's message format: a new provider starts a new conversation
            self.messages = []
            self.pending = None
        self.config = config
        await self._close_client()
        await self._send_config()

    async def _close_client(self):
        """Closes the provider client (its HTTP connections); the next request creates a new one."""
        client, self.client = getattr(self, 'client', None), None
        if client is not None and hasattr(client, 'close'):
            try:
                await client.close()
            except Exception:
                logger.warning('AI assistant: closing the provider client failed', exc_info=True)

    async def disconnect(self, code):
        await self._close_client()

    async def _access_error(self):
        if not self._setting('SDC_AI_ASSISTANT', False):
            return _f('The AI assistant is disabled.')
        if self._setting('SDC_AI_PROVIDER', 'anthropic') not in AI_PROVIDERS:
            return _f('AI provider %(provider)s is not supported yet.') % {'provider': self._setting('SDC_AI_PROVIDER')}
        user = self.scope.get('user')
        # The system's key must never be used anonymously
        if (self._setting('SDC_AI_REQUIRE_LOGIN', True) or self._uses_system_token()) and \
                not (user and user.is_authenticated):
            return _f('Please log in to use the AI assistant.')
        if not await self._in_allowed_group(user):
            return _f('403 Not allowed!')
        return None

    @database_sync_to_async
    def _in_allowed_group(self, user):
        groups = self._setting('SDC_AI_ALLOWED_GROUPS')
        if not groups:
            return True
        if not (user and user.is_authenticated):
            return False
        return user.is_staff or user.is_superuser or user.groups.filter(name__in=groups).exists()

    async def state_error(self, event, id=None):
        await self.send(text_data=json.dumps({
            'type': 'error',
            'id': id,
            'is_error': True,
            'msg': event.get('msg', ''),
            'header': event.get('header', ''),
            # 'settings': rejected set_config values, 'token': an API key is needed (independent of translations)
            'scope': event.get('scope'),
        }, cls=DjangoJSONEncoder))

    async def receive(self, text_data=None, bytes_data=None):
        json_data = {}
        try:
            data = json.loads(text_data or '')
            if not isinstance(data, dict):
                raise ValueError('A message must be a JSON object')
            json_data = data
            event = json_data.get('event')
            if event == 'prompt':
                await self._answer(json_data.get('id'), str(json_data.get('prompt', '')).strip())
            elif event == 'set_config':
                await self._set_config(json_data)
            elif event == 'action_results':
                await self._action_results(json_data.get('id'), json_data.get('results'))
            elif event == 'reset':
                self.messages = []
                self.pending = None
            else:
                raise ValueError('event must be prompt, action_results, set_config or reset')
        except PermissionDenied:
            await self.state_error({'msg': _f('403 Not allowed!'), 'header': _f('Upps!!')}, json_data.get('id'))
        except AiConfigError as e:
            await self.state_error({'msg': str(e), 'header': _f('AI settings'), 'scope': 'settings'},
                                   json_data.get('id'))
        except AiLimitError:
            await self.state_error({'msg': _f('You have reached the daily limit of AI requests.'),
                                    'header': _f('AI assistant')}, json_data.get('id'))
        except Exception as e:
            logger.error('AI assistant: ' + ''.join(traceback.format_exception(e)))
            provider_msg = self._provider_error_message(e)
            if provider_msg:
                # The user's own settings are the likely cause: the settings menu opens again
                scope = None if self._uses_system_token() else 'settings'
                await self.state_error({'msg': provider_msg, 'header': _f('AI service'), 'scope': scope},
                                       json_data.get('id'))
                return
            msg = str(e) if settings.DEBUG else _f('Something went wrong')
            await self.state_error({'msg': msg, 'header': _f('Upps!!')}, json_data.get('id'))

    def _provider_error_message(self, e):
        """A readable message for errors of the provider SDKs (anthropic, openai); None for other errors."""
        if type(e).__module__.split('.')[0] not in ('anthropic', 'openai'):
            return None
        status = getattr(e, 'status_code', None)
        if self._uses_system_token():
            # Users must not learn the project's (possibly internal) API URL
            return _f('The AI service is not available at the moment (error %(status)s).') % {
                'status': status or _f('no connection')}
        request = getattr(e, 'request', None) or getattr(getattr(e, 'response', None), 'request', None)
        where = f' ({request.method} {request.url})' if request is not None else ''
        if status is None:
            return _f('The AI service could not be reached%(where)s. Please check the API URL.') % {'where': where}
        hints = {401: _f('Please check the API key.'), 403: _f('Please check the API key.'),
                 404: _f('Please check the provider, API URL and model.'),
                 405: _f('The API URL does not offer the API of the selected provider. Please check the provider '
                         'and the API URL.')}
        detail = getattr(e, 'message', '') or ''
        return _f('The AI service answered %(status)s%(where)s: %(detail)s %(hint)s') % {
            'status': status, 'where': where, 'detail': detail,
            'hint': hints.get(status, _f('Please check the AI settings.'))}

    # ---------------------------------------------------------------- answer
    async def _answer(self, id, prompt):
        if not prompt:
            return
        if not self._uses_system_token() and not self.config.get('token'):
            await self.state_error({'msg': _f('Please enter your API key first.'), 'header': _f('AI assistant'),
                                    'scope': 'token'}, id)
            return

        if self.pending:
            # Unanswered actions of the previous answer are cancelled, so every tool use keeps its result. They
            # belong to the previous turn (Anthropic joins the two consecutive user messages).
            self._append_tool_results(cancelled=True)
        self.turn_start = len(self.messages)
        self.turn_text = ''
        self.messages.append({'role': 'user', 'content': prompt})
        await self._run(id, round=0)

    async def _run(self, id, round):
        """Streams one model response of the current turn; ends the turn or sends its actions to the client."""
        started = time.monotonic()
        try:
            result = await self._stream(id, final=round >= self._max_action_rounds())
        except Exception as e:
            self._drop_turn()
            await self._log_request(id, round, started, error=f'{type(e).__name__}: {e}')
            raise
        await self._log_request(id, round, started, result=result)
        if result['stop'] == 'refusal' or (result['tool_uses'] and result['stop'] != 'tool_use'):
            # A declined or truncated answer is not kept: the conversation continues from before the prompt
            self._drop_turn()
            msg = _f('The assistant declined to answer this request.') if result['stop'] == 'refusal' \
                else _f('The answer was too long. Please ask for less at once.')
            await self.state_error({'msg': msg, 'header': _f('AI assistant')}, id)
            return
        self.messages.append(result['message'])
        self.turn_text += result['text']
        if not result['tool_uses']:
            await self.send(text_data=json.dumps({
                'type': 'ai_answer',
                'id': id,
                'text': self.turn_text,
                'stop_reason': result['stop'],
                'is_error': False,
            }))
            return

        # Invalid calls (e.g. truncated while streaming) are answered here; the client only runs valid ones
        self.pending = {'id': id, 'round': round, 'tool_use_ids': [t['id'] for t in result['tool_uses']],
                        'results': {}}
        actions = []
        for tool_use in result['tool_uses']:
            error = (_ai_tool_input_error(tool_use['name'], tool_use['input'])
                     or _ai_resolve_model(tool_use['name'], tool_use['input']))
            if error:
                self.pending['results'][tool_use['id']] = {'content': error, 'is_error': True}
            else:
                actions.append({'tool_use_id': tool_use['id'], 'name': tool_use['name'], 'input': tool_use['input']})
        if not actions:
            await self._continue()
            return
        await self.send(text_data=json.dumps({
            'type': 'ai_actions', 'id': id, 'text': result['text'], 'actions': actions, 'is_error': False,
        }, cls=DjangoJSONEncoder))

    async def _action_results(self, id, results):
        if not self.pending or id != self.pending['id']:
            # Late results of actions that a new prompt cancelled (or a confused client): nothing to continue
            logger.debug(f'AI assistant: ignored action_results for request {id!r}')
            return
        missing = set(self.pending['tool_use_ids']) - set(self.pending['results'])
        results = {r.get('tool_use_id'): r for r in results or [] if isinstance(r, dict)}
        if set(results) != missing:
            raise ValueError('action_results must contain exactly one result per action')
        for tool_use_id, result in results.items():
            self.pending['results'][tool_use_id] = {'content': result.get('content'),
                                                    'is_error': bool(result.get('is_error'))}
        if self._metrics_enabled():
            await self._log_metrics({'type': 'action_results', 'request_id': id, 'round': self.pending['round'],
                                     'results': [{'tool_use_id': k, 'is_error': bool(r.get('is_error')),
                                                  'content_chars': len(r['content']) if isinstance(
                                                      r.get('content'), str) else len(json.dumps(
                                                      r.get('content'), cls=DjangoJSONEncoder, default=str))}
                                                 for k, r in results.items()]})
        await self._continue()

    async def _continue(self):
        """Appends the results of the pending actions and lets the model continue its answer."""
        id, round = self.pending['id'], self.pending['round']
        self._append_tool_results()
        await self._run(id, round + 1)

    def _append_tool_results(self, cancelled=False):
        """Adds one result per pending tool use to the conversation (in the provider's format)."""
        results = []
        for tool_use_id in self.pending['tool_use_ids']:
            result = self.pending['results'].get(tool_use_id)
            if cancelled or result is None:
                result = {'content': 'Cancelled: the user sent a new message instead.', 'is_error': True}
            content = result['content']
            if not isinstance(content, str):
                content = json.dumps(content, cls=DjangoJSONEncoder, ensure_ascii=False)
            results.append((tool_use_id, content, result['is_error']))
        self.pending = None
        if self._config('provider') == 'openai-compatible':
            # OpenAI has no error flag: errors are marked in the text
            self.messages += [{'role': 'tool', 'tool_call_id': tool_use_id,
                               'content': f'Error: {content}' if is_error else content}
                              for tool_use_id, content, is_error in results]
        else:
            self.messages.append({'role': 'user', 'content': [
                {'type': 'tool_result', 'tool_use_id': tool_use_id, 'is_error': is_error, 'content': content}
                for tool_use_id, content, is_error in results]})

    def _drop_turn(self):
        del self.messages[self.turn_start:]
        self.pending = None

    # -------------------------------------------------------------- providers
    async def _stream(self, id, final=False):
        """
        Streams one model response and sends its text as ``ai_delta``. Returns ``{'text', 'tool_uses': [{'id',
        'name', 'input'}], 'stop': 'end_turn' | 'tool_use' | 'max_tokens' | 'refusal', 'message'}``; ``message`` is
        the assistant message to keep in the conversation.
        """
        # Every model request is billed, also the ones after action rounds: each one counts against the limit
        if not await self._count_request():
            raise AiLimitError()
        if self.system_prompt is None:
            self.system_prompt = await sync_to_async(self._cached_system_prompt)()
        if self._config('provider') == 'openai-compatible':
            return await self._stream_openai(id, final)
        return await self._stream_anthropic(id, final)

    async def _send_delta(self, id, text):
        await self.send(text_data=json.dumps({'type': 'ai_delta', 'id': id, 'text': text, 'is_error': False}))

    async def _stream_anthropic(self, id, final):
        model = self._config('model')
        params = dict(
            model=model,
            max_tokens=int(self._config('max_tokens')),
            # The tools and the system prompt (incl. the skill file) are stable and cached; so is the conversation
            system=[{'type': 'text', 'text': self.system_prompt, 'cache_control': {'type': 'ephemeral'}}],
            tools=[t | {'eager_input_streaming': True} for t in AI_TOOLS],
            cache_control={'type': 'ephemeral'},
            messages=self.messages,
        )
        if final:
            # The action round limit is reached: the model has to answer with the results it has
            params['tool_choice'] = {'type': 'none'}
        if self._config('effort'):
            params['output_config'] = {'effort': self._config('effort')}
        if model in AI_FALLBACK_MODELS and not self._config('base_url'):
            # A request declined by the model's safety classifiers is retried on a fallback model
            params.update(betas=['server-side-fallback-2026-07-01'], fallbacks='default')
        async with self._client().beta.messages.stream(**params) as stream:
            async for text in stream.text_stream:
                await self._send_delta(id, text)
            message = await stream.get_final_message()
        return {
            'text': ''.join(b.text for b in message.content if b.type == 'text'),
            'tool_uses': [{'id': b.id, 'name': b.name, 'input': b.input}
                          for b in message.content if b.type == 'tool_use'],
            'stop': message.stop_reason,
            # The complete content (incl. thinking blocks) must be sent back in later requests
            'message': {'role': 'assistant', 'content': message.content},
            'usage': self._usage(getattr(message, 'usage', None), {
                'input_tokens': 'input_tokens', 'output_tokens': 'output_tokens',
                'cache_read_input_tokens': 'cache_read_input_tokens',
                'cache_creation_input_tokens': 'cache_creation_input_tokens'}),
        }

    async def _stream_openai(self, id, final):
        params = dict(
            model=self._config('model'),
            max_tokens=int(self._config('max_tokens')),
            messages=[{'role': 'system', 'content': self.system_prompt}] + self.messages,
            tools=[{'type': 'function', 'function': {'name': t['name'], 'description': t['description'],
                                                     'parameters': t['input_schema']}} for t in AI_TOOLS],
            stream=True,
        )
        if final:
            params['tool_choice'] = 'none'
        if self._metrics_enabled():
            # The token usage comes in a last chunk without choices (not requested otherwise: older
            # OpenAI-compatible servers may reject the option)
            params['stream_options'] = {'include_usage': True}
        text, calls, finish_reason, usage = '', {}, None, None
        stream = await self._client().chat.completions.create(**params)
        async for chunk in stream:
            usage = getattr(chunk, 'usage', None) or usage
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta
            if delta and delta.content:
                text += delta.content
                await self._send_delta(id, delta.content)
            # Tool calls arrive in pieces, identified by their index
            for part in (delta.tool_calls or []) if delta else []:
                call = calls.setdefault(part.index, {'id': None, 'name': '', 'arguments': ''})
                call['id'] = part.id or call['id']
                if part.function:
                    # The name comes complete; some servers repeat it in every piece of the call
                    call['name'] = call['name'] or part.function.name or ''
                    call['arguments'] += part.function.arguments or ''
            finish_reason = choice.finish_reason or finish_reason
        tool_uses = []
        for index, call in sorted(calls.items()):
            try:
                tool_input = json.loads(call['arguments'] or '{}')
            except ValueError:
                tool_input = None  # rejected as INVALID_JSON
            tool_uses.append({'id': call['id'] or f'call_{index}', 'name': call['name'], 'input': tool_input})
        # OpenAI wants null instead of empty text next to tool calls
        message = {'role': 'assistant', 'content': text or (None if tool_uses else '')}
        if tool_uses:
            message['tool_calls'] = [{'id': t['id'], 'type': 'function',
                                      'function': {'name': calls[i]['name'], 'arguments': calls[i]['arguments']}}
                                     for t, i in zip(tool_uses, sorted(calls))]
        # Some servers report "stop" although the answer contains tool calls
        stop = {'length': 'max_tokens', 'content_filter': 'refusal'}.get(
            finish_reason, 'tool_use' if tool_uses else 'end_turn')
        usage_dict = self._usage(usage, {'input_tokens': 'prompt_tokens', 'output_tokens': 'completion_tokens'})
        cached = getattr(getattr(usage, 'prompt_tokens_details', None), 'cached_tokens', None)
        if usage_dict is not None and isinstance(cached, int):
            usage_dict['cache_read_input_tokens'] = cached
        return {'text': text, 'tool_uses': tool_uses, 'stop': stop, 'message': message, 'usage': usage_dict}

    def _client(self):
        if self.client is None:
            api_key = None if self._uses_system_token() else self.config.get('token')
            timeout = float(self._setting('SDC_AI_TIMEOUT', 600))
            options = dict(base_url=self._config('base_url') or None, timeout=timeout,
                           max_retries=int(self._setting('SDC_AI_MAX_RETRIES', 2)))
            if self.config.get('base_url'):
                # A URL entered by the user: every connection is checked for public addresses (SSRF)
                options['http_client'] = _ai_public_http_client(timeout)
            # With the system token the SDKs read their key (ANTHROPIC_API_KEY / OPENAI_API_KEY) from the environment
            if self._config('provider') == 'openai-compatible':
                try:
                    import openai
                except ImportError:
                    raise RuntimeError('The AI provider openai-compatible needs the openai package: '
                                       'pip install "simpledomcontrol[ai]"')
                self.client = openai.AsyncOpenAI(api_key=api_key, **options)
            else:
                try:
                    import anthropic
                except ImportError:
                    raise RuntimeError('The AI assistant needs the anthropic package: pip install "simpledomcontrol[ai]"')
                self.client = anthropic.AsyncAnthropic(api_key=api_key, **options)
        return self.client

    async def _count_request(self):
        """
        Counts a model request on the system's key against ``SDC_AI_MAX_REQUESTS_PER_USER``; False if over.
        Uses Django's async cache API (the sync one blocks the event loop or fails, e.g. with ``DatabaseCache``).
        """
        limit = self._setting('SDC_AI_MAX_REQUESTS_PER_USER')
        user = self.scope.get('user')
        if not limit or not self._uses_system_token() or not (user and user.is_authenticated):
            return True
        key = f'sdc_ai_requests:{user.pk}:{datetime.date.today().isoformat()}'
        await cache.aadd(key, 0, timeout=60 * 60 * 24)
        try:
            count = await cache.aincr(key)
        except ValueError:  # expired between add and incr
            await cache.aset(key, 1, timeout=60 * 60 * 24)
            count = 1
        return count <= limit

    # --------------------------------------------------------------- metrics
    @staticmethod
    def _usage(usage, fields):
        """The token counts of a provider's usage object as dict (``fields``: our name -> provider's name)."""
        if usage is None:
            return None
        values = {name: getattr(usage, attr, None) for name, attr in fields.items()}
        return {k: v for k, v in values.items() if isinstance(v, int) and not isinstance(v, bool)}

    def _metrics_enabled(self):
        """Metrics are recorded with ``SDC_AI_METRICS_FILE`` or ``SDC_AI_METRICS = True`` (logger only)."""
        return bool(self._setting('SDC_AI_METRICS_FILE')) or bool(self._setting('SDC_AI_METRICS', False))

    async def _log_request(self, id, round, started, result=None, error=None):
        """Logs one model request: duration, token usage, tool calls and the knowledge in the system prompt."""
        if not self._metrics_enabled():
            return
        prompt = self.system_prompt or ''
        record = {
            'type': 'request', 'request_id': id, 'round': round,
            'provider': self._config('provider'), 'model': self._config('model'), 'effort': self._config('effort'),
            'skill_source': self._setting('SDC_AI_SKILL_SOURCE', None) or 'auto',
            'system_prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest() if prompt else None,
            'system_prompt_chars': len(prompt),
            'duration_ms': round_ms(time.monotonic() - started),
        }
        if result is not None:
            record |= {
                'stop': result['stop'],
                'usage': result.get('usage'),
                'text_chars': len(result['text']),
                'tool_calls': [{'tool_use_id': t['id'], 'name': t['name'], 'input': t['input'],
                                'invalid': _ai_tool_input_error(t['name'], t['input'])
                                or _ai_resolve_model(t['name'], dict(t['input']))}
                               for t in result['tool_uses']],
            }
        if error is not None:
            record['error'] = error
        await self._log_metrics(record)

    async def _log_metrics(self, record):
        """
        Writes ``record`` (plus time, connection and user) to the logger ``sdc_core.ai_metrics`` and as one JSON
        line to ``SDC_AI_METRICS_FILE`` (relative to ``BASE_DIR``). The records contain the model's tool inputs
        (e.g. form values), but never the prompts, answers or tool results.
        """
        user = self.scope.get('user')
        record = {'ts': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'connection': getattr(self, 'connection_id', None),
                  'user': user.pk if user is not None and getattr(user, 'is_authenticated', False) else None} | record
        line = json.dumps(record, cls=DjangoJSONEncoder, ensure_ascii=False, default=str)
        metrics_logger.info(line)
        path = self._setting('SDC_AI_METRICS_FILE')
        if not path:
            return
        path = os.path.join(str(self._setting('BASE_DIR', '')), os.fspath(path))

        def write():
            with open(path, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
        try:
            await asyncio.to_thread(write)
        except OSError as e:
            logger.warning(f'SDC_AI_METRICS_FILE: cannot write {path}: {e}')

    # ---------------------------------------------------------------- prompt
    @classmethod
    def _cached_system_prompt(cls):
        """
        ``_system_prompt``, built once per process: the skill files are fixed per deployment. With ``DEBUG`` it is
        rebuilt for every connection, so edited skill files apply after a page reload.
        """
        global _ai_system_prompt
        if settings.DEBUG:
            return cls._system_prompt()
        if _ai_system_prompt is None:
            _ai_system_prompt = cls._system_prompt()
        return _ai_system_prompt

    @staticmethod
    def _system_prompt():
        prompt = getattr(settings, 'AI_DEFAULT_SYSTEM_PROMPT', None) or AI_DEFAULT_SYSTEM_PROMPT
        skill = SDCAiConsumer._skill_context()
        if not skill:
            skill = getattr(settings, 'SDC_AI_NO_SKILL_NOTE', AI_NO_SKILL_NOTE)
        parts = [prompt, SDCAiConsumer._url_guide(skill), skill] + SDCAiConsumer._additional_skills()
        return '\n\n'.join(p for p in parts if p)

    @staticmethod
    def _url_guide(skill):
        """
        How to read SDC URLs. Not added if the skill file of ``sdc_teach`` already contains it or with
        ``SDC_AI_SKILL_SOURCE = 'none'`` (no knowledge about the website, e.g. the baseline of an evaluation).
        """
        from sdc_core.management.commands.utils.teach_markdown import SDC_URL_GUIDE, SDC_URL_GUIDE_HEADING
        if SDCAiConsumer._skill_source() == 'none' or SDC_URL_GUIDE_HEADING in (skill or ''):
            return ''
        return SDC_URL_GUIDE

    @staticmethod
    def _additional_skills():
        """Contents of the files in ``SDC_AI_ADDITIONAL_SKILL_FILE``; missing files are logged and skipped."""
        paths = getattr(settings, 'SDC_AI_ADDITIONAL_SKILL_FILE', None) or []
        if isinstance(paths, (str, os.PathLike)):
            paths = [paths]
        contents = []
        for path in paths:
            path = os.path.join(str(getattr(settings, 'BASE_DIR', '')), os.fspath(path))
            try:
                with open(path, encoding='utf-8') as f:
                    contents.append(f.read().strip())
            except OSError as e:
                logger.warning(f'SDC_AI_ADDITIONAL_SKILL_FILE: cannot read {path}: {e}')
        return contents

    @staticmethod
    def _skill_source():
        source = getattr(settings, 'SDC_AI_SKILL_SOURCE', None) or 'auto'
        if source not in AI_SKILL_SOURCES:
            raise ImproperlyConfigured(f'SDC_AI_SKILL_SOURCE must be one of {", ".join(AI_SKILL_SOURCES)}')
        return source

    @staticmethod
    def _skill_context():
        """The knowledge about the website selected by ``SDC_AI_SKILL_SOURCE`` (see ``AI_SKILL_SOURCES``)."""
        source = SDCAiConsumer._skill_source()
        if source == 'none':
            return ''
        if source in ('auto', 'full'):
            path = SDCAiConsumer._skill_file()
            if os.path.isfile(path):
                with open(path, encoding='utf-8') as f:
                    return f.read()
            if source == 'full':
                raise ImproperlyConfigured(f'SDC_AI_SKILL_SOURCE is "full" but the skill file {path} does not exist '
                                           f'(run manage.py sdc_teach)')
        from sdc_core.management.commands.utils.teach_apps import load_app_skills
        skills = load_app_skills()
        # @ai-hidden controllers have nothing to operate for the assistant
        for skill in skills.values():
            controllers = skill.get('controllers')
            if isinstance(controllers, dict):
                skill['controllers'] = {t: c for t, c in controllers.items()
                                        if not (isinstance(c, dict) and c.get('hidden'))}
        return json.dumps(skills, indent=1, ensure_ascii=False) if skills else ''

    @staticmethod
    def _skill_file():
        """
        ``SDC_AI_SKILL_FILE`` relative to ``BASE_DIR``; by default ``SDC_SKILL.assistant.md`` (written by
        ``sdc_teach`` for the assistant) if it exists, else ``SDC_SKILL.md``.
        """
        base = str(getattr(settings, 'BASE_DIR', ''))
        configured = getattr(settings, 'SDC_AI_SKILL_FILE', None)
        if configured:
            return os.path.join(base, os.fspath(configured))
        assistant = os.path.join(base, 'SDC_SKILL.assistant.md')
        return assistant if os.path.isfile(assistant) else os.path.join(base, 'SDC_SKILL.md')
