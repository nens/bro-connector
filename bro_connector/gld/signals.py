from django.db.models.signals import (
    post_save,
    post_delete,
    pre_save,
)
from django.dispatch import receiver
from .models import gld_registration_log, GroundwaterLevelDossier, MeasurementTvp
from gmw.models import GroundwaterMonitoringTubeStatic
import reversion

def _calculate_value(field_value: float, unit: str):
    """
    For now only supports m / cm / mm.
    Conversion to 
    """
    if unit == "m":
        return field_value
    elif unit == "cm":
        return field_value / 10
    elif unit == "mm":
        return field_value / 100
    else:
        return None

@receiver(post_save, sender=gld_registration_log)
def on_save_gld_synchronisatie_log(sender, instance: gld_registration_log, created, **kwargs):
    if instance.gld_bro_id is not None:
        tube = GroundwaterMonitoringTubeStatic.objects.get(
            groundwater_monitoring_well_static__bro_id=instance.gwm_bro_id, 
            tube_number=instance.filter_number
        )
        gld = GroundwaterLevelDossier.objects.get(groundwater_monitoring_tube=tube)
        if gld.gld_bro_id != instance.gld_bro_id:
            with reversion.create_revision():
                gld.gld_bro_id = instance.gld_bro_id
                gld.save(update_fields=["gld_bro_id"])
                reversion.set_comment(f"Updated BRO-ID based on sync_log ({instance.id}).")

@receiver(post_delete, sender=MeasurementTvp)
def on_delete_measurement_tvp(sender, instance: MeasurementTvp, **kwargs):
    metadata = instance.measurement_point_metadata
    if metadata:
        metadata.delete()

@receiver(pre_save, sender=MeasurementTvp)
def pre_save_measurement_tvp(sender, instance: MeasurementTvp, **kwargs):
    if not instance.calculated_value and instance.field_value:
        instance.calculated_value = _calculate_value(instance.field_value, instance.field_value_unit)