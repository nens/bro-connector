import datetime

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import (
    GroundwaterMonitoringTubeDynamic,
    GroundwaterMonitoringTubeStatic,
    GroundwaterMonitoringWellDynamic,
    GroundwaterMonitoringWellStatic,
)

# @receiver(post_save, sender=GroundwaterMonitoringWellStatic)
# def on_save_groundwater_monitoring_static_pre(sender, **kwargs):
#     print("Post save GMWS")

# @receiver(pre_save, sender=GroundwaterMonitoringWellStatic)
# def on_save_groundwater_monitoring_static_post(sender, **kwargs):
#     print("Pre save GMWS")


@receiver([post_save, post_delete], sender=GroundwaterMonitoringWellStatic)
@receiver([post_save, post_delete], sender=GroundwaterMonitoringTubeStatic)
def clear_map_cache(sender, **kwargs):
    print("Map cache cleared due to model change:", sender.__name__)
    cache.clear()


@receiver(post_save, sender=GroundwaterMonitoringWellStatic)
def on_save_groundwater_monitoring_well_static(sender, instance, created, **kwargs):
    if created and not instance.state.exists():
        GroundwaterMonitoringWellDynamic.objects.create(
            groundwater_monitoring_well_static=instance,
            date_from=datetime.datetime.now(),
        )


@receiver(post_delete, sender=GroundwaterMonitoringWellStatic)
def on_delete_groundwater_monitoring_well_static(sender, instance, **kwargs):
    """
    Delete all GroundwaterMonitoringWellDynamic objects related to the
    deleted GroundwaterMonitoringWellStatic instance.
    """
    GroundwaterMonitoringWellDynamic.objects.filter(
        groundwater_monitoring_well_static=instance
    ).delete()


@receiver(post_save, sender=GroundwaterMonitoringTubeStatic)
def on_save_groundwater_monitoring_tube_static(sender, instance, created, **kwargs):
    if created and not instance.state.exists():
        GroundwaterMonitoringTubeDynamic.objects.create(
            groundwater_monitoring_tube_static=instance,
            date_from=datetime.datetime.now(),
        )


@receiver(post_delete, sender=GroundwaterMonitoringTubeStatic)
def on_delete_groundwater_monitoring_tube_static(sender, instance, **kwargs):
    """
    Delete all GroundwaterMonitoringTubeDynamic objects related to the
    deleted GroundwaterMonitoringTubeStatic instance.
    """
    GroundwaterMonitoringTubeDynamic.objects.filter(
        groundwater_monitoring_tube_static=instance
    ).delete()


# @receiver(post_save, sender=gmw_registration_log)
# def on_save_gmw_synchronisatie_log(
#     sender, instance: gmw_registration_log, created, **kwargs
# ):
#     if instance.event_type != "constructie":
#         return

#     if instance.bro_id is not None:
#         event = Event.objects.get(change_id=instance.event_id)
#         well = event.groundwater_monitoring_well_static
#         if well.bro_id != instance.bro_id:
#             with reversion.create_revision():
#                 well.bro_id = instance.bro_id
#                 well.save(update_fields=["bro_id"])
#                 reversion.set_comment(
#                     f"Updated BRO-ID based on sync_log ({instance.id})."
#                 )


# @receiver(pre_save, sender=GroundwaterMonitoringWellStatic)
# def pre_save_gmw_static(sender, instance: GroundwaterMonitoringWellStatic, **kwargs):
#     if (
#         instance.in_management is False
#         and instance.delivery_accountable_party.company_number == settings.KVK_USER
#     ):
#         instance.in_management = True

#     if instance.bro_id is None:
#         Event.objects.get_or_create(
#             groundwater_monitoring_well_static=instance,
#             event_name="constructie",
#             defaults={
#                 "event_date": instance.construction_date,
#             },
#         )

#     validator = WellValidation()
#     validator.well_complete(instance)
#     instance.complete_bro = validator.com_bro
#     instance.bro_actions = validator.bro_act


# @receiver(pre_save, sender=Electrode)
# def pre_save_electrode(sender, instance: Electrode, **kwargs):
#     if not instance.electrode_static_id:
#         return

#     old_instance = Electrode.objects.get(
#         electrode_static_id=instance.electrode_static_id
#     )

#     if old_instance.electrode_status != instance.electrode_status:
#         Event.objects.update_or_create(
#             event_name="elektrodestatusVeranderd",
#             event_date=datetime.datetime.now().date(),
#             groundwater_monitoring_well_static=instance.geo_ohm_cable.groundwater_monitoring_tube_static.groundwater_monitoring_well_static,
#             electrode_dynamic=instance,
#         )
