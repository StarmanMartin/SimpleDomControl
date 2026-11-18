"""Tests of the application's own MCP tools (``SDC_MCP['tools']``) and application privileges."""
import json
import os

import django
import pytest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SdcTest.settings')
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.core.exceptions import ImproperlyConfigured  # noqa: E402
from django.test import Client, override_settings  # noqa: E402

from sdc_core import api_tokens  # noqa: E402
from sdc_core.mcp import tools as mcp_tools  # noqa: E402
from pytests import mcp_app_tools_fixture as fixture  # noqa: E402
from pytests.mcp_app_tools_fixture import CALLS, SCHEMA, TOOLS, _echo  # noqa: E402
from sdc_core.mcp.app_tools import CAREFUL, READ_ONLY_OPEN_WORLD, McpTool, app_tools  # noqa: E402
from sdc_core.sdc_extentions.model_actions import FULL  # noqa: E402

User = get_user_model()
URL = '/sdc_mcp/'
APP_PRIVILEGES = {'lab:read': 'Read the devices', 'lab:write': {'description': 'Steer the devices',
                                                                 'presets': ['read_write', 'full']}}
TOOLS_PATH = 'pytests.mcp_app_tools_fixture.TOOLS'
@pytest.fixture(autouse=True)
def settings_():
    CALLS.clear()
    with override_settings(SDC_MCP={'enabled': True, 'tools': [TOOLS_PATH]},
                           SDC_API_TOKENS={'app_privileges': APP_PRIVILEGES},
                           SDC_AI_SKILL_DATA_FILE='missing.json', SDC_AI_SKILL_FILE='missing.md'):
        yield


@pytest.fixture
def user(db):
    return User.objects.create_user(username='jane', password='x')


def _secret(user, *privileges):
    return api_tokens.create_token(user, 'mcp', list(privileges))[1]


def _rpc(secret, method, params=None):
    response = Client(headers={'Authorization': f'Bearer {secret}'}).post(
        URL, json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}}),
        content_type='application/json')
    assert response.status_code == 200, response.content
    return json.loads(response.content)


def _tools(secret):
    return {t['name']: t for t in _rpc(secret, 'tools/list')['result']['tools']}


def _call(secret, name, **arguments):
    return _rpc(secret, 'tools/call', {'name': name, 'arguments': arguments})


# ------------------------------------------------------------------ privileges

def test_app_privileges_are_valid_token_privileges():
    assert api_tokens.normalize_privileges(['lab:read', 'account:read']) == ['account:read', 'lab:read']
    with pytest.raises(api_tokens.TokenError):
        api_tokens.normalize_privileges(['lab:delete'])


@pytest.mark.parametrize('name', ['Lab:read', 'model:read', 'account:x', 'lab', 'lab:read:x', 'lab:*'])
def test_invalid_app_privilege_names(name):
    with override_settings(SDC_API_TOKENS={'app_privileges': {name: 'x'}}):
        with pytest.raises(ImproperlyConfigured):
            api_tokens.app_privileges()


def test_unknown_preset_is_refused():
    with override_settings(SDC_API_TOKENS={'app_privileges': {'lab:read': {'presets': ['admin']}}}):
        with pytest.raises(ImproperlyConfigured):
            api_tokens.app_privileges()


def test_presets_and_full_access():
    presets = api_tokens.presets()
    assert 'lab:read' in presets['full'] and 'lab:read' not in presets['read']
    assert 'lab:write' in presets['read_write'] and 'lab:write' in presets['full']
    assert api_tokens.PRESETS['full'] == api_tokens.FULL_ACCESS  # the constants stay unchanged
    assert {'lab:read', 'lab:write'} <= set(api_tokens.full_access())


def test_model_wildcard_does_not_include_app_privileges():
    grant = api_tokens.Grant(api_tokens.FULL_ACCESS)
    assert not grant.has('lab:read')
    assert grant.has('model:Author:read') and grant.has('account:read')
    assert api_tokens.Grant(['lab:read']).has('lab:read')
    assert FULL.has('lab:read')


def test_tokens_cannot_create_tokens_with_more_app_privileges(user):
    parent, _ = api_tokens.create_token(user, 'parent', ['account:tokens', 'lab:read'])
    api_tokens.create_token(user, 'child', ['lab:read'], created_by_token=parent)
    with pytest.raises(api_tokens.TokenError):
        api_tokens.create_token(user, 'child', ['lab:write'], created_by_token=parent)


# ------------------------------------------------------------------ listing

def test_tools_follow_the_privileges(user):
    assert 'lab_read' not in _tools(_secret(user, 'model:*:read', 'account:read'))
    listed = _tools(_secret(user, 'lab:read'))
    assert {'lab_read', 'lab_fails', 'lab_refuses'} <= set(listed) and 'lab_steer' not in listed
    # every privilege of a tool is needed
    assert 'lab_steer' not in _tools(_secret(user, 'lab:write'))
    assert 'lab_steer' in _tools(_secret(user, 'lab:write', 'model:*:read'))


def test_definition(user):
    tool = _tools(_secret(user, 'lab:read'))['lab_read']
    assert tool == {'name': 'lab_read', 'title': 'Read a device', 'description': 'Reads a device.',
                    'inputSchema': SCHEMA, 'annotations': READ_ONLY_OPEN_WORLD}
    # careful annotations by default, the name as title
    steer = _tools(_secret(user, 'lab:write', 'model:*:read'))['lab_steer']
    assert steer['annotations'] == CAREFUL and steer['title'] == 'lab_steer'


def test_a_function_can_provide_the_tools(user):
    with override_settings(SDC_MCP={'enabled': True, 'tools': ['pytests.mcp_app_tools_fixture.tool_factory']}):
        assert [t.name for t in app_tools()] == ['lab_read']


@pytest.mark.parametrize('tool', [
    McpTool(name='model_load', description='', input_schema={'type': 'object', 'properties': {}},
            handler=_echo, privileges=('lab:read',)),
    McpTool(name='author_create', description='', input_schema={'type': 'object', 'properties': {}},
            handler=_echo, privileges=('lab:read',)),
    McpTool(name='bad name', description='', input_schema={'type': 'object', 'properties': {}},
            handler=_echo, privileges=('lab:read',)),
    McpTool(name='x', description='', input_schema={'type': 'object', 'properties': {}}, handler=_echo,
            privileges=()),
    McpTool(name='x', description='', input_schema={'type': 'object', 'properties': {}}, handler=_echo,
            privileges='lab:read'),
    McpTool(name='x', description='', input_schema={'type': 'object', 'properties': {}}, handler=_echo,
            privileges=('lab:unknown',)),
    McpTool(name='x', description='', input_schema={'type': 'object'}, handler=_echo, privileges=('lab:read',)),
    McpTool(name='x', description='', input_schema={'type': 'object', 'properties': {'a': {}}}, handler=_echo,
            privileges=('lab:read',)),
    McpTool(name='x', description='', input_schema={'type': 'object', 'properties': {}, 'required': ['a']},
            handler=_echo, privileges=('lab:read',)),
])
def test_invalid_tools_are_refused(tool, monkeypatch):
    monkeypatch.setattr(fixture, 'TOOLS', [tool])
    with pytest.raises(ImproperlyConfigured):
        app_tools(reserved=mcp_tools.generic_tool_names())


def test_duplicate_names_are_refused(monkeypatch):
    monkeypatch.setattr(fixture, 'TOOLS', TOOLS[:1] * 2)
    with pytest.raises(ImproperlyConfigured):
        app_tools()


def test_unknown_path_is_refused():
    with override_settings(SDC_MCP={'enabled': True, 'tools': ['pytests.nothing.TOOLS']}):
        with pytest.raises(ImproperlyConfigured):
            app_tools()


# ------------------------------------------------------------------ calls

def test_call(user):
    result = _call(_secret(user, 'lab:read'), 'lab_read', device=3, full=True, factor=1.5, view='paths',
                   keys=['a'])['result']
    assert not result['isError']
    assert result['structuredContent'] == {'echo': {'device': 3, 'full': True, 'factor': 1.5, 'view': 'paths',
                                                    'keys': ['a']}, 'user': 'jane'}


@pytest.mark.parametrize('arguments, message', [
    ({}, 'Missing arguments: device'),
    ({'device': 1, 'other': 1}, 'Unknown arguments: other'),
    ({'device': True}, 'device must be of type integer'),
    ({'device': 1, 'full': 1}, 'full must be of type boolean'),
    ({'device': 1, 'factor': '1'}, 'factor must be of type number'),
    ({'device': 1, 'factor': 11}, 'factor must be between 0 and 10'),
    ({'device': 1, 'view': 'xml'}, 'view must be one of: json, paths'),
    ({'device': 1, 'keys': [1]}, 'keys must be a list of strings'),
])
def test_arguments_are_checked(user, arguments, message):
    result = _call(_secret(user, 'lab:read'), 'lab_read', **arguments)['result']
    assert result == {'content': [{'type': 'text', 'text': message}], 'isError': True}
    assert CALLS == []


def test_tool_without_privilege_is_unknown(user):
    body = _call(_secret(user, 'model:*:read'), 'lab_read', device=1)
    assert body['error']['message'] == 'Unknown tool: lab_read'
    assert CALLS == []


def test_unexpected_errors_are_hidden(user, caplog):
    result = _call(_secret(user, 'lab:read'), 'lab_fails')['result']
    assert result['isError']
    text = result['content'][0]['text']
    assert text == 'The tool lab_fails failed; the details are in the server log'
    assert 'password' not in text
    assert 'secret detail' in caplog.text


@pytest.mark.parametrize('kind, message', [('tool', 'No such device'), ('permission', 'Not your device')])
def test_expected_errors_reach_the_model(user, kind, message):
    result = _call(_secret(user, 'lab:read'), 'lab_refuses', kind=kind)['result']
    assert result == {'content': [{'type': 'text', 'text': message}], 'isError': True}


def test_invalid_configuration_is_an_internal_error(user, monkeypatch):
    monkeypatch.setattr(fixture, 'TOOLS', ['not a tool'])
    body = _rpc(_secret(user, 'lab:read'), 'tools/list')
    assert body['error']['message'] == 'Internal error'


def test_without_tools_setting_nothing_changes(user):
    with override_settings(SDC_MCP={'enabled': True}):
        assert not any(name.startswith('lab_') for name in _tools(_secret(user, 'lab:read', 'model:*:read')))
