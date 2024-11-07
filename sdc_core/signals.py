
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save, post_delete
from django.dispatch.dispatcher import receiver

from sdc_core.sdc_extentions.models import SDCSerializer


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