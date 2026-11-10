"""
Read, create, change and delete records of SdcModels on behalf of a user, independent of the channel (REST API,
MCP, ...). Every action checks, in this order:

1. that the model exists (``Http404``),
2. the privileges of the caller's ``grant`` (an API token may narrow the user's rights; ``FULL`` allows everything),
3. the model's own rules: ``is_authorised`` and ``get_queryset`` with the actions ``load``, ``create``, ``save`` and
   ``delete`` (``PermissionDenied``; records outside ``get_queryset`` raise the model's ``DoesNotExist``).

Records are returned in the format of the ``SDCSerializer``: ``{"model": ..., "pk": ..., "fields": {...}}``.
"""
import json

from django.core.exceptions import PermissionDenied
from django.forms.models import model_to_dict
from django.http import Http404, QueryDict

from sdc_core.sdc_extentions.models import SDCSerializer, all_models, resolve_form, sanitize_filter_query

READ = 'read'
WRITE = 'write'
DELETE = 'delete'


class FormValidationError(Exception):
    """The submitted data does not pass the model's form; ``errors`` is the form's ``ErrorDict``."""

    def __init__(self, errors):
        super().__init__('Invalid data')
        self.errors = errors


class MissingPrivilege(PermissionDenied):
    """The caller's grant (API token) lacks ``privilege``, e.g. ``model:Book:write`` or ``account:tokens``."""

    def __init__(self, privilege):
        super().__init__(f"The token lacks the privilege {privilege}")
        self.privilege = privilege


class _FullGrant:
    """
    Allows every privilege: the rights of the user, not narrowed by a token (web session, WebSocket). Grants of
    API tokens are ``sdc_core.api_tokens.Grant``.
    """
    is_full = True

    def allows(self, model_name, privilege):
        return True

    def allows_account(self, privilege):
        return True

    def models(self, privilege):
        return set(all_models().keys())


FULL = _FullGrant()


def get_model(model_name):
    """The SdcModel class of ``model_name`` (any letter case); ``Http404`` if there is none."""
    model = all_models().get(model_name)
    if model is None:
        raise Http404(f"Model: {model_name} not found")
    return model


def _check_grant(grant, model, privilege):
    if not grant.allows(model.__name__, privilege):
        raise MissingPrivilege(f"model:{model.__name__}:{privilege}")


def _check_authorised(model, user, action, query):
    if not model.is_authorised(user, action, query):
        raise PermissionDenied()


def serialize(instances):
    return json.loads(SDCSerializer().serialize(instances))


def _load_queryset(user, model_name, query, grant):
    model = get_model(model_name)
    query = sanitize_filter_query(model, query or {})
    _check_grant(grant, model, READ)
    _check_authorised(model, user, 'load', query)
    return model.get_queryset(user, 'load', query).filter(**query)


def load(user, model_name, query=None, limit=None, grant=FULL):
    """
    The records of the model that match ``query`` (Django field lookups on the exposed fields) and that
    ``get_queryset`` gives the user; at most ``limit`` records if it is set.
    """
    records = _load_queryset(user, model_name, query, grant)
    if limit is not None:
        records = records[:limit]
    return serialize(records)


def load_page(user, model_name, query=None, limit=None, grant=FULL):
    """Like ``load``, returns ``(records, total)``: ``total`` is the number of matching records without limit."""
    records = _load_queryset(user, model_name, query, grant)
    total = records.count()
    if limit is not None:
        records = records[:limit]
    return serialize(records), total


def get(user, model_name, pk, grant=FULL):
    """One record by its primary key."""
    model = get_model(model_name)
    query = {'pk': pk}
    _check_grant(grant, model, READ)
    _check_authorised(model, user, 'load', query)
    return serialize([model.get_queryset(user, 'load', query).get(**query)])[0]


def create(user, model_name, data, files=None, grant=FULL):
    """Creates a record with the model's ``create_form``; ``FormValidationError`` if the data is invalid."""
    model = get_model(model_name)
    _check_grant(grant, model, WRITE)
    _check_authorised(model, user, 'create', {})
    form_class = resolve_form(model.SdcMeta.create_form)
    form = form_class(instance=None, data=data, files=files)
    if not form.is_valid():
        raise FormValidationError(form.errors)
    return serialize([form.save()])[0]


def update(user, model_name, pk, data, files=None, partial=False, grant=FULL):
    """
    Changes a record with the model's ``edit_form``. ``partial``: fields missing in ``data`` keep their current
    values; otherwise ``data`` must contain every required field.
    """
    model = get_model(model_name)
    query = {'pk': pk}
    _check_grant(grant, model, WRITE)
    _check_authorised(model, user, 'save', {})
    instance = model.get_queryset(user, 'save', query).get(**query)
    form_class = resolve_form(model.SdcMeta.edit_form)
    if partial:
        data = patch_data(form_class, instance, data)
    form = form_class(instance=instance, data=data, files=files)
    if not form.is_valid():
        raise FormValidationError(form.errors)
    return serialize([form.save()])[0]


def delete(user, model_name, pk, grant=FULL):
    """Deletes a record."""
    model = get_model(model_name)
    query = {'pk': pk}
    _check_grant(grant, model, DELETE)
    _check_authorised(model, user, 'delete', query)
    model.get_queryset(user, 'delete', query).get(**query).delete()


def patch_data(form_class, instance, data):
    """Form data for a partial update: the current values, overwritten by the submitted ones."""
    field_names = list(form_class(instance=instance).fields.keys())
    current = model_to_dict(instance, fields=field_names)
    if isinstance(data, QueryDict):
        merged = QueryDict(mutable=True)
        for key, value in current.items():
            values = value if isinstance(value, list) else [value]
            merged.setlist(key, ['' if v is None else v for v in values])
        for key in data.keys():
            merged.setlist(key, data.getlist(key))
        return merged
    return current | dict(data)
