"""
Characterization tests of the REST API (``sdc_core.rest_api``: ``get_api_token`` and ``AdcApi``) on the models of
``main_test``. They pin the current behavior before the CRUD logic moves into ``model_actions``.
"""
import json
import os

import django
import pytest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SdcTest.settings')
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.contrib.auth.models import update_last_login  # noqa: E402
from django.test import Client, override_settings  # noqa: E402
from django.conf import settings  # noqa: E402

from main_test.models import Author, Book, BookContent  # noqa: E402
from sdc_core.jwt_utils import generate_jwt  # noqa: E402

User = get_user_model()
PASSWORD = 'a-secret-Pa55word'


@pytest.fixture
def user(db):
    user = User.objects.create_user(username='jane', password=PASSWORD)
    # Like the login endpoint: generate_jwt puts last_login into the access token, which must not be None
    update_last_login(None, user)
    return user


@pytest.fixture
def token(user):
    access, _refresh = generate_jwt(user)
    return access


@pytest.fixture
def api(token):
    """A test client that sends the access token of ``user``."""
    return Client(headers={'Authorization': f'Bearer {token}'})


def _json(response):
    return json.loads(response.content)


def _send(api, method, url, data, content_type='application/json'):
    body = json.dumps(data) if content_type == 'application/json' else data
    return getattr(api, method)(url, body, content_type=content_type)


# ------------------------------------------------------------------ token

def test_login_returns_tokens(user):
    response = Client().post('/sdc_api/login', json.dumps({'username': 'jane', 'password': PASSWORD}),
                             content_type='application/json')
    assert response.status_code == 200
    body = _json(response)
    assert body['token_type'] == 'bearer'
    assert body['access_token'] and body['refresh_token']


@pytest.mark.parametrize('payload, status, error', [
    ({'username': 'jane', 'password': 'wrong'}, 401, 'Invalid credentials'),
    ({'username': 'jane'}, 400, 'Missing credentials'),
])
def test_login_refused(user, payload, status, error):
    response = Client().post('/sdc_api/login', json.dumps(payload), content_type='application/json')
    assert response.status_code == status
    assert _json(response)['error'] == error


def test_login_invalid_json(user):
    response = Client().post('/sdc_api/login', '{no json', content_type='application/json')
    assert response.status_code == 400
    assert _json(response)['error'] == 'Invalid JSON'


def test_refresh_with_refresh_token(user):
    login = _json(Client().post('/sdc_api/login', json.dumps({'username': 'jane', 'password': PASSWORD}),
                                content_type='application/json'))
    response = Client(headers={'Authorization': f"Bearer {login['refresh_token']}"}).get('/sdc_api/login')
    assert response.status_code == 200
    assert _json(response)['access_token']


def test_refresh_with_access_token_is_refused(user):
    login = _json(Client().post('/sdc_api/login', json.dumps({'username': 'jane', 'password': PASSWORD}),
                                content_type='application/json'))
    response = Client(headers={'Authorization': f"Bearer {login['access_token']}"}).get('/sdc_api/login')
    assert response.status_code == 401
    assert _json(response)['error'] == 'Invalid token'


def test_refresh_token_is_invalid_after_a_new_login(user):
    """Current behavior (see mcp.plan.md, M2): refresh tokens are bound to ``last_login``."""
    import datetime
    from sdc_core.jwt_utils import generate_jwt as gen
    _access, refresh = gen(user)
    User.objects.filter(pk=user.pk).update(
        last_login=datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=5))
    response = Client(headers={'Authorization': f'Bearer {refresh}'}).get('/sdc_api/login')
    assert response.status_code == 401


def test_api_requires_a_token(db):
    response = Client().get('/sdc_api/Author')
    assert response.status_code == 401
    assert _json(response)['error'] == 'Missing Authorization header'


def test_api_requires_a_bearer_header(token):
    response = Client(headers={'Authorization': f'Token {token}'}).get('/sdc_api/Author')
    assert response.status_code == 401
    assert _json(response)['error'] == 'Invalid Authorization header'


def test_api_refuses_an_invalid_token(db):
    response = Client(headers={'Authorization': 'Bearer not-a-jwt'}).get('/sdc_api/Author')
    assert response.status_code == 401
    assert _json(response)['error'] == 'Invalid token'


def test_api_refuses_an_expired_token(user):
    with override_settings(JWT=settings.JWT | {'exp_delta_seconds': -10}):
        access, _refresh = generate_jwt(user)
    response = Client(headers={'Authorization': f'Bearer {access}'}).get('/sdc_api/Author')
    assert response.status_code == 401
    assert _json(response)['error'] == 'Expired token'


def test_api_refuses_a_refresh_token(user):
    _access, refresh = generate_jwt(user)
    response = Client(headers={'Authorization': f'Bearer {refresh}'}).get('/sdc_api/Author')
    assert response.status_code == 401
    assert _json(response)['error'] == 'Invalid token'


def test_api_refuses_the_token_of_a_deleted_user(api, user):
    user.delete()
    response = api.get('/sdc_api/Author')
    assert response.status_code == 401
    assert _json(response)['error'] == 'User not found'


def test_api_refuses_the_token_of_an_inactive_user(api, user):
    User.objects.filter(pk=user.pk).update(is_active=False)
    response = api.get('/sdc_api/Author')
    assert response.status_code == 401
    assert _json(response)['error'] == 'Invalid token'


# ------------------------------------------------------------------ read

def test_list(api):
    jane = Author.objects.create(name='Jane', age=40)
    Author.objects.create(name='John', age=50)
    response = api.get('/sdc_api/Author')
    assert response.status_code == 200
    body = _json(response)
    assert body['success'] is True
    assert {a['fields']['name'] for a in body['data']} == {'Jane', 'John'}
    first = next(a for a in body['data'] if a['pk'] == jane.pk)
    assert first == {'model': 'main_test.author', 'pk': jane.pk, 'fields': {'name': 'Jane', 'age': 40}}


def test_list_model_name_is_case_insensitive(api):
    Author.objects.create(name='Jane', age=40)
    assert len(_json(api.get('/sdc_api/author'))['data']) == 1


def test_list_with_filter(api):
    Author.objects.create(name='Jane', age=40)
    Author.objects.create(name='John', age=50)
    data = _json(api.get('/sdc_api/Author', {'age__gte': 45}))['data']
    assert [a['fields']['name'] for a in data] == ['John']


def test_list_with_forbidden_filter(api):
    response = api.get('/sdc_api/Author', {'secret__startswith': 'a'})
    assert response.status_code == 403
    assert b"Filtering on 'secret__startswith' is not allowed" in response.content


def test_list_respects_get_queryset(api, user):
    other = User.objects.create_user(username='other', password=PASSWORD)
    mine = BookContent.objects.create(user=user, text='mine.txt')
    BookContent.objects.create(user=other, text='other.txt')
    data = _json(api.get('/sdc_api/BookContent'))['data']
    assert [c['pk'] for c in data] == [mine.pk]
    assert data[0]['fields']['text'] == {'name': 'mine.txt', 'url': f'{settings.MEDIA_URL}mine.txt'}


def test_get_single(api):
    jane = Author.objects.create(name='Jane', age=40)
    response = api.get(f'/sdc_api/Author/{jane.pk}')
    assert response.status_code == 200
    assert _json(response) == {'success': True, 'data': {'model': 'main_test.author', 'pk': jane.pk,
                                                         'fields': {'name': 'Jane', 'age': 40}}}


def test_get_single_missing(api):
    assert api.get('/sdc_api/Author/999999').status_code == 404


def test_get_single_outside_get_queryset(api):
    other = User.objects.create_user(username='other', password=PASSWORD)
    foreign = BookContent.objects.create(user=other, text='other.txt')
    assert api.get(f'/sdc_api/BookContent/{foreign.pk}').status_code == 404


def test_unknown_model(api):
    assert api.get('/sdc_api/NoSuchModel').status_code == 404


def test_not_authorised(api, monkeypatch):
    monkeypatch.setattr(Author, 'is_authorised', classmethod(lambda cls, user, action, obj: False))
    jane = Author.objects.create(name='Jane', age=40)
    assert api.get('/sdc_api/Author').status_code == 403
    assert api.get(f'/sdc_api/Author/{jane.pk}').status_code == 403
    assert _send(api, 'post', '/sdc_api/Author', {'name': 'X', 'age': 1}).status_code == 403
    assert _send(api, 'patch', f'/sdc_api/Author/{jane.pk}', {'age': 1}).status_code == 403
    assert api.delete(f'/sdc_api/Author/{jane.pk}').status_code == 403
    assert Author.objects.get(pk=jane.pk).age == 40


def test_is_authorised_gets_action_and_query(api, monkeypatch):
    calls = []

    def is_authorised(cls, user, action, obj):
        calls.append((user.username, action, dict(obj)))
        return True

    monkeypatch.setattr(Author, 'is_authorised', classmethod(is_authorised))
    jane = Author.objects.create(name='Jane', age=40)
    api.get('/sdc_api/Author', {'name': 'Jane'})
    api.get(f'/sdc_api/Author/{jane.pk}')
    _send(api, 'post', '/sdc_api/Author', {'name': 'X', 'age': 1})
    _send(api, 'patch', f'/sdc_api/Author/{jane.pk}', {'age': 41})
    api.delete(f'/sdc_api/Author/{jane.pk}')
    assert calls == [('jane', 'load', {'name': 'Jane'}), ('jane', 'load', {'pk': jane.pk}),
                     ('jane', 'create', {}), ('jane', 'save', {}), ('jane', 'delete', {'pk': jane.pk})]


# ------------------------------------------------------------------ create

def test_create_json(api):
    response = _send(api, 'post', '/sdc_api/Author', {'name': 'Jane', 'age': 40})
    assert response.status_code == 200
    body = _json(response)
    jane = Author.objects.get(name='Jane')
    assert body == {'success': True, 'data': {'model': 'main_test.author', 'pk': jane.pk,
                                              'fields': {'name': 'Jane', 'age': 40}}}


def test_create_form_encoded(api):
    response = api.post('/sdc_api/Author', {'name': 'Jane', 'age': '40'})
    assert response.status_code == 200
    assert Author.objects.get(name='Jane').age == 40


def test_create_with_foreign_key(api):
    jane = Author.objects.create(name='Jane', age=40)
    response = _send(api, 'post', '/sdc_api/Book', {'title': 'Dune', 'author': jane.pk})
    assert response.status_code == 200
    assert _json(response)['data']['fields'] == {'title': 'Dune', 'author': jane.pk}
    assert Book.objects.get(title='Dune').author == jane


def test_create_invalid(api):
    response = _send(api, 'post', '/sdc_api/Author', {'name': 'Jane'})
    assert response.status_code == 400
    body = _json(response)
    assert body['success'] is False
    assert list(body['errors']) == ['age']
    assert not Author.objects.exists()


def test_create_with_invalid_json_body(api):
    response = api.post('/sdc_api/Author', '[1, 2]', content_type='application/json')
    assert response.status_code == 400
    assert _json(response) == {'success': False, 'error': 'Invalid request body: The JSON body must be an object'}


def test_create_on_the_object_url(api):
    jane = Author.objects.create(name='Jane', age=40)
    response = _send(api, 'post', f'/sdc_api/Author/{jane.pk}', {'name': 'X', 'age': 1})
    assert response.status_code == 405
    assert _json(response)['success'] is False


# ------------------------------------------------------------------ update

def test_put(api):
    jane = Author.objects.create(name='Jane', age=40)
    response = _send(api, 'put', f'/sdc_api/Author/{jane.pk}', {'name': 'Janet', 'age': 41})
    assert response.status_code == 200
    assert _json(response)['data']['fields'] == {'name': 'Janet', 'age': 41}
    jane.refresh_from_db()
    assert (jane.name, jane.age) == ('Janet', 41)


def test_put_is_not_partial(api):
    jane = Author.objects.create(name='Jane', age=40)
    response = _send(api, 'put', f'/sdc_api/Author/{jane.pk}', {'age': 41})
    assert response.status_code == 400
    assert list(_json(response)['errors']) == ['name']


def test_patch_json(api):
    jane = Author.objects.create(name='Jane', age=40)
    response = _send(api, 'patch', f'/sdc_api/Author/{jane.pk}', {'age': 41})
    assert response.status_code == 200
    assert _json(response)['data']['fields'] == {'name': 'Jane', 'age': 41}


def test_patch_form_encoded(api):
    jane = Author.objects.create(name='Jane', age=40)
    response = _send(api, 'patch', f'/sdc_api/Author/{jane.pk}', 'age=42',
                     content_type='application/x-www-form-urlencoded')
    assert response.status_code == 200
    jane.refresh_from_db()
    assert (jane.name, jane.age) == ('Jane', 42)


def test_patch_invalid(api):
    jane = Author.objects.create(name='Jane', age=40)
    response = _send(api, 'patch', f'/sdc_api/Author/{jane.pk}', {'age': 'old'})
    assert response.status_code == 400
    assert list(_json(response)['errors']) == ['age']
    jane.refresh_from_db()
    assert jane.age == 40


def test_update_missing(api):
    assert _send(api, 'patch', '/sdc_api/Author/999999', {'age': 1}).status_code == 404


def test_update_outside_get_queryset(api):
    other = User.objects.create_user(username='other', password=PASSWORD)
    foreign = BookContent.objects.create(user=other, text='other.txt')
    assert _send(api, 'patch', f'/sdc_api/BookContent/{foreign.pk}', {}).status_code == 404


def test_update_on_the_list_url(api):
    assert _send(api, 'put', '/sdc_api/Author', {'name': 'X', 'age': 1}).status_code == 405


# ------------------------------------------------------------------ delete

def test_delete(api):
    jane = Author.objects.create(name='Jane', age=40)
    response = api.delete(f'/sdc_api/Author/{jane.pk}')
    assert response.status_code == 200
    assert _json(response) == {'success': True}
    assert not Author.objects.filter(pk=jane.pk).exists()


def test_delete_missing(api):
    assert api.delete('/sdc_api/Author/999999').status_code == 404


def test_delete_outside_get_queryset(api):
    other = User.objects.create_user(username='other', password=PASSWORD)
    foreign = BookContent.objects.create(user=other, text='other.txt')
    assert api.delete(f'/sdc_api/BookContent/{foreign.pk}').status_code == 404
    assert BookContent.objects.filter(pk=foreign.pk).exists()


def test_delete_on_the_list_url(api):
    assert api.delete('/sdc_api/Author').status_code == 405
