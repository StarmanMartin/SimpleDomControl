"""Client filters may not follow relations beyond what the model allows (``sanitize_filter_query``)."""
import os

import django
import pytest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SdcTest.settings')
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.core.exceptions import PermissionDenied  # noqa: E402

from main_test.models import Author, Book, BookContent  # noqa: E402
from sdc_core.sdc_extentions import model_actions  # noqa: E402
from sdc_core.sdc_extentions.models import sanitize_filter_query  # noqa: E402

User = get_user_model()


@pytest.mark.parametrize('model, key', [
    (Author, 'name'),
    (Author, 'name__icontains'),
    (Author, 'age__gte'),
    (Author, 'pk'),
    (Author, 'id__in'),
    (Book, 'author'),
    (Book, 'author__pk'),
    (Book, 'author__id'),
    (Book, 'author__in'),
    (Book, 'author__isnull'),
    (Book, 'author__name'),                 # listed in Book.SdcMeta.filter_relations
    (Book, 'author__name__icontains'),
])
def test_allowed_keys(model, key):
    assert sanitize_filter_query(model, {key: 1}) == {key: 1}


@pytest.mark.parametrize('model, key', [
    (Book, 'author__age'),                  # not listed in filter_relations
    (Book, 'author__age__gte'),
    (Book, 'author__book__title'),          # hop and back again
    (Book, 'author__name__book'),
    (Author, 'book'),                       # reverse relation
    (Author, 'book__pk'),
    (Author, 'book__title__startswith'),
    (Author, 'name__nonsense'),             # neither transform nor lookup
    (Author, 'name__icontains__exact'),     # nothing after the lookup
    (Author, 'unknown'),
])
def test_refused_keys(model, key):
    with pytest.raises(PermissionDenied):
        sanitize_filter_query(model, {key: 1})


def test_relation_paths_can_be_allowed_per_model(monkeypatch):
    with pytest.raises(PermissionDenied):
        sanitize_filter_query(Book, {'author__age': 1})
    monkeypatch.setattr(Book.SdcMeta, 'filter_relations', ('author__name', 'author__age'))
    assert sanitize_filter_query(Book, {'author__age__gte': 1})


def test_model_actions_refuse_a_relation_oracle(db):
    user = User.objects.create_user(username='jane', password='x')
    author = Author.objects.create(name='secret-name', age=1)
    Book.objects.create(title='t', author=author)
    with pytest.raises(PermissionDenied):
        model_actions.load(user, 'Author', {'book__title__startswith': 't'})
    assert len(model_actions.load(user, 'Book', {'author__name__startswith': 'secret'})) == 1


def test_models_without_relations_are_unchanged():
    # every concrete field of a model without relations stays filterable
    for field in BookContent._meta.concrete_fields:
        if not field.is_relation:
            sanitize_filter_query(BookContent, {field.name: 1})
