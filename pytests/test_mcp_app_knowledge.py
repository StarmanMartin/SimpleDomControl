"""The application's own MCP instructions (``SDC_MCP['instructions_extra']``) and resources (``SDC_MCP['resources']``)."""
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
from sdc_core.mcp import resources  # noqa: E402

User = get_user_model()
URL = '/sdc_mcp/'
BASE = dict(SDC_AI_SKILL_DATA_FILE='missing.json', SDC_AI_SKILL_FILE='missing.md')


@pytest.fixture
def secret(db):
    user = User.objects.create_user(username='jane', password='x')
    return api_tokens.create_token(user, 'mcp', ['account:read'])[1]


@pytest.fixture
def docs(tmp_path):
    (tmp_path / 'docs').mkdir()
    (tmp_path / 'docs' / 'recipe.md').write_text('# Recipe\n1. do this', encoding='utf-8')
    (tmp_path / 'docs' / 'keys.txt').write_text('a.b.c', encoding='utf-8')
    (tmp_path / 'secret.txt').write_text('TOP SECRET', encoding='utf-8')
    return tmp_path


def _rpc(secret, method, params=None):
    response = Client(headers={'Authorization': f'Bearer {secret}'}).post(
        URL, json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}}),
        content_type='application/json')
    assert response.status_code == 200, response.content
    return json.loads(response.content)


def _settings(docs, **mcp):
    return override_settings(BASE_DIR=docs, SDC_MCP={'enabled': True, **mcp}, **BASE)


RESOURCES = [{'name': 'recipe', 'path': 'docs/recipe.md', 'title': 'Recipe', 'description': 'How to map'},
             {'name': 'key-paths', 'path': 'docs/keys.txt'}]


def test_extra_instructions_and_resource_list_are_in_the_instructions(secret, docs):
    with _settings(docs, instructions_extra='Always finish a sync model.', resources=RESOURCES):
        text = _rpc(secret, 'initialize', {'protocolVersion': '2025-06-18'})['result']['instructions']
    assert text.startswith('MCP server of the website')
    assert 'Always finish a sync model.' in text
    assert '- `sdc://app/recipe`: Recipe (How to map)' in text
    assert '- `sdc://app/key-paths`: key-paths' in text


def test_without_settings_the_instructions_are_unchanged(secret, docs):
    with _settings(docs):
        text = _rpc(secret, 'initialize', {'protocolVersion': '2025-06-18'})['result']['instructions']
    assert 'sdc://app/' not in text and 'Documentation of this website' not in text


def test_list_and_read(secret, docs):
    with _settings(docs, resources=RESOURCES):
        listed = {r['uri']: r for r in _rpc(secret, 'resources/list')['result']['resources']}
        assert listed['sdc://app/recipe'] == {'uri': 'sdc://app/recipe', 'name': 'recipe', 'title': 'Recipe',
                                             'description': 'How to map', 'mimeType': 'text/markdown'}
        assert listed['sdc://app/key-paths']['mimeType'] == 'text/plain'
        content = _rpc(secret, 'resources/read', {'uri': 'sdc://app/recipe'})['result']['contents'][0]
    assert content == {'uri': 'sdc://app/recipe', 'mimeType': 'text/markdown', 'text': '# Recipe\n1. do this'}


@pytest.mark.parametrize('uri', ['sdc://app/secret', 'sdc://app/../secret.txt', 'sdc://app/docs/recipe.md',
                                 'sdc://app/', 'sdc://app/recipe/../../secret.txt'])
def test_only_configured_names_can_be_read(secret, docs, uri):
    with _settings(docs, resources=RESOURCES):
        error = _rpc(secret, 'resources/read', {'uri': uri})['error']
    assert error['code'] == -32002


def test_a_missing_file_is_not_listed(secret, docs):
    with _settings(docs, resources=[{'name': 'gone', 'path': 'docs/gone.md'}]):
        uris = [r['uri'] for r in _rpc(secret, 'resources/list')['result']['resources']]
        assert 'sdc://app/gone' not in uris
        assert _rpc(secret, 'resources/read', {'uri': 'sdc://app/gone'})['error']['code'] == -32002


@pytest.mark.parametrize('configured', [
    {'name': 'x'},
    [{'name': 'bad name', 'path': 'docs/recipe.md'}],
    [{'name': 'x', 'path': 'a'}, {'name': 'x', 'path': 'b'}],
    [{'path': 'docs/recipe.md'}],
])
def test_invalid_configurations(docs, configured):
    with _settings(docs, resources=configured), pytest.raises(ImproperlyConfigured):
        resources.app_resources()
