import os
import types
import traceback
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.files.uploadhandler import TemporaryFileUploadHandler

from django.utils.datastructures import MultiValueDict
from django.utils.translation import gettext as _f
from django.contrib.auth import get_user_model
from channels.generic.websocket import WebsocketConsumer

from asgiref.sync import async_to_sync
import importlib
import json

from sdc_core.sdc_extentions.models import SdcModel, SDCSerializer, all_models
from sdc_core.sdc_extentions.response import sdc_link_factory, sdc_link_obj_factory
from sdc_core.sdc_extentions.import_manager import import_function
from sdc_core.sdc_extentions.views import SdcAccessMixin

import logging

logger = logging.getLogger(__name__)
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
                'delete': {'header': f'{model} was deleted', 'msg': '{0} was changed'}}


class SDCConsumer(WebsocketConsumer):

    def connect(self):
        self.scope["session"]["channel_name"] = self.channel_name
        self.scope["session"].save()
        self.accept()
        self.group_list = []
        self.queryset = None

    def disconnect(self, close_code):
        for group in self.group_list:
            async_to_sync(self.channel_layer.group_discard)(
                group,
                self.channel_name
            )

    def state_sdc_event(self, event):
        self.send(text_data=json.dumps({
            'type': 'sdc_event',
            'event': event.get('event', False),
            'msg': event.get('msg', False),
            'header': event.get('header', False),
            'payload': event.get('payload', False),
            'is_error': False
        }))

    def state_redirect(self, event):
        if 'controller' in event:
            event['link'] = sdc_link_factory(event.get('controller'), event.get('args'))

        self.send(text_data=json.dumps({
            'type': 'sdc_redirect',
            'msg': event.get('msg', False),
            'header': event.get('header', False),
            'link': sdc_link_obj_factory(event.get('link', False)),
            'is_error': False
        }))

    def state_error(self, event, id=None):
        self.send(text_data=json.dumps({
            'type': 'error',
            'id': id,
            'is_error': True,
            'msg': event.get('msg', ''),
            'header': event.get('header', ''),
        }))

    @staticmethod
    def to_camel_case(snake_str):
        components = snake_str.split('-')
        # We capitalize the first letter of each component except the first one
        # with the 'title' method and join them together.
        return ''.join(x.title() for x in components)

    def receive(self, text_data=None, bytes_data=None):
        json_data = {}
        try:
            session = self.scope['session'].load()
            json_data = json.loads(text_data)
            if json_data['event'] == 'sdc_call':
                controller_name = self.to_camel_case(json_data['controller'])
                controller = import_function("%s.sdc_views.%s" % (json_data['app'], controller_name))
                c_instance = controller()
                if isinstance(c_instance, SdcAccessMixin):
                    if not c_instance.check_requirements(self.scope['user']):
                        raise PermissionDenied()
                method = getattr(controller(), json_data['function'])

                logger.info(f"SDC call Socket received: {json_data['app']}.{controller_name}.{json_data['function']}")

                return_vals = method(channel=self, **json_data.get('args', {}))
                return_vals_generator = []
                if isinstance(return_vals, types.GeneratorType):
                    return_vals_generator = return_vals
                    return_vals = next(return_vals, None)

                self.send(text_data=json.dumps({
                    'id': json_data['id'],
                    'type': 'sdc_recall',
                    'data': return_vals,
                    'is_error': False
                }))
                for x in return_vals_generator: pass
            else:
                raise ValueError("event must be sdc_call")

        except PermissionDenied:
            self.state_error({
                'msg': _f('403 Not allowed!'),
                'header': _f('Upps!!')
            }, json_data.get('id'))

        except Exception as e:
            extracted_list = traceback.extract_tb(e.__traceback__)
            e_text = [e.__str__()] + [item for item in traceback.StackSummary.from_list(extracted_list).format()]
            logger.error('\n'.join(e_text))
            if not settings.DEBUG:
                e_text = _f('Something went wrong')
            self.state_error({
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
        self.model_id_list = []
        self._upload_handler = {}
        self._group_names = []

    def connect(self):
        self.model_name = self.scope['url_route']['kwargs']['model_name']
        self.model = ALL_MODELS.get(self.model_name)
        if self.model is None or not hasattr(self.model, '__is_sdc_model__'):
            return
        self.scope["session"]["channel_name"] = self.channel_name
        self.scope["session"].save()
        self.accept()

    def disconnect(self, close_code):
        for group in self._group_names:
            async_to_sync(self.channel_layer.group_discard( group, self.channel_name ))

    def on_update(self, data):
        if data['pk'] in self.ids:
            self.send(text_data=json.dumps(data))

    def on_create(self, data):
        instance = data['pk']
        try:
            self._load_model().get(pk=instance)
            self.send(text_data=json.dumps(data))
        except:
            pass

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
                model_data = SDCSerializer().serialize(self._load_model())
                self.send(text_data=json.dumps({
                    'type': json_data['event_type'],
                    'event_id': json_data['event_id'],
                    'args': {
                        'data': model_data,
                        'media_url': settings.MEDIA_URL or '/'
                    },
                    'is_error': False
                }))
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
                traceback.print_tb(e.__traceback__)
            else:
                logger.error(e_text)
                e_text_details = str(e)
                e_text = _f('Something went wrong! {e}').format(e=e_text_details)

            self.state_error({
                'type': msg_type,
                'msg': e_text,
                'event_id': json_data.get('event_id'),
                'header': _f('Upps!!')
            })

    def _add_to_class(self):
        async_to_sync(self.channel_layer.group_add)(
            self.model_name,
            self.channel_name
        )

    def _load_model(self):
        queryset = self.model.get_queryset(self.scope['user'], self.scope['event_type'], self.queryset)

        data_load_result = self.model.data_load(self.scope['user'], queryset, self.queryset)
        if data_load_result is not None:
            return data_load_result
        res = queryset.filter(**self.queryset)
        self.ids = list(res.values_list('id', flat=True))

        return res

    def _init_connection(self, json_data):
        self._load_model()
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
        if not hasattr(self.model, 'forms'):
            raise NotImplemented()

        return self._load_form(json_data, self.model.forms.get(form_name), instance)

    def _load_form(self, json_data, form_attr, instance=None):
        if callable(form_attr):
            form_attr = form_attr({})
        if form_attr is None:
            raise NotImplemented()
        elif isinstance(form_attr, str):
            edit_form_path = form_attr.split('.')
            form = getattr(importlib.import_module('.'.join(edit_form_path[0:-1])), edit_form_path[-1])
        else:
            form = form_attr

        self.send(text_data=json.dumps({
            'type': json_data['event_type'],
            'event_id': json_data['event_id'],
            'html': self._render(self.model.SdcMeta.html_form_template, {'instance': instance, 'form': form(instance=instance)},
                                 json_data),
            'is_error': False
        }))

    def _create_element(self, json_data):
        instance: SdcModel = self.model()
        instance.scope = self.scope
        return self._submit_element(json_data, self.model.SdcMeta.create_form, instance)

    def _save_element(self, json_data):
        instance = self._load_model().get(pk=json_data['args']['data']['pk'])
        instance.scope = self.scope
        return self._submit_element(json_data, self.model.SdcMeta.edit_form, instance)

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
        handler.receive_data_chunk(bytes([ord(x) for x in file_data['chunk']]), int(file_data['idx']))
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
        if form_attr is None:
            raise NotImplemented()
        elif isinstance(form_attr, str):
            edit_form_path = form_attr.split('.')
            form = getattr(importlib.import_module('.'.join(edit_form_path[0:-1])), edit_form_path[-1])
        else:
            form = form_attr
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
            msg = self.msg_manager.get_msg(form_instance.instance, json_data['event_type'])
        else:
            msg = {'header': 'Upss!',
                   'msg': "<ul>%s</ul>" % "\n".join(
                       ["<li>%s: %s</li>" % (k, v[0]) for k, v in form_instance.errors.items()])
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
            raise NotImplemented()

        self.send(text_data=json.dumps({
            'type': json_data['event_type'],
            'event_id': json_data['event_id'],
            'html': self._render(self.model.SdcMeta.html_list_template, {'instances': self._load_model()}, json_data),
            'is_error': False
        }))

    def _load_detail_view(self, json_data):
        if self.model.html_detail_template is None:
            raise NotImplemented()
        instance = self._load_model().get(pk=json_data['args']['pk'])
        instance.scope = self.scope
        self.send(text_data=json.dumps({
            'type': json_data['event_type'],
            'event_id': json_data['event_id'],
            'html': self._render(self.model.html_detail_template, {'instance': instance}, json_data),
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
