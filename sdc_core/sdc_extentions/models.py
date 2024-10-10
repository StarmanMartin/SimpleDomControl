from asgiref.sync import async_to_sync
from django.conf import settings
from django.db.models import QuerySet
from django.template.loader import render_to_string
from django.db.models.signals import post_save, post_delete
from django.dispatch.dispatcher import receiver
from django.core.serializers.json import Serializer
from django.db.models import FileField
from django.apps import apps

from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model

from sdc_core.sdc_extentions.forms import AbstractSearchForm

User = get_user_model()

_ALL_MODELS = None


def all_models() -> dict[str,any]:
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


class SDCSerializer(Serializer):
    """
    The SDCSerializer serializes SdcModels for the API and websocket communication

    """

    def handle_m2m_field(self, obj, field):
        super().handle_m2m_field(obj, field)
        self._current[field.name] = {
            'pk': self._current[field.name],
            'model': field.related_model.__name__,
            '__is_sdc_model__': True
        }

    def _value_from_field(self, obj, field):
        if hasattr(field, 'foreign_related_fields') and all_models().get(
                field.related_model.__name__) == field.related_model:
            return {'pk': super()._value_from_field(obj, field), 'model': field.related_model.__name__,
                    '__is_sdc_model__': True}
        if issubclass(field.__class__, FileField):
            return field.value_from_object(obj).url
        return super()._value_from_field(obj, field)


_SDC_META_DEFAULT = {'edit_form': None,
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


class _SdcMetaDummy:
    _sdc_checked = False


class SdcModel():
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

    @classproperty
    def SdcMeta(cls):
        """
        SdcMeta is a metaclass that contains all the
        important metadata for rendering HTML views of instances.
        All class variable are python import sting

        :cvar edit_form: Import string to edit form class
        :cvar create_form: Import string to edit form class
        :cvar forms: Import string to edit form class

        """
        if not hasattr(cls, '_SdcMeta'):
            setattr(cls, '_SdcMeta', _SdcMetaDummy())

        sdc_meta = getattr(cls, '_SdcMeta')

        if not getattr(sdc_meta, '_sdc_checked', False):
            setattr(sdc_meta, '_sdc_checked', True)
            for k, v in _SDC_META_DEFAULT.items():
                if not hasattr(sdc_meta, k):
                    setattr(sdc_meta, k, getattr(cls, k, v))
        return sdc_meta

    @property
    def scope(self) -> dict[str: any]:
        """
        :return: Websocket scope object
        """
        return self._scope

    @scope.setter
    def scope(self, scope: dict[str: any]):
        """
        Set the Websocket scope object
        """
        self._scope = scope

    @classmethod
    def render(cls, template_name: str, context=None, request=None, using=None) -> str:
        return render_to_string(template_name=template_name, context=context, request=request, using=using)

    @classmethod
    def is_authorised(cls, user: User, action: str, obj: dict[str: any]) -> bool:
        return True

    @classmethod
    def get_queryset(cls, user: User, action: str, obj: dict[str: any]) -> QuerySet:
        raise NotImplemented

    @classmethod
    def data_load(cls, user: User, action: str, obj: dict[str: any]) -> QuerySet | None:
        return None


@receiver(post_save)  # instead of @receiver(post_save, sender=Rebel)
@receiver(post_delete)  # instead of @receiver(post_save, sender=Rebel)
def set_winner(sender, instance=None, created: bool = False, **kwargs):
    """
    Handles the client notification if an SDC model has been saved, created or deleted.

    :param sender: The modul class
    :param instance: Saved, created or deleted instance
    :param created: True if instance has no db id before it has been saved
    :param kwargs:
    """

    if instance is not None and hasattr(sender, '__is_sdc_model__'):
        serialize_instance = SDCSerializer().serialize([instance])
        if created:
            async_to_sync(get_channel_layer().group_send)(sender.__name__, {
                'event_id': 'none',
                'type': 'on_create',
                'pk': instance.pk,
                'args': {'data': serialize_instance},
                'is_error': False
            })
        else:
            async_to_sync(get_channel_layer().group_send)(sender.__name__, {
                'event_id': 'none',
                'type': 'on_update',
                'pk': instance.pk,
                'args': {'data': serialize_instance},
                'is_error': False
            })
