"""
Tools of the MCP endpoint. Which tools a client sees depends on its token (``Grant``) and ``SDC_MCP['models']``;
every call runs through ``model_actions``, so the token's privileges and the models' own rules
(``is_authorised`` / ``get_queryset``) apply exactly as in the REST API.
"""
import json

from django.contrib.auth import get_user_model
from django.core.exceptions import FieldError, ObjectDoesNotExist, PermissionDenied, ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.http import Http404

from sdc_core import api_tokens, skill_data
from sdc_core.mcp.settings import exposed_models, mcp_settings
from sdc_core.sdc_extentions import model_actions

READ_ONLY = {'readOnlyHint': True, 'destructiveHint': False, 'idempotentHint': True, 'openWorldHint': False}


class UnknownTool(Exception):
    """The client called a tool that does not exist or is not listed for its token (JSON-RPC error)."""


class ToolError(Exception):
    """An error of a tool call, returned to the model as a result with ``isError`` so it can react."""


def readable_models(grant):
    """The exposed models the grant may read."""
    readable = grant.models(model_actions.READ)
    return [name for name in exposed_models() if name in readable]


def _model_schema(models):
    return {'type': 'string', 'enum': models, 'description': 'Name of the data model (SdcModel)'}


def list_tools(grant):
    """The tool definitions (MCP ``tools/list``) for the grant of the calling token."""
    tools = []
    if skill_data.skill_data() is not None:
        tools.append({
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
        })
    models = readable_models(grant)
    if models:
        max_records = mcp_settings()['max_records']
        tools.append({
            'name': 'model_get',
            'title': 'Read one record',
            'description': 'Read one record of a data model by its id, if the user is allowed to see it. Returns '
                           '{"model", "pk", "fields"}.',
            'inputSchema': {'type': 'object', 'additionalProperties': False, 'required': ['model', 'id'],
                            'properties': {'model': _model_schema(models),
                                           'id': {'type': 'integer', 'description': 'Primary key of the record'}}},
            'annotations': READ_ONLY,
        })
        tools.append({
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
        })
    if grant.allows_account(api_tokens.ACCOUNT_READ):
        tools.append({
            'name': 'account_get',
            'title': 'Read the own account',
            'description': 'The user record of the user this token belongs to.',
            'inputSchema': {'type': 'object', 'additionalProperties': False, 'properties': {}},
            'annotations': READ_ONLY,
        })
    return tools


_JSON_TYPES = {'string': str, 'integer': int, 'object': dict}


def _validate(tool, arguments):
    """Checks the arguments against the tool's input schema (required, unknown keys, types, enum, range)."""
    schema = tool['inputSchema']
    if not isinstance(arguments, dict):
        raise ToolError('The arguments must be an object')
    missing = [name for name in schema.get('required', []) if name not in arguments]
    if missing:
        raise ToolError(f"Missing arguments: {', '.join(missing)}")
    unknown = [name for name in arguments if name not in schema['properties']]
    if unknown:
        raise ToolError(f"Unknown arguments: {', '.join(unknown)}")
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
    tool = next((t for t in list_tools(grant) if t['name'] == name), None)
    if tool is None:
        raise UnknownTool(name)
    try:
        _validate(tool, arguments if arguments is not None else {})
        result = _TOOLS[name](arguments or {}, user, grant)
    except ToolError as e:
        return _error(str(e))
    except model_actions.MissingPrivilege as e:
        return _error(str(e))
    except PermissionDenied as e:
        return _error(str(e) or 'The user is not allowed to do this')
    except ObjectDoesNotExist:
        return _error('Not found (or the user is not allowed to see it)')
    except Http404 as e:
        return _error(str(e))
    except (FieldError, ValidationError, ValueError, TypeError) as e:
        return _error(f'Invalid filter: {e}')
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
    records, total = model_actions.load_page(user, arguments['model'], query, limit=limit, grant=grant)
    return {'records': records, 'total': total, 'truncated': total > len(records)}


def _account_get(arguments, user, grant):
    return model_actions.get(user, get_user_model().__name__, user.pk)


_TOOLS = {
    'describe': _describe,
    'model_get': _model_get,
    'model_load': _model_load,
    'account_get': _account_get,
}
