from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist, PermissionDenied
from django.db.models import QuerySet
from django.db.models.constants import LOOKUP_SEP
from django.template.loader import render_to_string
from django.core.serializers.json import Serializer
from django.db.models import FileField
from django.apps import apps
from django.utils.module_loading import import_string

from django.contrib.auth import get_user_model

from sdc_core.sdc_extentions.forms import AbstractSearchForm

if TYPE_CHECKING:
    UserType = get_user_model()

_ALL_MODELS = None

class CaseInsensitiveDict(dict[str, Any]):
    """
    A dict whose keys can be looked up in any letter case. The keys keep their
    original spelling; each instance keeps its own lower-case key map.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.key_mapper = {key.lower(): key for key in self.keys()}

    def _mapped(self, key):
        if isinstance(key, str):
            return self.key_mapper.get(key.lower(), key)
        return key

    def __setitem__(self, key, value):
        if isinstance(key, str):
            self.key_mapper[key.lower()] = key
        super().__setitem__(key, value)

    def __getitem__(self, key):
        return super().__getitem__(self._mapped(key))

    def __contains__(self, key):
        return super().__contains__(self._mapped(key))

    def get(self, key, default=None):
        return super().get(self._mapped(key), default)


def all_models() -> CaseInsensitiveDict:
    """
    Collects and returns all SDC Models

    :return: all SDC models as a dict with keys are model names and the class as value
    """

    global _ALL_MODELS
    if _ALL_MODELS is None:
        _ALL_MODELS = CaseInsensitiveDict({
            model.__name__: model for model in apps.get_models() if hasattr(model, '__is_sdc_model__')
        })
    return _ALL_MODELS


def filter_model_fields(obj, data):
    """
    Restricts ``data`` (a dict keyed by model field name) to the fields exposed by
    ``SdcMeta.fields`` / ``SdcMeta.exclude``:

    - ``fields`` is ``None``, ``"__all__"`` or ``"*"``: all fields except those in
      ``exclude`` (if set).
    - ``fields`` is an iterable of names: only those fields. ``exclude`` must then
      be ``None``.
    """
    meta = getattr(obj, "SdcMeta", None)

    whitelist = getattr(meta, "fields", None)
    blacklist = getattr(meta, "exclude", None)
    all_fields = whitelist is None or whitelist == '__all__' or whitelist == '*'

    if all_fields:
        if not blacklist:
            return data
        if isinstance(blacklist, str) or not isinstance(blacklist, Iterable):
            raise Exception("SdcMeta.exclude must be None or an iterable of field names.")
        return {key: value for key, value in data.items() if key not in blacklist}

    if isinstance(whitelist, str) or not isinstance(whitelist, Iterable) or blacklist:
        raise Exception(
            "SdcMeta.fields and SdcMeta.exclude are mutually exclusive. If fields is a list of names, exclude must be None. "
            "To exclude fields, set fields to None or \"__all__\" and exclude to an iterable.")
    return {key: value for key, value in data.items() if key in whitelist}


def resolve_form(form_attr):
    """
    Returns the form class of an SdcMeta form setting (``edit_form``, ``create_form``
    or a named form): a dotted import path, a form class, or a callable (not a class)
    that is called with ``{}`` and returns one of them.
    """
    if callable(form_attr) and not isinstance(form_attr, type):
        form_attr = form_attr({})
    if form_attr is None:
        raise NotImplementedError("No form is defined for this SdcMeta setting.")
    if isinstance(form_attr, str):
        return import_string(form_attr)
    return form_attr


def make_form(form_class, user=None, **kwargs):
    """
    An instance of a model form. A form class with ``sdc_pass_user = True`` also gets ``user=``: the user who loads
    or submits it (``None`` where no user is involved, e.g. when a schema is generated). Such a form can limit its
    choices to the user's records, e.g. ``self.fields['project'].queryset = Project.objects.filter(owner=user)``.
    """
    if getattr(form_class, 'sdc_pass_user', False):
        kwargs['user'] = user
    return form_class(**kwargs)


def get_filterable_fields(model_cls) -> set[str]:
    """
    Returns the set of field names a client is allowed to filter on. Derived from
    the model's concrete fields, restricted by the same ``SdcMeta.fields`` /
    ``SdcMeta.exclude`` rules the serializer uses for output. ``pk`` and ``id``
    are always allowed.
    """
    field_names = {f.name for f in model_cls._meta.get_fields()}
    allowed = set(filter_model_fields(model_cls, {name: None for name in field_names}).keys())
    allowed.update({'pk', 'id'})
    return allowed


def _is_lookup_chain(field, segments) -> bool:
    """
    True if ``segments`` are transforms of ``field`` (``date``, a JSON key, ...), optionally ended by one lookup
    (``gte``, ``icontains``, ...). The name of a field of another model is neither.
    """
    for i, name in enumerate(segments):
        if field.get_transform(name) is not None:
            continue
        return field.get_lookup(name) is not None and i == len(segments) - 1
    return True


def check_filter_key(model_cls, key: str, allowed: set[str]) -> None:
    """
    ``PermissionDenied`` unless the filter key stays on ``model_cls``. Allowed are:

    - an exposed field of the model (:func:`get_filterable_fields`), followed only by transforms and one lookup
      (``title__icontains``, ``created__date__gte``);
    - a forward relation followed by the related primary key (``author__pk``, ``author__id``) or by a lookup of the
      relation itself (``author__in``, ``author__isnull``);
    - a one-hop path listed in ``SdcMeta.filter_relations`` (e.g. ``"author__name"``), followed only by lookups.

    Reverse relations are never filterable. Without this rule a key like
    ``owner__other_records__secret__startswith`` turns a filter on the user's own rows into an oracle for
    other users' data.
    """
    segments = key.split(LOOKUP_SEP)
    first, rest = segments[0], segments[1:]

    def refuse(reason='is not allowed'):
        raise PermissionDenied(f"Filtering on '{key}' {reason}")

    if first == 'pk':
        field = model_cls._meta.pk
    else:
        if first not in allowed:
            refuse()
        try:
            field = model_cls._meta.get_field(first)
        except FieldDoesNotExist:
            refuse()
    if field.is_relation and not field.concrete:
        refuse('follows a reverse relation, which is not allowed')
    if field.is_relation and rest:
        related = field.related_model
        hop = rest[0]
        relations = set(getattr(model_cls.SdcMeta, 'filter_relations', None) or ())
        if hop == 'pk' or hop == related._meta.pk.name:
            field, rest = related._meta.pk, rest[1:]
        elif f'{first}{LOOKUP_SEP}{hop}' in relations:
            try:
                field, rest = related._meta.get_field(hop), rest[1:]
            except FieldDoesNotExist:
                refuse()
            if field.is_relation and rest:
                refuse('follows a relation, which is not allowed')
        elif field.get_lookup(hop) is not None and len(rest) == 1:
            return
        else:
            refuse('follows a relation, which is not allowed (see SdcMeta.filter_relations)')
    if rest and not _is_lookup_chain(field, rest):
        refuse()


def sanitize_filter_query(model_cls, query) -> dict[str, Any]:
    """
    Validates client-supplied filter keys (REST, websocket, MCP) with :func:`check_filter_key`, so that neither
    hidden fields (``password__startswith``) nor other tables reached through relations can be probed. Raises
    ``PermissionDenied`` for a refused key. Returns a plain dict safe for ``filter(**...)``.
    """
    allowed = get_filterable_fields(model_cls)
    clean: dict[str, Any] = {}
    for key, value in query.items():
        check_filter_key(model_cls, key, allowed)
        clean[key] = value
    return clean


class SDCSerializer(Serializer):
    """
    The SDCSerializer serializes SdcModels for the API and websocket communication

    """

    def get_dump_object(self, obj):
        data = super().get_dump_object(obj)
        data['fields'] = filter_model_fields(obj, data['fields'])
        return data

    def handle_field(self, obj, field):
        value = field.value_from_object(obj)

        if isinstance(field, FileField):
            if not value:
                self._current[field.name] = None
                return

            self._current[field.name] = {
                "name": value.name.split("/")[-1],
                "url": value.url
            }
        else:
            super().handle_field(obj, field)

    def handle_fk_field(self, obj, field):
        super().handle_fk_field(obj, field)

    def handle_m2m_field(self, obj, field):
        super().handle_m2m_field(obj, field)
        self._current[field.name] = self._current[field.name]

    def _value_from_field(self, obj, field):
        if hasattr(field, 'foreign_related_fields') and all_models().get(
                field.related_model.__name__) == field.related_model:
            return super()._value_from_field(obj, field)
        if issubclass(field.__class__, FileField):
            try:
                return field.value_from_object(obj).url
            except (ValueError, TypeError):
                return None
        return super()._value_from_field(obj, field)


_SDC_META_DEFAULT = {
    'fields': '__all__',
    'exclude': None,
    'edit_form': None,
    'create_form': None,
    'html_list_template': None,
    'html_detail_template': None,
    'html_form_template': getattr(settings, 'MODEL_FORM_TEMPLATE', "elements/form.html"),
    'filter_relations': (),
}


class classproperty(property):
    def __get__(self, obj, objtype=None):
        return super().__get__(objtype)

    def __set__(self, obj, value):
        super().__set__(type(obj), value)



class SdcModel:
    """
    A Django Model which also extents the SdcModel class can be used as a Websocked based Client Model.
    Use the SDC management command new_model to create a new model class.
    """

    __is_sdc_model__ = True
    _scope = None

    class SearchForm(AbstractSearchForm):
        CHOICES = (("id", "Id"),)
        PLACEHOLDER = ""
        DEFAULT_CHOICES = CHOICES[0][0]
        SEARCH_FIELDS = ("id",)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        if hasattr(cls, "_SdcMeta"):
            setattr(cls, "SdcMeta", getattr(cls, '_SdcMeta'))

        child_meta = cls.__dict__.get("SdcMeta")

        # If subclass does NOT define Meta → create a NEW one
        if child_meta is None:
            cls.SdcMeta = type("SdcMeta", (), {})
            child_meta = cls.SdcMeta

        if not getattr(child_meta, '_sdc_checked', False):
            setattr(child_meta, '_sdc_checked', True)
            for k, v in _SDC_META_DEFAULT.items():
                if not hasattr(child_meta, k):
                    setattr(child_meta, k, getattr(cls, k, v))
        pass

    class SdcMeta:
        """
        SdcMeta is a metaclass that contains all the
        important metadata for rendering HTML views of instances.
        All class variable are python import sting

        :cvar edit_form: Import string to edit form class
        :cvar create_form: Import string to edit form class
        :cvar forms: Import string to edit form class

        """
        _sdc_checked = False

        @classmethod
        def on_disconnected(cls, qs: QuerySet):
            pass

    @property
    def scope(self) -> dict[str, Any]:
        """
        :return: Websocket scope object
        """
        return self._scope

    @scope.setter
    def scope(self, scope: dict[str, Any]):
        """
        Set the Websocket scope object
        """
        self._scope = scope

    @classmethod
    def render(cls, template_name: str, context=None, request=None, using=None) -> str:
        return render_to_string(template_name=template_name, context=context, request=request, using=using)

    @classmethod
    def is_authorised(cls, user: UserType, action: str, obj: dict[str, Any]) -> bool:
        # Deny by default: every SdcModel MUST override is_authorised to grant
        # access. Returning False here keeps models closed unless they opt in.
        return False

    @classmethod
    def get_queryset(cls, user: UserType, action: str, obj: dict[str, Any]) -> QuerySet:
        raise NotImplementedError()

    @classmethod
    def data_load(cls, user: UserType, queryset: QuerySet, model_query: dict[str, Any]) -> QuerySet | None:
        """
        Optional hook to load the rows for a WebSocket request yourself.

        :param user: the user of the connection
        :param queryset: the result of ``get_queryset()`` for this request
        :param model_query: the client filter, already checked against ``SdcMeta.fields`` / ``exclude``
        :return: the rows to use, or ``None`` for the default ``queryset.filter(**model_query)``
        """
        return None
