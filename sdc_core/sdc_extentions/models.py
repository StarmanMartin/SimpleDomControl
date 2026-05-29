from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.db.models import QuerySet
from django.template.loader import render_to_string
from django.core.serializers.json import Serializer
from django.db.models import FileField
from django.apps import apps

from django.contrib.auth import get_user_model

from sdc_core.sdc_extentions.forms import AbstractSearchForm

if TYPE_CHECKING:
    UserType = get_user_model()

_ALL_MODELS = None


def all_models() -> dict[str,Any]:
    """
    Collects and returns all SDC Models

    :return: all SDC models as a dict with keys are model names and the class as value
    """

    global _ALL_MODELS
    if _ALL_MODELS is None:
        _ALL_MODELS = {
            model.__name__: model for model in apps.get_models() if hasattr(model, '__is_sdc_model__')
        }
    return _ALL_MODELS


def filter_model_fields(obj, data):
    meta = getattr(obj, "SdcMeta", None)

    whitelist = getattr(meta, "fields", None)
    blacklist = getattr(meta, "exclude", None)
    if whitelist is None and blacklist is None or whitelist == '__all__' or whitelist == '*':
        return data
    filtered = {}

    if whitelist is None and isinstance(blacklist, Iterable):
        for key, value in data.items():
            if key not in blacklist:
                filtered[key] = value
    elif blacklist is None and isinstance(whitelist, Iterable):
        for key, value in data.items():
            if key in whitelist:
                filtered[key] = value
    else:
        raise Exception(
            "SdcMeta.fields and SdcMeta.exclude are mutually exclusive. If fields is set, exclude must be None and fields must be an iterable or \"__all__\". If exclude is set, fields must be None and exclude must be an iterable.")

    return filtered

class SDCSerializer(Serializer):
    """
    The SDCSerializer serializes SdcModels for the API and websocket communication

    """

    def get_dump_object(self, obj):
        data = super().get_dump_object(obj)

        return filter_model_fields(obj, data)

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
    'html_form_template': getattr(settings, 'MODEL_FORM_TEMPLATE', "elements/form.html")
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
        return True

    @classmethod
    def get_queryset(cls, user: UserType, action: str, obj: dict[str, Any]) -> QuerySet:
        raise NotImplemented

    @classmethod
    def data_load(cls, user: UserType, action: str, obj: dict[str, Any]) -> QuerySet | None:
        return None
