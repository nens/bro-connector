from django.db.models.signals import post_save, pre_save
from django.conf import settings
from django.dispatch import receiver
from .models import gmw_registration_log, Event, GroundwaterMonitoringWellStatic
from bro_connector.gmw.bro_validators.well_validation import WellValidation
import reversion


@receiver(post_save, sender=gmw_registration_log)
def on_save_gmw_synchronisatie_log(
    sender, instance: gmw_registration_log, created, **kwargs
):
    if instance.event_type != "constructie":
        return

    if instance.bro_id is not None:
        event = Event.objects.get(change_id=instance.event_id)
        well = event.groundwater_monitoring_well_static
        if well.bro_id != instance.bro_id:
            with reversion.create_revision():
                well.bro_id = instance.bro_id
                well.save(update_fields=["bro_id"])
                reversion.set_comment(
                    f"Updated BRO-ID based on sync_log ({instance.id})."
                )


@receiver(pre_save, sender=GroundwaterMonitoringWellStatic)
def pre_save_gmw_static(sender, instance: GroundwaterMonitoringWellStatic, **kwargs):
    if (
        instance.in_management is False
        and instance.delivery_accountable_party.company_number == settings.KVK_USER
    ):
        instance.in_management = True

    if instance.bro_id is None:
        Event.objects.get_or_create(
            groundwater_monitoring_well_static=instance,
            event_name="constructie",
            defaults={
                "event_date": instance.construction_date,
            },
        )

    validator = WellValidation()
    validator.well_static(instance)
    instance.complete_bro = validator.com_bro
    instance.bro_actions = validator.bro_act
