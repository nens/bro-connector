from django.db.models.signals import post_save, pre_save
from django.conf import settings
from django.dispatch import receiver
from .models import gmw_registration_log, Event, GroundwaterMonitoringWellStatic
import reversion
from .bro_validators.well import *


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


# @receiver(pre_save, sender=GroundwaterMonitoringWellStatic)
# def validate_well_before_save(sender, instance: GroundwaterMonitoringWellStatic, **kwargs):
#     is_valid, report = validate_well_static(instance)

#     # Update complete_bro based on validation result
#     instance.complete_bro = is_valid

#     # Store validation report in bro_actions
#     instance.bro_actions = report

#     # Display a warning message to the user if invalid
#     if not is_valid:
#         # If this is being triggered in the admin, add a warning message
#         messages.warning("hallo")
