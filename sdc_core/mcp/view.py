"""
The MCP endpoint (``sdc_mcp/``): the Streamable HTTP transport of the Model Context Protocol, stateless and without
server-sent events. Every POST carries one JSON-RPC message; requests are answered with ``application/json``,
notifications and responses with 202. ``GET`` (a server-to-client stream) is not offered (405).

Every request needs an API token (``Authorization: Bearer sdc_...``); the token's privileges decide which tools a
client sees and can call. Requests from browser pages of other sites are refused (``Origin`` must match
``ALLOWED_HOSTS``).
"""
import json
import logging
import re
from urllib.parse import urlsplit

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.http.request import validate_host
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from sdc_core import api_tokens, skill_data
from sdc_core.mcp import resources, tools
from sdc_core.mcp.settings import exposed_models, mcp_settings, server_name

logger = logging.getLogger(__name__)

# Protocol versions this server speaks, newest first. Requests of other versions are answered with the newest.
PROTOCOL_VERSIONS = ('2025-11-25', '2025-06-18', '2025-03-26')
# Assumed when a client sends no MCP-Protocol-Version header (as the specification says)
DEFAULT_PROTOCOL_VERSION = '2025-03-26'

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


def _sdc_version():
    try:
        from importlib.metadata import version
        return version('SimpleDomControl')
    except Exception:
        return 'unknown'


def _rpc_error(id, code, message, status=200):
    return JsonResponse({'jsonrpc': '2.0', 'id': id, 'error': {'code': code, 'message': message}}, status=status)


def _rpc_result(id, result):
    return JsonResponse({'jsonrpc': '2.0', 'id': id, 'result': result})


def _origin_allowed(request):
    """
    False if a browser page of another site sent the request (DNS rebinding protection required by the MCP
    specification). Requests without ``Origin`` come from programs, not browsers, and are allowed.
    """
    origin = request.headers.get('Origin')
    if origin is None:
        return True
    host = urlsplit(origin).hostname
    if not host:
        return False
    allowed_hosts = settings.ALLOWED_HOSTS or (['localhost', '127.0.0.1', '[::1]'] if settings.DEBUG else [])
    return validate_host(host, allowed_hosts)


def _instructions():
    name = server_name()
    text = (f'MCP server of the website "{name}", built with SimpleDomControl. It gives access to the data models '
            f'(SdcModels) of the website with the rights of the user who created the API token: use model_load '
            f'and model_get to read records, describe for the documentation of a view or model. Depending on the '
            f'token there are also tools to create, change and delete records (<model>_create, <model>_update, '
            f'<model>_delete); they check the values like the forms of the web app. Ask the user before you '
            f'change or delete data.')
    mode = mcp_settings()['instructions']
    index = skill_data.skill_index() if mode in ('models', 'index') else None
    if index and mode == 'models':
        index = _models_section(index)
    return f'{text}\n\n{index}' if index else text


def _models_section(index):
    """The 'Data models' section of the skill index (one line per model); None if there is none."""
    exposed = set(exposed_models())
    lines, inside = [], False
    for line in index.splitlines():
        if line.startswith('#'):
            inside = line.lstrip('#').strip().lower() == 'data models'
            if inside:
                lines.append('## Data models of this website')
            continue
        if inside:
            match = re.match(r'- `(\w+)`', line)
            if match and match.group(1) not in exposed:
                continue
            lines.append(line)
    text = '\n'.join(lines).strip()
    return text + '\n\nViews and controllers: `describe` with a tag; the full index: resource `sdc://skill`.' \
        if text else None


@method_decorator(csrf_exempt, name='dispatch')
class SdcMcpView(View):
    http_method_names = ['get', 'post', 'delete', 'options']

    def dispatch(self, request, *args, **kwargs):
        if not mcp_settings()['enabled']:
            return HttpResponse(status=404)
        if not _origin_allowed(request):
            return JsonResponse({'error': 'Origin not allowed'}, status=403)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        # No server-to-client stream (stateless server without server-sent events)
        return HttpResponse(status=405, headers={'Allow': 'POST'})

    def delete(self, request):
        # There are no sessions to end
        return HttpResponse(status=405, headers={'Allow': 'POST'})

    def post(self, request):
        version = request.headers.get('MCP-Protocol-Version')
        if version is not None and version not in PROTOCOL_VERSIONS:
            return _rpc_error(None, INVALID_REQUEST, f'Unsupported MCP-Protocol-Version: {version}', status=400)

        try:
            auth = api_tokens.authenticate(request)
        except api_tokens.AuthenticationFailed as e:
            return api_tokens.unauthorized_response(e)
        if auth.token is None:
            # Deprecated JSON web tokens are not accepted here
            return api_tokens.unauthorized_response(api_tokens.AuthenticationFailed('MCP needs an API token'))

        try:
            message = json.loads(request.body)
        except ValueError:
            return _rpc_error(None, PARSE_ERROR, 'Parse error', status=400)
        if not isinstance(message, dict) or message.get('jsonrpc') != '2.0':
            return _rpc_error(None, INVALID_REQUEST, 'Invalid request: one JSON-RPC 2.0 message per POST',
                              status=400)

        method = message.get('method')
        if method is None and 'id' in message and ('result' in message or 'error' in message):
            # A response to a request of the server (this server sends none): nothing to answer
            return HttpResponse(status=202)
        if 'id' not in message:
            # A notification (method without id): nothing to answer
            if method is not None and not isinstance(method, str):
                return _rpc_error(None, INVALID_REQUEST, 'Invalid request', status=400)
            return HttpResponse(status=202)
        id = message['id']
        if not isinstance(method, str) or isinstance(id, bool) or not isinstance(id, (str, int)):
            return _rpc_error(id if isinstance(id, (str, int)) else None, INVALID_REQUEST, 'Invalid request',
                              status=400)
        params = message.get('params') or {}
        if not isinstance(params, dict):
            return _rpc_error(id, INVALID_PARAMS, 'params must be an object')

        handler = getattr(self, f"_rpc_{method.replace('/', '_')}", None)
        if handler is None:
            return _rpc_error(id, METHOD_NOT_FOUND, f'Method not found: {method}')
        try:
            return handler(id, params, auth)
        except Exception:
            logger.exception(f'MCP {method} failed')
            return _rpc_error(id, INTERNAL_ERROR, 'Internal error')

    # ------------------------------------------------------------- methods
    def _rpc_initialize(self, id, params, auth):
        requested = params.get('protocolVersion')
        version = requested if requested in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0]
        return _rpc_result(id, {
            'protocolVersion': version,
            'capabilities': {'tools': {'listChanged': False}, 'resources': {'listChanged': False}},
            'serverInfo': {'name': server_name(), 'title': f'{server_name()} (SimpleDomControl)',
                           'version': str(getattr(settings, 'VERSION', '') or _sdc_version())},
            'instructions': _instructions(),
        })

    def _rpc_ping(self, id, params, auth):
        return _rpc_result(id, {})

    def _rpc_tools_list(self, id, params, auth):
        return _rpc_result(id, {'tools': tools.list_tools(auth.grant)})

    def _rpc_tools_call(self, id, params, auth):
        name = params.get('name')
        if not isinstance(name, str):
            return _rpc_error(id, INVALID_PARAMS, 'name must be a string')
        try:
            return _rpc_result(id, tools.call_tool(name, params.get('arguments'), auth.user, auth.grant))
        except tools.UnknownTool:
            return _rpc_error(id, INVALID_PARAMS, f'Unknown tool: {name}')

    def _rpc_resources_list(self, id, params, auth):
        return _rpc_result(id, {'resources': resources.list_resources()})

    def _rpc_resources_templates_list(self, id, params, auth):
        return _rpc_result(id, {'resourceTemplates': []})

    def _rpc_resources_read(self, id, params, auth):
        uri = params.get('uri')
        try:
            return _rpc_result(id, resources.read_resource(uri))
        except resources.UnknownResource:
            # Resource not found (error code of the MCP specification)
            return JsonResponse({'jsonrpc': '2.0', 'id': id,
                                 'error': {'code': -32002, 'message': 'Resource not found', 'data': {'uri': uri}}})
