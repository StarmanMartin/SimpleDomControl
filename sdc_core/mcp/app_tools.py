"""
The application's own MCP tools, besides the generic model tools of ``sdc_core.mcp.tools``.

An application lists its tools in ``SDC_MCP['tools']``: dotted paths that name an ``McpTool``, a list of them, or a
function without arguments that returns them::

    # settings.py
    SDC_MCP = {'enabled': True, 'tools': ['my_app.mcp_tools.TOOLS']}
    SDC_API_TOKENS = {'app_privileges': {'lab:read': 'Read the measurements of the connected devices'}}

    # my_app/mcp_tools.py
    from sdc_core.mcp.app_tools import McpTool, READ_ONLY_OPEN_WORLD
    from sdc_core.mcp.tools import ToolError

    def _measurement(arguments, user, grant):
        device = Device.objects.filter(owner=user, pk=arguments['device']).first()
        if device is None:
            raise ToolError('Not found (or the user is not allowed to see it)')
        return device.read_measurement()

    TOOLS = [McpTool(
        name='device_measurement', title='Read a measurement',
        description='The latest measurement of one of the user\\'s devices.',
        input_schema={'type': 'object', 'additionalProperties': False, 'required': ['device'],
                      'properties': {'device': {'type': 'integer', 'description': 'Id of the device'}}},
        handler=_measurement, privileges=('lab:read',), annotations=READ_ONLY_OPEN_WORLD)]

Rules:

- ``handler(arguments, user, grant)`` gets the checked arguments, the token's user and its grant, and returns a
  JSON-serialisable value (or a string). **The handler itself decides which records the user may reach**; the
  privileges only decide whether the token may use the tool at all.
- ``privileges``: every one of them must be granted (``Grant.has``): application privileges
  (``SDC_API_TOKENS['app_privileges']``), ``model:<Name>:<read|write|delete>`` or ``account:*``. A tool needs at
  least one.
- Errors: ``ToolError``, ``PermissionDenied``, ``ObjectDoesNotExist`` and ``Http404`` go back to the AI model as
  error results. Any other exception is logged and answered with a generic error, so that no internal detail
  (paths, credentials in URLs, ...) reaches the client.
- ``annotations`` default to the most careful hints (not read-only, destructive, open world): clients then ask the
  user before each call. Pass ``READ_ONLY``, ``READ_ONLY_OPEN_WORLD`` or your own dict for harmless tools.
- Names: letters, digits, ``_`` and ``-``, at most 64 characters, and not the name of a generic tool.
- ``strict=True`` (default) checks the types, enums and ranges of the top-level arguments (``string``, ``integer``,
  ``number``, ``boolean``, ``object``, ``array``); ``strict=False`` only the required and unknown names.
"""
import re
from dataclasses import dataclass, field
from typing import Callable

from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

from sdc_core import api_tokens

READ_ONLY = {'readOnlyHint': True, 'destructiveHint': False, 'idempotentHint': True, 'openWorldHint': False}
# Reads data of an external system (another server, a device, ...)
READ_ONLY_OPEN_WORLD = {'readOnlyHint': True, 'destructiveHint': False, 'idempotentHint': True,
                        'openWorldHint': True}
CAREFUL = {'readOnlyHint': False, 'destructiveHint': True, 'idempotentHint': False, 'openWorldHint': True}

NAME_PATTERN = re.compile(r'^[A-Za-z0-9_-]{1,64}$')
SCHEMA_TYPES = ('string', 'integer', 'number', 'boolean', 'object', 'array')


@dataclass(frozen=True)
class McpTool:
    name: str
    description: str
    input_schema: dict
    handler: Callable
    privileges: tuple
    title: str = None
    annotations: dict = field(default_factory=lambda: dict(CAREFUL))
    strict: bool = True

    def definition(self):
        """The MCP tool definition (``tools/list``)."""
        result = {'name': self.name, 'title': self.title or self.name, 'description': self.description,
                  'inputSchema': self.input_schema, 'annotations': dict(self.annotations)}
        return result


def _check(tool, path, reserved):
    where = f"SDC_MCP['tools'] ({path})"
    if not isinstance(tool, McpTool):
        raise ImproperlyConfigured(f'{where}: {tool!r} is not an McpTool')
    if not isinstance(tool.name, str) or not NAME_PATTERN.match(tool.name):
        raise ImproperlyConfigured(f'{where}: invalid tool name {tool.name!r}')
    if tool.name in reserved:
        raise ImproperlyConfigured(f'{where}: the tool name {tool.name!r} is already used')
    if not callable(tool.handler):
        raise ImproperlyConfigured(f'{where}: the handler of {tool.name} is not callable')
    schema = tool.input_schema
    if not isinstance(schema, dict) or schema.get('type') != 'object' or \
            not isinstance(schema.get('properties'), dict):
        raise ImproperlyConfigured(f'{where}: the input schema of {tool.name} must be an object with "properties"')
    for name, prop in schema['properties'].items():
        if not isinstance(prop, dict) or prop.get('type') not in SCHEMA_TYPES:
            raise ImproperlyConfigured(f'{where}: the argument {name!r} of {tool.name} needs a "type" of '
                                       f'{", ".join(SCHEMA_TYPES)}')
    unknown_required = [name for name in schema.get('required', []) if name not in schema['properties']]
    if unknown_required:
        raise ImproperlyConfigured(f'{where}: {tool.name} requires unknown arguments: {", ".join(unknown_required)}')
    if isinstance(tool.privileges, str) or not tool.privileges:
        raise ImproperlyConfigured(f'{where}: {tool.name} needs a tuple of at least one privilege')
    try:
        normalized = api_tokens.normalize_privileges(list(tool.privileges))
    except api_tokens.TokenError as e:
        raise ImproperlyConfigured(f'{where}: {tool.name}: {e}')
    if len(normalized) != len(set(tool.privileges)):
        raise ImproperlyConfigured(f'{where}: {tool.name} lists a privilege twice')


def app_tools(reserved=()):
    """
    The tools of ``SDC_MCP['tools']``, checked, in the order they are configured. ``reserved``: names that are
    already taken (the generic tools). ``ImproperlyConfigured`` for invalid entries.
    """
    from sdc_core.mcp.settings import mcp_settings
    paths = mcp_settings().get('tools') or []
    if isinstance(paths, str):
        paths = [paths]
    result, names = [], set(reserved)
    for path in paths:
        try:
            value = import_string(path)
        except ImportError as e:
            raise ImproperlyConfigured(f"SDC_MCP['tools']: cannot import {path}: {e}")
        if callable(value) and not isinstance(value, McpTool):
            value = value()
        items = [value] if isinstance(value, McpTool) else list(value or [])
        for tool in items:
            _check(tool, path, names)
            names.add(tool.name)
            result.append(tool)
    return result
