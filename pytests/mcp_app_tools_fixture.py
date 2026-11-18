"""
MCP tools for ``test_mcp_app_tools`` (``SDC_MCP['tools']`` imports them by path). Kept apart from the test module:
importing a test module by path would run its Django setup a second time and set DJANGO_SETTINGS_MODULE again,
which the project-generation tests must not inherit (see ``conftest.pytest_collection_finish``).
"""
from django.core.exceptions import PermissionDenied

from sdc_core.mcp.app_tools import READ_ONLY_OPEN_WORLD, McpTool
from sdc_core.mcp.tools import ToolError

CALLS = []


def _echo(arguments, user, grant):
    CALLS.append((arguments, user.username))
    return {'echo': arguments, 'user': user.username}


def _fails(arguments, user, grant):
    raise RuntimeError('secret detail https://user:password@example.org')


def _refuses(arguments, user, grant):
    if arguments.get('kind') == 'tool':
        raise ToolError('No such device')
    raise PermissionDenied('Not your device')


SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['device'],
          'properties': {'device': {'type': 'integer'}, 'full': {'type': 'boolean'},
                         'factor': {'type': 'number', 'minimum': 0, 'maximum': 10},
                         'view': {'type': 'string', 'enum': ['json', 'paths']},
                         'keys': {'type': 'array', 'items': {'type': 'string'}}}}
TOOLS = [
    McpTool(name='lab_read', title='Read a device', description='Reads a device.', input_schema=SCHEMA,
            handler=_echo, privileges=('lab:read',), annotations=READ_ONLY_OPEN_WORLD),
    McpTool(name='lab_steer', description='Steers a device.', input_schema=SCHEMA, handler=_echo,
            privileges=('lab:write', 'model:Author:read')),
    McpTool(name='lab_fails', description='Always fails.', input_schema={'type': 'object', 'properties': {}},
            handler=_fails, privileges=('lab:read',)),
    McpTool(name='lab_refuses', description='Refuses.',
            input_schema={'type': 'object', 'properties': {'kind': {'type': 'string'}}},
            handler=_refuses, privileges=('lab:read',)),
]


def tool_factory():
    return TOOLS[:1]
