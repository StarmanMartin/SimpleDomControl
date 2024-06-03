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

User = get_user_model()

_ALL_MODELS = None

def all_models():
    global _ALL_MODELS
    if _ALL_MODELS is None:
        _ALL_MODELS = {
            model.__name__: model for model in apps.get_models() if hasattr(model, '__is_sdc_model__')
        }
    return _ALL_MODELS

class ConsumerSerializer(Serializer):

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

class SdcModel():
    __is_sdc_model__ = True
    edit_form = None
    create_form = None
    html_list_template = None
    html_detail_template = None
    html_form_template = getattr(settings, 'MODEL_FORM_TEMPLATE', "elements/form.html")
    apply_filter = None
    _scope = None

    @property
    def scope(self) -> dict[str: any]:
        return self._scope

    @scope.setter
    def scope(self, scope: dict[str: any]):
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
    def data_load(cls, user: User, action: str, obj: dict[str: any]) -> QuerySet|None:
        return None


@receiver(post_save)  # instead of @receiver(post_save, sender=Rebel)
@receiver(post_delete)  # instead of @receiver(post_save, sender=Rebel)
def set_winner(sender, instance=None, created=False, **kwargs):
    if instance is not None and hasattr(sender, '__is_sdc_model__'):
        serialize_instance = ConsumerSerializer().serialize([instance])
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
