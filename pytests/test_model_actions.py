"""Tests of ``sdc_core.sdc_extentions.model_actions`` beyond what the REST API tests cover (limit, grants)."""
import os

import django
import pytest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SdcTest.settings')
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.core.exceptions import PermissionDenied  # noqa: E402
from django.http import Http404  # noqa: E402

from main_test.models import Author  # noqa: E402
from sdc_core.sdc_extentions import model_actions  # noqa: E402

User = get_user_model()


class Grant:
    """Allows only the listed ``(model, privilege)`` pairs."""

    def __init__(self, *allowed):
        self.allowed = set(allowed)
        self.asked = []

    def allows(self, model_name, privilege):
        self.asked.append((model_name, privilege))
        return (model_name, privilege) in self.allowed


@pytest.fixture
def user(db):
    return User.objects.create_user(username='jane', password='x')


def test_load_with_limit(user):
    for i in range(5):
        Author.objects.create(name=f'A{i}', age=i)
    assert len(model_actions.load(user, 'Author', limit=3)) == 3
    assert len(model_actions.load(user, 'author')) == 5


def test_unknown_model(user):
    with pytest.raises(Http404):
        model_actions.load(user, 'NoSuchModel')


@pytest.mark.parametrize('call, privilege', [
    (lambda u, pk, g: model_actions.load(u, 'Author', grant=g), 'read'),
    (lambda u, pk, g: model_actions.get(u, 'Author', pk, grant=g), 'read'),
    (lambda u, pk, g: model_actions.create(u, 'Author', {'name': 'X', 'age': 1}, grant=g), 'write'),
    (lambda u, pk, g: model_actions.update(u, 'Author', pk, {'age': 1}, partial=True, grant=g), 'write'),
    (lambda u, pk, g: model_actions.delete(u, 'Author', pk, grant=g), 'delete'),
])
def test_grant_is_checked_before_the_model_rules(user, monkeypatch, call, privilege):
    authorised = []
    monkeypatch.setattr(Author, 'is_authorised',
                        classmethod(lambda cls, u, action, obj: authorised.append(action) or True))
    jane = Author.objects.create(name='Jane', age=40)

    grant = Grant()
    with pytest.raises(PermissionDenied, match=f'model:Author:{privilege}'):
        call(user, jane.pk, grant)
    assert grant.asked == [('Author', privilege)]
    assert authorised == []

    call(user, jane.pk, Grant(('Author', privilege)))
    assert len(authorised) == 1


def test_validation_error(user):
    with pytest.raises(model_actions.FormValidationError) as e:
        model_actions.create(user, 'Author', {'name': 'Jane'})
    assert list(e.value.errors) == ['age']
