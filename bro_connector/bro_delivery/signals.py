from django.db.models.signals import post_save
from django.dispatch import receiver

from bro_delivery.models import FRDMessage, GLDMessage, GMNMessage, GMWMessage
from bro_delivery.utils import send_to_brostar


@receiver(post_save, sender=GMWMessage)
def on_gmw_message_created(sender, instance, created, **kwargs):
    if created:
        send_to_brostar(instance)


@receiver(post_save, sender=GLDMessage)
def on_gld_message_created(sender, instance, created, **kwargs):
    if created:
        send_to_brostar(instance)


@receiver(post_save, sender=FRDMessage)
def on_frd_message_created(sender, instance, created, **kwargs):
    if created:
        send_to_brostar(instance)


@receiver(post_save, sender=GMNMessage)
def on_gmn_message_created(sender, instance, created, **kwargs):
    if created:
        send_to_brostar(instance)
