"""Forms with ``sdc_pass_user = True`` get the user who loads or submits them (``make_form``)."""
import json
import os

import django
import pytest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SdcTest.settings')
django.setup()

from django import forms  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.contrib.auth.models import AnonymousUser  # noqa: E402

from main_test.models import Author, Book  # noqa: E402
from sdc_core.consumers import SDCModelConsumer  # noqa: E402
from sdc_core.mcp.tools import _form_input_schema  # noqa: E402
from sdc_core.sdc_extentions import model_actions  # noqa: E402
from sdc_core.sdc_extentions.models import make_form  # noqa: E402
from sdc_core.sdc_extentions.schema import generate_form_schema  # noqa: E402

User = get_user_model()
SEEN = []


class OwnAuthorBookForm(forms.ModelForm):
    """Only offers the authors named like the user (a stand-in for "the user's own records")."""
    sdc_pass_user = True

    class Meta:
        model = Book
        fields = ('title', 'author')

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        SEEN.append(user)
        name = user.username if user is not None and user.is_authenticated else None
        self.fields['author'].queryset = Author.objects.filter(name=name)


class PlainBookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ('title', 'author')


@pytest.fixture(autouse=True)
def own_author_forms(monkeypatch):
    SEEN.clear()
    monkeypatch.setattr(Book.SdcMeta, 'create_form', OwnAuthorBookForm)
    monkeypatch.setattr(Book.SdcMeta, 'edit_form', OwnAuthorBookForm)


@pytest.fixture
def jane(db):
    return User.objects.create_user(username='jane', password='x')


@pytest.fixture
def authors(db):
    return Author.objects.create(name='jane', age=40), Author.objects.create(name='joe', age=50)


def test_make_form_passes_the_user_only_on_request(jane):
    make_form(OwnAuthorBookForm, jane)
    assert SEEN == [jane]
    # forms without the flag are built as before (no unexpected keyword argument)
    assert isinstance(make_form(PlainBookForm, jane), PlainBookForm)


def test_create_limits_choices_to_the_user(jane, authors):
    own, other = authors
    with pytest.raises(model_actions.FormValidationError) as error:
        model_actions.create(jane, 'Book', {'title': 'x', 'author': other.pk})
    assert 'author' in error.value.errors
    created = model_actions.create(jane, 'Book', {'title': 'y', 'author': own.pk})
    assert created['fields']['author'] == own.pk
    assert SEEN == [jane, jane]


def test_partial_update_gets_the_user(jane, authors):
    own, other = authors
    book = Book.objects.create(title='a', author=own)
    model_actions.update(jane, 'Book', book.pk, {'title': 'b'}, partial=True)
    # patch_data builds the form once to read its fields, then the form validates
    assert SEEN == [jane, jane]
    with pytest.raises(model_actions.FormValidationError):
        model_actions.update(jane, 'Book', book.pk, {'author': other.pk}, partial=True)


def test_schemas_build_the_form_without_a_user(db):
    schema, _files = generate_form_schema(OwnAuthorBookForm)
    assert 'author' in schema['properties']
    assert _form_input_schema(OwnAuthorBookForm, partial=False)['required'] == ['title', 'author']
    assert SEEN and all(user is None for user in SEEN)


class _Consumer(SDCModelConsumer):
    """The model consumer without a socket: sends are collected."""

    def __init__(self, user):
        super().__init__()
        self.scope = {'user': user, 'session': {}, 'event_type': 'create'}
        self.model = Book
        self.model_name = 'Book'
        self.model_id = None
        self.queryset = {}
        self.ids = []
        self.sent = []

    def send(self, text_data=None, bytes_data=None, close=False):
        self.sent.append(json.loads(text_data))


@pytest.mark.parametrize('submitter', ['jane', 'anonymous'])
def test_websocket_forms_get_the_user(jane, authors, submitter):
    user = jane if submitter == 'jane' else AnonymousUser()
    own, _other = authors
    consumer = _Consumer(user)
    consumer._create_element({'event_type': 'create', 'event_id': '1',
                              'args': {'data': {'title': 't', 'author': own.pk}}})
    assert SEEN == [user]
    assert Book.objects.filter(title='t').exists() == (submitter == 'jane')
