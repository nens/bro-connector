from django.db.models.signals import (
    m2m_changed,
    post_delete,
    post_save,
    pre_delete,
    pre_save,
)
from django.dispatch import receiver
from .models import gmw_registration_log, Event
import reversion

@receiver(post_save, sender=gmw_registration_log)
def on_save_gmw_synchronisatie_log(sender, instance: gmw_registration_log, created, **kwargs):
    if instance.levering_type != "Construction":
        return
    
    if instance.bro_id is not None:
        event = Event.objects.get(change_id=instance.event_id)
        well = event.groundwater_monitoring_well_static
        if well.bro_id != instance.bro_id:
            with reversion.create_revision():
                well.bro_id = instance.bro_id
                well.save(update_fields=["bro_id"])
                reversion.set_comment(f"Updated BRO-ID based on sync_log ({instance.id}).")

    