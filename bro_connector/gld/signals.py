from django.db.models.signals import (
    post_save,
    post_delete,
    pre_save,
)
from django.dispatch import receiver
from .models import (
    gld_registration_log,
    gld_addition_log,
    GroundwaterLevelDossier,
    MeasurementTvp,
    MeasurementPointMetadata,
    Observation,
)
from gmw.models import GroundwaterMonitoringTubeStatic
import reversion
import datetime


def _calculate_value(field_value: float, unit: str) -> float | None:
    """
    For now only supports m / cm / mm.
    Conversion to mNAP
    """
    if unit == "m":
        return field_value
    elif unit == "cm":
        return field_value / 100
    elif unit == "mm":
        return field_value / 1000
    else:
        return None


def _calculate_value_tube(
    field_value: float, unit: str, tube_top_position: float
) -> float | None:
    """
    For now only supports m tov bkb / cm tov bkb / mm tov bkb.
    Conversion to mNAP
    """
    if unit == "m t.o.v. bkb":
        return field_value + tube_top_position
    elif unit == "cm t.o.v. bkb":
        return (field_value / 100) + tube_top_position
    elif unit == "mm t.o.v. bkb":
        return (field_value / 1000) + tube_top_position
    elif unit == "bar":
        return (field_value * 10.1974) + tube_top_position
    else:
        return None


@receiver(post_save, sender=gld_registration_log)
def on_save_gld_registration_log(
    sender, instance: gld_registration_log, created, **kwargs
):
    if instance.gld_bro_id is not None:
        tube = GroundwaterMonitoringTubeStatic.objects.get(
            groundwater_monitoring_well_static__bro_id=instance.gmw_bro_id,
            tube_number=instance.filter_number,
        )
        gld = GroundwaterLevelDossier.objects.get(groundwater_monitoring_tube=tube)
        if gld.gld_bro_id != instance.gld_bro_id:
            with reversion.create_revision():
                gld.gld_bro_id = instance.gld_bro_id
                gld.save(update_fields=["gld_bro_id"])
                reversion.set_comment(
                    f"Updated BRO-ID based on sync_log ({instance.id})."
                )


@receiver(post_save, sender=gld_addition_log)
def on_save_gld_addition_log(sender, instance: gld_addition_log, created, **kwargs):
    if instance.observation_identifier is not None:
        with reversion.create_revision():
            observation = instance.observation
            observation.observation_id_bro = instance.observation_identifier
            observation.save(update_fields=["observation_id_bro"])
            reversion.set_comment("Updated observation_id based on delivery to BRO.")

    if instance.delivery_status == "DOORGELEVERD":
        with reversion.create_revision():
            observation.up_to_date_in_bro = True
            observation.save(update_fields=["up_to_date_in_bro"])
            reversion.set_comment(
                "Updated up_to_date_in_bro as delivery was succesful."
            )


@receiver(post_delete, sender=MeasurementTvp)
def on_delete_measurement_tvp(sender, instance: MeasurementTvp, **kwargs):
    metadata = instance.measurement_point_metadata
    if metadata:
        metadata.delete()

@receiver(pre_save, sender=Observation)
def pre_save_observation(sender, instance: Observation, **kwargs):
    if instance.observation_endtime:
        if (
            instance.observation_metadata.status == "voorlopig"
            or instance.observation_metadata.observation_type == "controlemeting"
        ):
            instance.result_time = instance.timestamp_last_measurement
        else:
            instance.result_time = (
                instance.observation_endtime + datetime.timedelta(weeks=1)
                if instance.observation_endtime + datetime.timedelta(weeks=1)
                < datetime.datetime.now().astimezone()
                else datetime.datetime.now().astimezone()
            )


@receiver(post_save, sender=Observation)
def on_save_observation(sender, instance: Observation, **kwargs):
    gld = instance.groundwater_level_dossier

    open_observations = gld.observation.filter(
        observation_endtime__isnull=True,
        observation_process=instance.observation_process,
        observation_metadata=instance.observation_metadata,
    )
    if open_observations.count() == 0:
        last_observation: Observation = (
            gld.observation.all(
                observation_process=instance.observation_process,
                observation_metadata=instance.observation_metadata,
            )
            .order_by("observation_starttime")
            .last()
        )
        Observation.objects.create(
            observation_starttime=last_observation.observation_endtime,
            groundwater_level_dossier=last_observation.groundwater_level_dossier,
            observation_metadata=last_observation.observation_metadata,
            observation_process=last_observation.observation_process,
        )


@receiver(pre_save, sender=MeasurementTvp)
def on_save_measurement_tvp(sender, instance: MeasurementTvp, **kwargs):
    if not instance.measurement_point_metadata:
        metadata = MeasurementPointMetadata.objects.create()
        instance.measurement_point_metadata = metadata

    if not instance.calculated_value and instance.field_value:
        if instance.field_value_unit in ["m", "cm", "mm"]:
            instance.calculated_value = _calculate_value(
                instance.field_value, instance.field_value_unit
            )
        else:
            # Access the related groundwater_monitoring_tube_static instance
            tube_static: GroundwaterMonitoringTubeStatic = instance.observation.groundwater_level_dossier.groundwater_monitoring_tube_static

            # Retrieve the latest state
            latest_state = tube_static.state.order_by("-date_from").first()

            # Get the tube_top_position
            if latest_state:
                tube_top_position = latest_state.tube_top_position
            else:
                tube_top_position = None

            instance.calculated_value = _calculate_value_tube(
                instance.field_value, instance.field_value_unit, tube_top_position
            )
