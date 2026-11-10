"""Tests of the MCP endpoint (``sdc_core.mcp``): transport, authentication, tools and resources."""
import datetime
import json
import os

import django
import pytest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SdcTest.settings')
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.contrib.auth.models import update_last_login  # noqa: E402
from django.test import Client, override_settings  # noqa: E402
from django.utils import timezone  # noqa: E402

from main_test.models import Author, BookContent  # noqa: E402
from pytests.test_ai_consumer import _write_skill_data  # noqa: E402
from sdc_core import api_tokens  # noqa: E402
from sdc_core.jwt_utils import generate_jwt  # noqa: E402
from sdc_core.mcp.view import PROTOCOL_VERSIONS  # noqa: E402
from sdc_core.models import ApiToken  # noqa: E402

User = get_user_model()
URL = '/sdc_mcp/'
# Without skill data, so that the tool list does not depend on the files of the test project
ENABLED = dict(SDC_MCP={'enabled': True}, SDC_AI_SKILL_DATA_FILE='missing.json', SDC_AI_SKILL_FILE='missing.md')


@pytest.fixture(autouse=True)
def enabled():
    with override_settings(**ENABLED):
        yield


@pytest.fixture
def user(db):
    return User.objects.create_user(username='jane', password='x', first_name='Jane')


def _secret(user, *privileges):
    return api_tokens.create_token(user, 'mcp', list(privileges))[1]


def _post(body, secret=None, **headers):
    if secret:
        headers['Authorization'] = f'Bearer {secret}'
    data = body if isinstance(body, str) else json.dumps(body)
    return Client(headers=headers).post(URL, data, content_type='application/json')


def _rpc(secret, method, params=None, id=1, **headers):
    message = {'jsonrpc': '2.0', 'id': id, 'method': method}
    if params is not None:
        message['params'] = params
    response = _post(message, secret, **headers)
    assert response.status_code == 200, response.content
    body = json.loads(response.content)
    assert body['id'] == id
    return body


def _result(secret, method, params=None):
    body = _rpc(secret, method, params)
    assert 'error' not in body, body
    return body['result']


def _call(secret, tool, **arguments):
    return _result(secret, 'tools/call', {'name': tool, 'arguments': arguments})


def _tool_names(secret):
    return [t['name'] for t in _result(secret, 'tools/list')['tools']]


# ------------------------------------------------------------------ transport

def test_disabled(user):
    with override_settings(SDC_MCP={'enabled': False}):
        assert _post({'jsonrpc': '2.0', 'id': 1, 'method': 'ping'}, _secret(user, 'account:read')).status_code == 404


def test_get_and_delete_are_not_offered(user):
    client = Client(headers={'Authorization': f"Bearer {_secret(user, 'account:read')}"})
    assert client.get(URL).status_code == 405
    assert client.delete(URL).status_code == 405


def test_initialize(user):
    secret = _secret(user, 'model:*:read')
    result = _result(secret, 'initialize', {'protocolVersion': '2025-06-18', 'capabilities': {},
                                            'clientInfo': {'name': 'test', 'version': '1'}})
    assert result['protocolVersion'] == '2025-06-18'
    assert result['capabilities'] == {'tools': {'listChanged': False}, 'resources': {'listChanged': False}}
    assert result['serverInfo']['name'] == 'SimpleDomControl'
    assert 'model_load' in result['instructions']
    # Unknown versions are answered with the newest one
    assert _result(secret, 'initialize', {'protocolVersion': '1999-01-01'})['protocolVersion'] == PROTOCOL_VERSIONS[0]


def test_instructions_contain_the_skill_index(user, tmp_path):
    _write_skill_data(tmp_path / 'SDC_SKILL.data.json')
    with override_settings(BASE_DIR=tmp_path, SDC_AI_SKILL_DATA_FILE=None):
        result = _result(_secret(user, 'model:*:read'), 'initialize', {'protocolVersion': '2025-06-18'})
    assert '- `Author` — An author of books.' in result['instructions']


def test_notifications_and_responses_are_accepted(user):
    secret = _secret(user, 'account:read')
    assert _post({'jsonrpc': '2.0', 'method': 'notifications/initialized'}, secret).status_code == 202
    assert _post({'jsonrpc': '2.0', 'id': 5, 'result': {}}, secret).status_code == 202


def test_ping(user):
    assert _result(_secret(user, 'account:read'), 'ping') == {}


def test_protocol_errors(user):
    secret = _secret(user, 'account:read')
    response = _post('{no json', secret)
    assert response.status_code == 400 and json.loads(response.content)['error']['code'] == -32700
    response = _post([{'jsonrpc': '2.0', 'id': 1, 'method': 'ping'}], secret)
    assert response.status_code == 400 and json.loads(response.content)['error']['code'] == -32600
    response = _post({'id': 1, 'method': 'ping'}, secret)
    assert response.status_code == 400
    assert _rpc(secret, 'nope/nothing')['error']['code'] == -32601
    assert _rpc(secret, 'tools/call', {'name': 3})['error']['code'] == -32602
    response = _post({'jsonrpc': '2.0', 'id': 1, 'method': 'ping', 'params': [1]}, secret)
    assert json.loads(response.content)['error']['code'] == -32602


def test_protocol_version_header(user):
    secret = _secret(user, 'account:read')
    assert _rpc(secret, 'ping', **{'MCP-Protocol-Version': '2025-06-18'})['result'] == {}
    response = _post({'jsonrpc': '2.0', 'id': 1, 'method': 'ping'}, secret, **{'MCP-Protocol-Version': '2020-01-01'})
    assert response.status_code == 400


def test_origin_of_other_sites_is_refused(user):
    secret = _secret(user, 'account:read')
    with override_settings(ALLOWED_HOSTS=['testserver', 'localhost']):
        message = {'jsonrpc': '2.0', 'id': 1, 'method': 'ping'}
        assert _post(message, secret, Origin='https://evil.example').status_code == 403
        assert _post(message, secret, Origin='http://localhost:8000').status_code == 200
        assert _post(message, secret).status_code == 200


# ------------------------------------------------------------------ authentication

def test_token_required(user):
    message = {'jsonrpc': '2.0', 'id': 1, 'method': 'ping'}
    response = _post(message)
    assert response.status_code == 401 and response['WWW-Authenticate'] == 'Bearer'
    assert _post(message, 'sdc_unknown').status_code == 401


def test_revoked_and_expired_tokens(user):
    token, secret = api_tokens.create_token(user, 'mcp', ['model:*:read'])
    message = {'jsonrpc': '2.0', 'id': 1, 'method': 'ping'}
    ApiToken.objects.filter(pk=token.pk).update(expires_at=timezone.now() - datetime.timedelta(seconds=1))
    assert json.loads(_post(message, secret).content)['error'] == 'Expired token'
    token.revoke()
    assert json.loads(_post(message, secret).content)['error'] == 'Revoked token'


def test_deprecated_jwt_is_refused(user):
    update_last_login(None, user)
    access, _refresh = generate_jwt(user)
    with pytest.warns(DeprecationWarning):
        response = _post({'jsonrpc': '2.0', 'id': 1, 'method': 'ping'}, access)
    assert response.status_code == 401


# ------------------------------------------------------------------ tool list

def test_tools_depend_on_the_privileges(user):
    assert _tool_names(_secret(user, 'account:read')) == ['account_get']
    assert _tool_names(_secret(user, 'model:Author:write')) == ['author_create', 'author_update']
    assert _tool_names(_secret(user, 'model:Author:read')) == ['model_get', 'model_load']
    tools = _result(_secret(user, 'model:Author:read', 'model:book:read'), 'tools/list')['tools']
    load = next(t for t in tools if t['name'] == 'model_load')
    assert load['inputSchema']['properties']['model']['enum'] == ['Author', 'Book']
    assert load['annotations']['readOnlyHint'] is True


def test_tools_respect_the_exposed_models(user, monkeypatch):
    secret = _secret(user, 'model:*:read')
    load = lambda: next(t for t in _result(secret, 'tools/list')['tools'] if t['name'] == 'model_load')  # noqa: E731
    assert load()['inputSchema']['properties']['model']['enum'] == ['Author', 'Book', 'BookContent', 'SdcUser']
    with override_settings(SDC_MCP={'enabled': True, 'models': ['book', 'Nope']}):
        assert load()['inputSchema']['properties']['model']['enum'] == ['Book']
    monkeypatch.setattr(Author.SdcMeta, 'mcp', False, raising=False)
    assert 'Author' not in load()['inputSchema']['properties']['model']['enum']


def test_describe_is_listed_with_skill_data(user, tmp_path):
    _write_skill_data(tmp_path / 'SDC_SKILL.data.json')
    secret = _secret(user, 'account:read')
    with override_settings(BASE_DIR=tmp_path, SDC_AI_SKILL_DATA_FILE=None):
        assert _tool_names(secret) == ['describe', 'account_get']
        result = _call(secret, 'describe', name='<SDC-Login>')
        assert not result['isError'] and '### `<sdc-login>`' in result['content'][0]['text']
        result = _call(secret, 'describe', name='logn')
        assert result['isError'] and 'Close matches: sdc-login' in result['content'][0]['text']


# ------------------------------------------------------------------ tool calls

def test_model_load(user):
    for i in range(5):
        Author.objects.create(name=f'A{i}', age=20 + i)
    secret = _secret(user, 'model:Author:read')
    result = _call(secret, 'model_load', model='Author', filter={'age__gte': 22}, limit=2)
    assert result['isError'] is False
    data = result['structuredContent']
    assert data['total'] == 3 and data['truncated'] is True and len(data['records']) == 2
    assert data['records'][0]['model'] == 'main_test.author'
    assert json.loads(result['content'][0]['text']) == data
    data = _call(secret, 'model_load', model='Author')['structuredContent']
    assert data['total'] == 5 and data['truncated'] is False


def test_model_load_respects_max_records(user):
    for i in range(4):
        Author.objects.create(name=f'A{i}', age=i)
    secret = _secret(user, 'model:Author:read')
    with override_settings(SDC_MCP={'enabled': True, 'max_records': 3}):
        assert len(_call(secret, 'model_load', model='Author')['structuredContent']['records']) == 3
        result = _call(secret, 'model_load', model='Author', limit=10)
        assert result['isError'] and 'limit must be between 1 and 3' in result['content'][0]['text']


def test_model_load_respects_get_queryset(user):
    other = User.objects.create_user(username='other', password='x')
    mine = BookContent.objects.create(user=user, text='mine.txt')
    foreign = BookContent.objects.create(user=other, text='other.txt')
    secret = _secret(user, 'model:*:read')
    records = _call(secret, 'model_load', model='BookContent')['structuredContent']['records']
    assert [r['pk'] for r in records] == [mine.pk]
    result = _call(secret, 'model_get', model='BookContent', id=foreign.pk)
    assert result['isError'] and 'Not found' in result['content'][0]['text']


def test_model_get(user):
    jane = Author.objects.create(name='Jane', age=40)
    result = _call(_secret(user, 'model:Author:read'), 'model_get', model='Author', id=jane.pk)
    assert result['structuredContent'] == {'model': 'main_test.author', 'pk': jane.pk,
                                           'fields': {'name': 'Jane', 'age': 40}}
    assert _call(_secret(user, 'model:Author:read'), 'model_get', model='Author', id=99999)['isError']


def test_user_rules_still_apply(user, monkeypatch):
    monkeypatch.setattr(Author, 'is_authorised', classmethod(lambda cls, u, action, obj: False))
    result = _call(_secret(user, 'model:*:read'), 'model_load', model='Author')
    assert result['isError'] and 'not allowed' in result['content'][0]['text']


@pytest.mark.parametrize('arguments, message', [
    ({}, 'Missing arguments: model'),
    ({'model': 'Book'}, 'model must be one of: Author'),
    ({'model': 'Author', 'extra': 1}, 'Unknown arguments: extra'),
    ({'model': 'Author', 'limit': '3'}, 'limit must be of type integer'),
    ({'model': 'Author', 'filter': {'secret': 1}}, "Filtering on 'secret' is not allowed"),
    ({'model': 'Author', 'filter': {'name__nonsense': 1}}, 'Invalid filter'),
    ({'model': 'Author', 'filter': {'age': 'old'}}, 'Invalid filter'),
])
def test_invalid_arguments_are_tool_errors(user, arguments, message):
    result = _result(_secret(user, 'model:Author:read'), 'tools/call', {'name': 'model_load', 'arguments': arguments})
    assert result['isError'] is True
    assert message in result['content'][0]['text']


def test_unavailable_tools_are_protocol_errors(user):
    secret = _secret(user, 'account:read')
    body = _rpc(secret, 'tools/call', {'name': 'model_load', 'arguments': {'model': 'Author'}})
    assert body['error']['code'] == -32602 and 'Unknown tool' in body['error']['message']


def test_account_get(user):
    result = _call(_secret(user, 'account:read'), 'account_get')
    assert result['structuredContent']['pk'] == user.pk
    assert 'password' not in result['structuredContent']['fields']


# ------------------------------------------------------------------ resources

def test_resources(user, tmp_path):
    (tmp_path / 'SDC_SKILL.md').write_text('# Skill')
    secret = _secret(user, 'account:read')
    with override_settings(BASE_DIR=tmp_path, SDC_AI_SKILL_FILE=None):
        uris = [r['uri'] for r in _result(secret, 'resources/list')['resources']]
        assert uris[0] == 'sdc://skill' and 'sdc://skill/sdc_user' in uris and uris[-1] == 'sdc://openapi'
        assert _result(secret, 'resources/read', {'uri': 'sdc://skill'})['contents'][0]['text'] == '# Skill'
    content = _result(secret, 'resources/read', {'uri': 'sdc://skill/sdc_user'})['contents'][0]
    assert content['mimeType'] == 'application/json' and '"sdc-api-tokens"' in content['text']
    content = _result(secret, 'resources/read', {'uri': 'sdc://openapi'})['contents'][0]
    assert '/sdc_api/tokens/' in content['text']
    assert _rpc(secret, 'resources/read', {'uri': 'sdc://nothing'})['error']['code'] == -32002
    assert _result(secret, 'resources/templates/list') == {'resourceTemplates': []}


# ------------------------------------------------------------------ write and delete tools (M4)

def _tool(secret, name):
    return next(t for t in _result(secret, 'tools/list')['tools'] if t['name'] == name)


def test_write_tools_follow_the_privileges(user):
    assert _tool_names(_secret(user, 'model:Author:delete')) == ['author_delete']
    names = _tool_names(_secret(user, 'model:*:write', 'model:*:delete'))
    assert {'author_create', 'author_update', 'author_delete', 'book_create', 'book_update', 'book_delete',
            'book_content_update', 'book_content_delete'} <= set(names)
    # BookContent needs a file to be created, which MCP cannot send
    assert 'book_content_create' not in names
    with override_settings(SDC_MCP={'enabled': True, 'models': ['Book']}):
        assert _tool_names(_secret(user, 'model:*:write')) == ['book_create', 'book_update']


def test_write_tool_schemas(user):
    secret = _secret(user, 'model:*:write', 'model:*:delete')
    create = _tool(secret, 'author_create')
    assert create['inputSchema']['required'] == ['name', 'age']
    assert create['inputSchema']['properties']['age'] == {'type': 'integer'}
    assert create['annotations'] == {'readOnlyHint': False, 'destructiveHint': False, 'idempotentHint': False,
                                     'openWorldHint': False}
    update = _tool(secret, 'author_update')
    assert update['inputSchema']['required'] == ['id'] and set(update['inputSchema']['properties']) == {
        'id', 'name', 'age'}
    assert update['annotations']['destructiveHint'] is True
    assert _tool(secret, 'author_delete')['annotations']['destructiveHint'] is True
    assert 'text' not in _tool(secret, 'book_content_update')['inputSchema']['properties']


def test_write_tool_schemas_match_the_openapi_description(user):
    from sdc_core.management.commands.sdc_open_api import build_openapi
    schemas = build_openapi()['components']['schemas']
    secret = _secret(user, 'model:*:write')
    for model in ('Author', 'Book'):
        create = _tool(secret, f'{model.lower()}_create')['inputSchema']
        assert create['properties'] == schemas[f'{model}Create']['properties']
        assert create['required'] == schemas[f'{model}Create']['required']
        update = _tool(secret, f'{model.lower()}_update')['inputSchema']
        assert {k: v for k, v in update['properties'].items() if k != 'id'} == schemas[f'{model}Patch']['properties']


def test_create(user):
    secret = _secret(user, 'model:Author:write')
    result = _call(secret, 'author_create', name='Jane', age=40)
    assert result['isError'] is False
    jane = Author.objects.get(name='Jane')
    assert result['structuredContent'] == {'model': 'main_test.author', 'pk': jane.pk,
                                           'fields': {'name': 'Jane', 'age': 40}}


def test_create_with_invalid_values(user):
    secret = _secret(user, 'model:Author:write')
    result = _call(secret, 'author_create', name='Jane', age='old')
    assert result['isError'] and 'Invalid values' in result['content'][0]['text']
    assert '"age"' in result['content'][0]['text']
    result = _call(secret, 'author_create', name='Jane')
    assert result['isError'] and 'Missing arguments: age' in result['content'][0]['text']
    result = _call(secret, 'author_create', name='Jane', age=1, extra=2)
    assert result['isError'] and 'Unknown arguments: extra' in result['content'][0]['text']
    assert not Author.objects.exists()


def test_update_is_partial(user):
    jane = Author.objects.create(name='Jane', age=40)
    result = _call(_secret(user, 'model:Author:write'), 'author_update', id=jane.pk, age=41)
    assert result['structuredContent']['fields'] == {'name': 'Jane', 'age': 41}
    jane.refresh_from_db()
    assert (jane.name, jane.age) == ('Jane', 41)
    result = _call(_secret(user, 'model:Author:write'), 'author_update', id=99999, age=1)
    assert result['isError'] and 'Not found' in result['content'][0]['text']
    result = _call(_secret(user, 'model:Author:write'), 'author_update', id='1', age=1)
    assert result['isError'] and 'id must be of type integer' in result['content'][0]['text']


def test_delete(user):
    jane = Author.objects.create(name='Jane', age=40)
    result = _call(_secret(user, 'model:Author:delete'), 'author_delete', id=jane.pk)
    assert result['structuredContent'] == {'deleted': True, 'model': 'Author', 'pk': jane.pk}
    assert not Author.objects.filter(pk=jane.pk).exists()
    assert _call(_secret(user, 'model:Author:delete'), 'author_delete', id=jane.pk)['isError']


def test_write_tools_respect_the_user(user, monkeypatch):
    other = User.objects.create_user(username='other', password='x')
    foreign = BookContent.objects.create(user=other, text='other.txt')
    secret = _secret(user, 'model:*:write', 'model:*:delete')
    assert _call(secret, 'book_content_update', id=foreign.pk)['isError']
    assert _call(secret, 'book_content_delete', id=foreign.pk)['isError']
    assert BookContent.objects.filter(pk=foreign.pk).exists()
    monkeypatch.setattr(Author, 'is_authorised', classmethod(lambda cls, u, action, obj: False))
    result = _call(secret, 'author_create', name='Jane', age=40)
    assert result['isError'] and not Author.objects.exists()


def test_write_tools_are_unavailable_without_privilege(user):
    jane = Author.objects.create(name='Jane', age=40)
    secret = _secret(user, 'model:Author:read', 'model:Author:write')
    body = _rpc(secret, 'tools/call', {'name': 'author_delete', 'arguments': {'id': jane.pk}})
    assert body['error']['code'] == -32602
    assert Author.objects.filter(pk=jane.pk).exists()


def test_account_update(user):
    assert 'account_update' not in _tool_names(_secret(user, 'account:read'))
    secret = _secret(user, 'account:write')
    tool = _tool(secret, 'account_update')
    assert set(tool['inputSchema']['properties']) == {'first_name', 'last_name'}
    result = _call(secret, 'account_update', first_name='Janet')
    assert result['isError'] is False and result['structuredContent']['fields']['first_name'] == 'Janet'
    for field, value in (('email', 'evil@example.com'), ('username', 'evil'), ('password', 'x')):
        result = _call(secret, 'account_update', **{field: value})
        assert result['isError'] and f'Unknown arguments: {field}' in result['content'][0]['text']
    user.refresh_from_db()
    assert user.first_name == 'Janet' and user.username == 'jane'
