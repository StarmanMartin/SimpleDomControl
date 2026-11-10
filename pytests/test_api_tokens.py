"""
Tests of the API tokens (``sdc_core.api_tokens``, ``sdc_core.models.ApiToken``): creation, privileges, the token
and account endpoints of the REST API and ``manage.py sdc_tokens``.
"""
import datetime
import io
import json
import os

import django
import pytest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SdcTest.settings')
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.core.management.base import CommandError  # noqa: E402
from django.test import Client, override_settings  # noqa: E402
from django.utils import timezone  # noqa: E402

from main_test.models import Author, BookContent  # noqa: E402
from sdc_core import api_tokens  # noqa: E402
from sdc_core.api_tokens import Grant, TokenError, create_token, hash_token, normalize_privileges  # noqa: E402
from sdc_core.models import ApiToken  # noqa: E402

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='jane', password='x', email='jane@example.com', first_name='Jane')


@pytest.fixture
def other(db):
    return User.objects.create_user(username='other', password='x')


def _client(secret):
    return Client(headers={'Authorization': f'Bearer {secret}'})


def _token(user, *privileges, **kwargs):
    return create_token(user, kwargs.pop('name', 'test'), list(privileges), **kwargs)


def _json(response):
    return json.loads(response.content)


def _post(client, url, data):
    return client.post(url, json.dumps(data), content_type='application/json')


def _patch(client, url, data):
    return client.patch(url, json.dumps(data), content_type='application/json')


# ------------------------------------------------------------------ creation

def test_create_stores_only_the_hash(user):
    token, secret = _token(user, 'model:*:read')
    assert secret.startswith('sdc_') and len(secret) > 40
    assert token.prefix == secret[:12]
    assert token.secret_hash == hash_token(secret) != secret
    assert secret not in json.dumps(api_tokens.token_to_dict(token), default=str)
    assert token.kind == 'personal'


def test_default_and_maximum_lifetime(user):
    token, _ = _token(user, 'account:read')
    assert abs(token.expires_at - timezone.now() - datetime.timedelta(days=90)) < datetime.timedelta(minutes=1)
    with pytest.raises(TokenError, match='at most 365 days'):
        _token(user, 'account:read', expires_at=timezone.now() + datetime.timedelta(days=400))
    with pytest.raises(TokenError, match='at most 365 days'):
        _token(user, 'account:read', expires_at=None)
    with pytest.raises(TokenError, match='future'):
        _token(user, 'account:read', expires_at=timezone.now() - datetime.timedelta(days=1))
    with override_settings(SDC_API_TOKENS={'max_lifetime_days': None, 'default_lifetime_days': None}):
        assert _token(user, 'account:read')[0].expires_at is None


def test_normalize_privileges():
    assert normalize_privileges(['model:author:read', 'model:Author:read', 'account:tokens', 'model:*:delete']) == \
        ['account:tokens', 'model:*:delete', 'model:Author:read']
    for wrong, message in ((['model:Author:admin'], 'Unknown privilege'), (['account:delete'], 'Unknown privilege'),
                           (['model:Nope:read'], 'Unknown model'), ('model:*:read', 'list of strings')):
        with pytest.raises(TokenError, match=message):
            normalize_privileges(wrong)


def test_name_and_privileges_are_required(user):
    with pytest.raises(TokenError, match='name'):
        _token(user, 'account:read', name=' ')
    with pytest.raises(TokenError, match='at least one privilege'):
        _token(user)


def test_grant():
    grant = Grant(['model:*:read', 'model:Author:write', 'account:read'])
    assert grant.allows('Book', 'read') and grant.allows('author', 'write')
    assert not grant.allows('Book', 'write') and not grant.allows('Author', 'delete')
    assert grant.models('write') == {'Author'}
    assert grant.allows_account('account:read') and not grant.allows_account('account:tokens')
    assert grant.covers(['model:Book:read', 'model:Author:write'])
    assert not grant.covers(['model:*:write']) and not grant.covers(['account:tokens'])


# ------------------------------------------------------------------ authentication

def test_last_used_is_throttled(user):
    token, secret = _token(user, 'model:*:read')
    _client(secret).get('/sdc_api/Author/')
    token.refresh_from_db()
    first = token.last_used_at
    assert first is not None and token.last_used_ip == '127.0.0.1'
    _client(secret).get('/sdc_api/Author/')
    token.refresh_from_db()
    assert token.last_used_at == first
    ApiToken.objects.filter(pk=token.pk).update(last_used_at=first - datetime.timedelta(minutes=2))
    _client(secret).get('/sdc_api/Author/')
    token.refresh_from_db()
    assert token.last_used_at > first


# ------------------------------------------------------------------ model privileges

@pytest.mark.parametrize('privilege', ['read', 'write', 'delete'])
def test_privilege_matrix(user, privilege):
    _token_, secret = _token(user, f'model:Author:{privilege}')
    client = _client(secret)
    jane = Author.objects.create(name='Jane', age=40)
    status = {
        'read': (client.get('/sdc_api/Author/').status_code,
                 client.get(f'/sdc_api/Author/{jane.pk}/').status_code),
        'write': (_post(client, '/sdc_api/Author/', {'name': 'X', 'age': 1}).status_code,
                  _patch(client, f'/sdc_api/Author/{jane.pk}/', {'age': 41}).status_code),
        'delete': (client.delete(f'/sdc_api/Author/{jane.pk}/').status_code,),
    }
    for name, codes in status.items():
        assert set(codes) == ({200} if name == privilege else {403}), name
    # Other models are not covered
    assert client.get('/sdc_api/Book/').status_code == 403


def test_missing_privilege_response(user):
    _token_, secret = _token(user, 'model:Author:write')
    response = _client(secret).get('/sdc_api/Author/')
    assert response.status_code == 403
    assert _json(response) == {'success': False, 'error': 'The token lacks the privilege model:Author:read',
                               'privilege': 'model:Author:read'}
    assert response['WWW-Authenticate'] == 'Bearer error="insufficient_scope", scope="model:Author:read"'


def test_wildcard_privilege(user):
    _token_, secret = _token(user, 'model:*:read')
    assert _client(secret).get('/sdc_api/Book/').status_code == 200
    assert _client(secret).get('/sdc_api/Author/').status_code == 200
    assert _post(_client(secret), '/sdc_api/Author/', {'name': 'X', 'age': 1}).status_code == 403


def test_token_never_exceeds_the_user(user, other, monkeypatch):
    _token_, secret = _token(user, *api_tokens.FULL_ACCESS)
    foreign = BookContent.objects.create(user=other, text='other.txt')
    assert _client(secret).get(f'/sdc_api/BookContent/{foreign.pk}/').status_code == 404
    assert _client(secret).delete(f'/sdc_api/BookContent/{foreign.pk}/').status_code == 404
    monkeypatch.setattr(Author, 'is_authorised', classmethod(lambda cls, u, action, obj: False))
    assert _client(secret).get('/sdc_api/Author/').status_code == 403


# ------------------------------------------------------------------ token endpoints

def test_list_own_tokens(user, other):
    _token(other, 'account:read')
    mine, secret = _token(user, 'account:read', name='mine')
    response = _client(secret).get('/sdc_api/tokens/')
    assert response.status_code == 200
    data = _json(response)['data']
    assert [t['id'] for t in data] == [str(mine.id)]
    assert data[0]['name'] == 'mine' and data[0]['prefix'] == mine.prefix and 'secret_hash' not in data[0]
    assert _client(secret).get(f'/sdc_api/tokens/{mine.id}/').status_code == 200


def test_list_needs_account_read(user):
    _token_, secret = _token(user, 'model:*:read')
    assert _client(secret).get('/sdc_api/tokens/').status_code == 403


def test_current_token(user):
    token, secret = _token(user, 'model:Author:read')
    response = _client(secret).get('/sdc_api/tokens/current/')
    assert response.status_code == 200
    assert _json(response)['data']['id'] == str(token.id)


def test_create_token_through_the_api(user):
    parent, secret = _token(user, 'account:tokens', 'model:*:read')
    response = _post(_client(secret), '/sdc_api/tokens/', {'name': 'child', 'privileges': ['model:Author:read']})
    assert response.status_code == 201
    body = _json(response)
    child = ApiToken.objects.get(pk=body['data']['id'])
    assert child.secret_hash == hash_token(body['token'])
    assert child.created_by_token == parent and child.privileges == ['model:Author:read']
    assert child.expires_at <= parent.expires_at
    assert _client(body['token']).get('/sdc_api/Author/').status_code == 200


def test_created_token_without_privileges_gets_those_of_its_creator(user):
    _parent, secret = _token(user, 'account:tokens', 'model:*:read')
    body = _json(_post(_client(secret), '/sdc_api/tokens/', {'name': 'child'}))
    assert body['data']['privileges'] == ['account:tokens', 'model:*:read']


def test_created_token_cannot_exceed_its_creator(user):
    _parent, secret = _token(user, 'account:tokens', 'model:Author:read')
    for privileges in (['model:*:read'], ['model:Author:write'], ['account:write']):
        response = _post(_client(secret), '/sdc_api/tokens/', {'name': 'child', 'privileges': privileges})
        assert response.status_code == 400
        assert 'more privileges' in _json(response)['error']
    response = _post(_client(secret), '/sdc_api/tokens/', {'name': 'child', 'privileges': ['account:tokens'],
                                                           'expires_at': None})
    assert response.status_code == 400


def test_create_needs_account_tokens(user):
    _token_, secret = _token(user, 'account:read', 'model:*:read')
    response = _post(_client(secret), '/sdc_api/tokens/', {'name': 'x', 'privileges': ['model:*:read']})
    assert response.status_code == 403
    assert _json(response)['privilege'] == 'account:tokens'


def test_create_with_invalid_input(user):
    _token_, secret = _token(user, 'account:tokens', 'model:*:read')
    assert _post(_client(secret), '/sdc_api/tokens/', {'name': 'x', 'expires_at': 'tomorrow'}).status_code == 400
    assert _client(secret).post('/sdc_api/tokens/', '[]', content_type='application/json').status_code == 400


def test_revoke_cascades_to_created_tokens(user):
    parent, secret = _token(user, 'account:tokens', 'model:*:read')
    child = _json(_post(_client(secret), '/sdc_api/tokens/', {'name': 'child'}))
    grandchild = _json(_post(_client(child['token']), '/sdc_api/tokens/', {'name': 'grandchild'}))
    _sibling, sibling_secret = _token(user, 'account:tokens', 'model:*:read')

    response = _client(sibling_secret).delete(f'/sdc_api/tokens/{parent.id}/')
    assert response.status_code == 200
    assert _json(response)['data']['revoked_at'] is not None
    for secret_ in (secret, child['token'], grandchild['token']):
        assert _json(_client(secret_).get('/sdc_api/Author/'))['error'] == 'Revoked token'
    assert _client(sibling_secret).get('/sdc_api/Author/').status_code == 200
    # Revoked tokens stay in the list
    parent.refresh_from_db()
    assert parent.revoked_by == user and ApiToken.objects.filter(user=user).count() == 4


def test_cannot_revoke_a_foreign_token(user, other):
    foreign, foreign_secret = _token(other, 'model:*:read')
    _token_, secret = _token(user, 'account:tokens')
    assert _client(secret).delete(f'/sdc_api/tokens/{foreign.id}/').status_code == 404
    assert _client(foreign_secret).get('/sdc_api/Author/').status_code == 200


def test_a_token_can_revoke_itself(user):
    token, secret = _token(user, 'account:tokens')
    assert _client(secret).delete(f'/sdc_api/tokens/{token.id}/').status_code == 200
    assert _client(secret).get('/sdc_api/tokens/current/').status_code == 401


def test_revoke_needs_account_tokens(user):
    token, secret = _token(user, 'account:read')
    assert _client(secret).delete(f'/sdc_api/tokens/{token.id}/').status_code == 403


# ------------------------------------------------------------------ account endpoint

def test_account_read(user):
    _token_, secret = _token(user, 'account:read')
    response = _client(secret).get('/sdc_api/account/')
    assert response.status_code == 200
    data = _json(response)['data']
    assert data['pk'] == user.pk and data['fields']['username'] == 'jane'
    assert 'password' not in data['fields']
    _token_, no_account = _token(user, 'model:*:read')
    assert _client(no_account).get('/sdc_api/account/').status_code == 403


def test_account_write(user):
    _token_, secret = _token(user, 'account:write')
    response = _patch(_client(secret), '/sdc_api/account/', {'first_name': 'Janet'})
    assert response.status_code == 200, response.content
    user.refresh_from_db()
    assert user.first_name == 'Janet' and user.email == 'jane@example.com'


@pytest.mark.parametrize('field, value', [('password', 'new-Pa55word!'), ('email', 'evil@example.com'),
                                          ('username', 'evil'), ('is_superuser', True)])
def test_account_write_never_changes_protected_fields(user, field, value):
    _token_, secret = _token(user, *api_tokens.FULL_ACCESS)
    response = _patch(_client(secret), '/sdc_api/account/', {field: value, 'first_name': 'Janet'})
    assert response.status_code == 403
    assert field in response.content.decode()
    user.refresh_from_db()
    assert user.first_name == 'Jane' and user.check_password('x') and user.email == 'jane@example.com'
    assert user.username == 'jane' and not user.is_superuser


def test_account_write_needs_account_write(user):
    _token_, secret = _token(user, 'account:read', 'model:*:write')
    assert _patch(_client(secret), '/sdc_api/account/', {'first_name': 'Janet'}).status_code == 403


# ------------------------------------------------------------------ manage.py sdc_tokens

def test_sdc_tokens_command(user):
    out = io.StringIO()
    call_command('sdc_tokens', 'create', '--user', 'jane', '--name', 'cli', '--privileges', 'read', stdout=out)
    secret = out.getvalue().strip().splitlines()[-1]
    token = ApiToken.objects.get(secret_hash=hash_token(secret))
    assert token.privileges == ['account:read', 'model:*:read']

    out = io.StringIO()
    call_command('sdc_tokens', 'list', '--user', 'jane', stdout=out)
    assert token.prefix in out.getvalue() and secret not in out.getvalue()

    call_command('sdc_tokens', 'revoke', token.prefix, stdout=io.StringIO())
    token.refresh_from_db()
    assert token.is_revoked
    out = io.StringIO()
    call_command('sdc_tokens', 'list', stdout=out)
    assert token.prefix not in out.getvalue()

    with pytest.raises(CommandError, match='Unknown privilege'):
        call_command('sdc_tokens', 'create', '--user', 'jane', '--name', 'x', '--privileges', 'model:*:all')
    with pytest.raises(CommandError, match='No user'):
        call_command('sdc_tokens', 'create', '--user', 'nobody', '--name', 'x')


# ------------------------------------------------------------------ <sdc-api-tokens> (sdc_user)

VIEW = '/sdc_view/sdc_user/sdc_api_tokens'


def _server_call(client, function, **data):
    response = client.post(VIEW, {'_method': 'sdc_server_call', '_sdc_func_name': function,
                                  'data': json.dumps(data)})
    return response.status_code, _json(response)


def test_token_view_lists_the_own_tokens(user, other):
    _token(user, 'model:*:read', name='my laptop')
    _token(other, 'model:*:read', name='foreign')
    client = Client()
    client.force_login(user)
    response = client.get(VIEW, {'_method': 'content'})
    assert response.status_code == 200
    html = _json(response)['html']
    assert 'my laptop' in html and 'foreign' not in html
    assert 'value="model:Author:delete"' in html and 'value="account:tokens"' in html


def test_token_view_needs_login(db):
    response = Client().get(VIEW, {'_method': 'content'})
    assert response.status_code == 301 and _json(response)['url'].startswith('.~sdc-login')
    status, body = _server_call(Client(), 'create_token', name='x', privileges='read')
    assert status == 301 and body['status'] == 'redirect'
    assert not ApiToken.objects.exists()


def test_token_view_creates_and_revokes(user, other):
    client = Client()
    client.force_login(user)
    status, body = _server_call(client, 'create_token', name='laptop', privileges='read_write', days='30')
    assert status == 200
    secret = body['_return_data']['token']
    token = ApiToken.objects.get(secret_hash=hash_token(secret))
    assert token.user == user and token.privileges == ['account:read', 'model:*:read', 'model:*:write']
    assert abs(token.expires_at - timezone.now() - datetime.timedelta(days=30)) < datetime.timedelta(minutes=1)

    _status, body = _server_call(client, 'create_token', name='custom',
                                 privileges=['model:Author:read', 'account:tokens'])
    assert ApiToken.objects.get(pk=body['_return_data']['id']).privileges == ['account:tokens', 'model:Author:read']

    status, _body = _server_call(client, 'create_token', name='forever', privileges='read', days='never')
    assert status != 200 and not ApiToken.objects.filter(name='forever').exists()

    foreign, _ = _token(other, 'model:*:read')
    status, _body = _server_call(client, 'revoke_token', token_id=str(foreign.id))
    foreign.refresh_from_db()
    assert status != 200 and not foreign.is_revoked
    status, _body = _server_call(client, 'revoke_token', token_id='not-a-uuid')
    assert status != 200
    status, _body = _server_call(client, 'revoke_token', token_id=str(token.id))
    token.refresh_from_db()
    assert status == 200 and token.is_revoked
