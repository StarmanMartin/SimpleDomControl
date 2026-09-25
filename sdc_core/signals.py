
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save, post_delete
from django.dispatch.dispatcher import receiver

from sdc_core.sdc_extentions.models import SDCSerializer


def _send(sender, event_type, instance):
    async_to_sync(get_channel_layer().group_send)(sender.__name__, {
        'event_id': 'none',
        'type': event_type,
        'pk': instance.pk,
        'args': {'data': SDCSerializer().serialize([instance])},
        'is_error': False
    })


@receiver(post_save)
def sdc_model_saved(sender, instance=None, created: bool = False, **kwargs):
    """
    Notifies the connected clients when an SDC model instance has been created
    (``on_create``) or saved (``on_update``).

    :param sender: The model class
    :param instance: Saved or created instance
    :param created: True if the instance has been created
    :param kwargs:
    """
    if instance is not None and hasattr(sender, '__is_sdc_model__'):
        _send(sender, 'on_create' if created else 'on_update', instance)


@receiver(post_delete)
def sdc_model_deleted(sender, instance=None, **kwargs):
    """
    Notifies the connected clients when an SDC model instance has been deleted
    (``on_delete``).

    :param sender: The model class
    :param instance: Deleted instance (its pk is still set in post_delete)
    :param kwargs:
    """
    if instance is not None and hasattr(sender, '__is_sdc_model__'):
        _send(sender, 'on_delete', instance)
