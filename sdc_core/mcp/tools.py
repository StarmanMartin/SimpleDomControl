"""
Tools of the MCP endpoint. Which tools a client sees depends on its token (``Grant``) and ``SDC_MCP['models']``;
every call runs through ``model_actions``, so the token's privileges and the models' own rules
(``is_authorised`` / ``get_queryset``) apply exactly as in the REST API.

- Read tools (generic, one model argument): ``describe``, ``model_get``, ``model_load``, ``account_get``.
- Write tools (one per model, input schema from the model's forms): ``<model>_create`` and ``<model>_update`` with
  ``model:<Name>:write``, ``<model>_delete`` with ``model:<Name>:delete``, and ``account_update`` with
  ``account:write``. File fields cannot be set over MCP.
"""
import json
import re
from dataclasses import dataclass
from typing import Callable

from django.contrib.auth import get_user_model
from django.core.exceptions import FieldError, ObjectDoesNotExist, PermissionDenied, ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.http import Http404

from sdc_core import api_tokens, skill_data
from sdc_core.mcp.settings import exposed_models, mcp_settings
from sdc_core.sdc_extentions import model_actions
from sdc_core.sdc_extentions.models import all_models, resolve_form
from sdc_core.sdc_extentions.schema import generate_form_schema, is_file_field

READ_ONLY = {'readOnlyHint': True, 'destructiveHint': False, 'idempotentHint': True, 'openWorldHint': False}
CREATE = {'readOnlyHint': False, 'destructiveHint': False, 'idempotentHint': False, 'openWorldHint': False}
# Changing a record overwrites the old values: clients should ask before they run it
UPDATE = {'readOnlyHint': False, 'destructiveHint': True, 'idempotentHint': True, 'openWorldHint': False}
DELETE = {'readOnlyHint': False, 'destructiveHint': True, 'idempotentHint': True, 'openWorldHint': False}


class UnknownTool(Exception):
    """The client called a tool that does not exist or is not listed for its token (JSON-RPC error)."""


class ToolError(Exception):
    """An error of a tool call, returned to the model as a result with ``isError`` so it can react."""


@dataclass
class Tool:
    definition: dict
    handler: Callable
    # True: the arguments are checked against the types of the schema; False: only required and unknown names
    # (the model's form validates the values and its errors go back to the client)
    strict: bool = True

    @property
    def name(self):
        return self.definition['name']


def tool_prefix(model_name):
    """``BookContent`` → ``book_content``: the prefix of a model's write tools."""
    return re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()


def readable_models(grant):
    """The exposed models the grant may read."""
    readable = grant.models(model_actions.READ)
    return [name for name in exposed_models() if name in readable]


def _model_schema(models):
    return {'type': 'string', 'enum': models, 'description': 'Name of the data model (SdcModel)'}


def _id_schema():
    return {'type': 'integer', 'description': 'Primary key (id) of the record'}


def _form_class(model, key):
    form_attr = getattr(model.SdcMeta, key, None)
    if form_attr is None:
        return None
    try:
        return resolve_form(form_attr)
    except (ImportError, NotImplementedError):
        return None


def _form_input_schema(form_class, partial, exclude=()):
    """
    The input schema of a form without file fields and ``exclude``; None if a required field cannot be given
    (a required file field when creating).
    """
    schema, _has_files = generate_form_schema(form_class, partial=partial)
    fields = form_class().fields
    dropped = {name for name, field in fields.items() if is_file_field(field)} | set(exclude)
    required = [name for name in schema.get('required', []) if name not in dropped]
    if not partial and any(name in dropped for name in schema.get('required', [])
                           if is_file_field(fields[name])):
        return None
    properties = {name: prop for name, prop in schema['properties'].items() if name not in dropped}
    result = {'type': 'object', 'additionalProperties': False, 'properties': properties}
    if required:
        result['required'] = required
    return result


# ------------------------------------------------------------------ the tools of a grant

def available_tools(grant):
    """The tools the grant may use, in the order they are listed."""
    tools = []
    if skill_data.skill_data() is not None:
        tools.append(Tool({
            'name': 'describe',
            'title': 'Describe a view or data model',
            'description': 'Full documentation of one view, controller or data model (SdcModel) of this website: '
                           'arguments, links, buttons, forms and fields, recipes. Names are listed in the server '
                           'instructions.',
            'inputSchema': {'type': 'object', 'additionalProperties': False, 'required': ['name'],
                            'properties': {'name': {'type': 'string', 'description': 'View or controller tag '
                                                                                     '(e.g. "sdc-login") or '
                                                                                     'model name'}}},
            'annotations': READ_ONLY,
        }, _describe))
    models = readable_models(grant)
    if models:
        max_records = mcp_settings()['max_records']
        tools.append(Tool({
            'name': 'model_get',
            'title': 'Read one record',
            'description': 'Read one record of a data model by its id, if the user is allowed to see it. Returns '
                           '{"model", "pk", "fields"}.',
            'inputSchema': {'type': 'object', 'additionalProperties': False, 'required': ['model', 'id'],
                            'properties': {'model': _model_schema(models), 'id': _id_schema()}},
            'annotations': READ_ONLY,
        }, _model_get))
        tools.append(Tool({
            'name': 'model_load',
            'title': 'Load records',
            'description': f'Load records of a data model that the user is allowed to see, optionally filtered. '
                           f'Returns {{"records": [{{"model", "pk", "fields"}}], "total", "truncated"}}; at most '
                           f'{max_records} records per call.',
            'inputSchema': {'type': 'object', 'additionalProperties': False, 'required': ['model'],
                            'properties': {
                                'model': _model_schema(models),
                                'filter': {'type': 'object', 'description': 'Django field lookups on the fields '
                                           'of the model, e.g. {"name": "Jane"}, {"age__gte": 18} or '
                                           '{"author__name__icontains": "tolk"}; omit to load all records'},
                                'limit': {'type': 'integer', 'minimum': 1, 'maximum': max_records,
                                          'description': f'Maximum number of records (default {max_records})'},
                            }},
            'annotations': READ_ONLY,
        }, _model_load))
    if grant.allows_account(api_tokens.ACCOUNT_READ):
        tools.append(Tool({
            'name': 'account_get',
            'title': 'Read the own account',
            'description': 'The user record of the user this token belongs to.',
            'inputSchema': {'type': 'object', 'additionalProperties': False, 'properties': {}},
            'annotations': READ_ONLY,
        }, _account_get))
    tools += _write_tools(grant)
    account_update = _account_update_tool(grant)
    if account_update is not None:
        tools.append(account_update)
    return tools


def _write_tools(grant):
    tools = []
    writable = grant.models(model_actions.WRITE)
    deletable = grant.models(model_actions.DELETE)
    models = all_models()
    for name in exposed_models():
        model, prefix = models[name], tool_prefix(name)
        if name in writable:
            create_form = _form_class(model, 'create_form')
            schema = _form_input_schema(create_form, partial=False) if create_form else None
            if schema is not None:
                tools.append(Tool({
                    'name': f'{prefix}_create',
                    'title': f'Create {name}',
                    'description': f'Create a {name} record with the values of its form (validated like in the '
                                   f'web app). Returns the new record {{"model", "pk", "fields"}}; invalid values '
                                   f'return the form errors per field.',
                    'inputSchema': schema,
                    'annotations': CREATE,
                }, _create_handler(name), strict=False))
            edit_form = _form_class(model, 'edit_form')
            schema = _form_input_schema(edit_form, partial=True) if edit_form else None
            if schema is not None:
                schema['properties'] = {'id': _id_schema(), **schema['properties']}
                schema['required'] = ['id']
                tools.append(Tool({
                    'name': f'{prefix}_update',
                    'title': f'Change {name}',
                    'description': f'Change fields of a {name} record; fields that are left out keep their values. '
                                   f'Returns the changed record; invalid values return the form errors per field.',
                    'inputSchema': schema,
                    'annotations': UPDATE,
                }, _update_handler(name), strict=False))
        if name in deletable:
            tools.append(Tool({
                'name': f'{prefix}_delete',
                'title': f'Delete {name}',
                'description': f'Delete a {name} record. This cannot be undone.',
                'inputSchema': {'type': 'object', 'additionalProperties': False, 'required': ['id'],
                                'properties': {'id': _id_schema()}},
                'annotations': DELETE,
            }, _delete_handler(name)))
    return tools


def _account_update_tool(grant):
    if not grant.allows_account(api_tokens.ACCOUNT_WRITE):
        return None
    user_model = get_user_model()
    if all_models().get(user_model.__name__) is not user_model:
        return None
    edit_form = _form_class(user_model, 'edit_form')
    if edit_form is None:
        return None
    schema = _form_input_schema(edit_form, partial=True, exclude=api_tokens.ACCOUNT_PROTECTED_FIELDS)
    if not schema['properties']:
        return None
    return Tool({
        'name': 'account_update',
        'title': 'Change the own profile',
        'description': 'Change fields of the own user profile; fields that are left out keep their values. '
                       'Password, e-mail and username cannot be changed with a token.',
        'inputSchema': schema,
        'annotations': UPDATE,
    }, _account_update, strict=False)


def list_tools(grant):
    """The tool definitions (MCP ``tools/list``) for the grant of the calling token."""
    return [tool.definition for tool in available_tools(grant)]


# ------------------------------------------------------------------ calls

_JSON_TYPES = {'string': str, 'integer': int, 'object': dict}


def _validate(tool, arguments):
    """
    Checks the arguments against the tool's input schema: required and unknown names always, types, enum and
    range only for ``strict`` tools.
    """
    schema = tool.definition['inputSchema']
    if not isinstance(arguments, dict):
        raise ToolError('The arguments must be an object')
    missing = [name for name in schema.get('required', []) if name not in arguments]
    if missing:
        raise ToolError(f"Missing arguments: {', '.join(missing)}")
    unknown = [name for name in arguments if name not in schema['properties']]
    if unknown:
        raise ToolError(f"Unknown arguments: {', '.join(unknown)}")
    if 'id' in schema['properties'] and 'id' in arguments and \
            (isinstance(arguments['id'], bool) or not isinstance(arguments['id'], int)):
        raise ToolError('id must be of type integer')
    if not tool.strict:
        return
    for name, value in arguments.items():
        prop = schema['properties'][name]
        expected = _JSON_TYPES[prop['type']]
        if isinstance(value, bool) or not isinstance(value, expected):
            raise ToolError(f'{name} must be of type {prop["type"]}')
        if 'enum' in prop and value not in prop['enum']:
            raise ToolError(f'{name} must be one of: {", ".join(prop["enum"])}')
        if 'minimum' in prop and value < prop['minimum'] or 'maximum' in prop and value > prop['maximum']:
            raise ToolError(f'{name} must be between {prop.get("minimum")} and {prop.get("maximum")}')


def call_tool(name, arguments, user, grant):
    """
    Runs a tool and returns the MCP ``tools/call`` result. ``UnknownTool`` if the tool is not available to the
    grant; all other problems are results with ``isError``.
    """
    tool = next((t for t in available_tools(grant) if t.name == name), None)
    if tool is None:
        raise UnknownTool(name)
    arguments = arguments if arguments is not None else {}
    try:
        _validate(tool, arguments)
        result = tool.handler(arguments, user, grant)
    except ToolError as e:
        return _error(str(e))
    except model_actions.FormValidationError as e:
        return _error('Invalid values: ' + json.dumps({field: list(messages) for field, messages in e.errors.items()},
                                                      ensure_ascii=False))
    except model_actions.MissingPrivilege as e:
        return _error(str(e))
    except PermissionDenied as e:
        return _error(str(e) or 'The user is not allowed to do this')
    except ObjectDoesNotExist:
        return _error('Not found (or the user is not allowed to see it)')
    except Http404 as e:
        return _error(str(e))
    if isinstance(result, str):
        return {'content': [{'type': 'text', 'text': result}], 'isError': False}
    text = json.dumps(result, cls=DjangoJSONEncoder, ensure_ascii=False)
    return {'content': [{'type': 'text', 'text': text}],
            'structuredContent': json.loads(text), 'isError': False}


def _error(message):
    return {'content': [{'type': 'text', 'text': message}], 'isError': True}


def _describe(arguments, user, grant):
    result = skill_data.describe(arguments['name'])
    if result is None:
        raise ToolError('There is no skill data (run manage.py sdc_teach)')
    text, is_error = result
    if is_error:
        raise ToolError(text)
    return text


def _model_get(arguments, user, grant):
    return model_actions.get(user, arguments['model'], arguments['id'], grant=grant)


def _model_load(arguments, user, grant):
    limit = arguments.get('limit') or mcp_settings()['max_records']
    query = arguments.get('filter') or {}
    try:
        records, total = model_actions.load_page(user, arguments['model'], query, limit=limit, grant=grant)
    except (FieldError, ValidationError, ValueError, TypeError) as e:
        raise ToolError(f'Invalid filter: {e}')
    return {'records': records, 'total': total, 'truncated': total > len(records)}


def _account_get(arguments, user, grant):
    return model_actions.get(user, get_user_model().__name__, user.pk)


def _account_update(arguments, user, grant):
    return api_tokens.update_account(user, grant, arguments)


def _create_handler(model_name):
    def create(arguments, user, grant):
        return model_actions.create(user, model_name, arguments, grant=grant)
    return create


def _update_handler(model_name):
    def update(arguments, user, grant):
        data = {key: value for key, value in arguments.items() if key != 'id'}
        return model_actions.update(user, model_name, arguments['id'], data, partial=True, grant=grant)
    return update


def _delete_handler(model_name):
    def delete(arguments, user, grant):
        model_actions.delete(user, model_name, arguments['id'], grant=grant)
        return {'deleted': True, 'model': model_name, 'pk': arguments['id']}
    return delete
