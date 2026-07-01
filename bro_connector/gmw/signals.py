import datetime
import logging

import frd.models as frd_models
import reversion
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from main.settings.base import KVK_USER

from .choices import config_schema, elektrode_schema, pair_schema
from .models import (
    Electrode,
    Event,
    GeoOhmCable,
    GroundwaterMonitoringTubeDynamic,
    GroundwaterMonitoringTubeStatic,
    GroundwaterMonitoringWellDynamic,
    GroundwaterMonitoringWellStatic,
    gmw_registration_log,
)

logger = logging.getLogger(__name__)

@receiver(pre_save, sender=GroundwaterMonitoringWellDynamic)
def on_save_groundwater_monitoring_well_dynamic_pre(sender, **kwargs):
    # if .comment field is changed, then set the 'comment_verwerkt' to false
    instance: GroundwaterMonitoringWellDynamic = kwargs["instance"]
    if instance.pk is not None:
        old_instance = GroundwaterMonitoringWellDynamic.objects.get(pk=instance.pk)
        if old_instance.comment != instance.comment:
            instance.comment_processed = False


@receiver(pre_save, sender=GroundwaterMonitoringTubeDynamic)
def on_save_groundwater_monitoring_tube_dynamic_pre(sender, **kwargs):
    # if .comment field is changed, then set the 'comment_processed' to false
    instance: GroundwaterMonitoringTubeDynamic = kwargs["instance"]
    if instance.pk is not None:
        old_instance = GroundwaterMonitoringTubeDynamic.objects.get(pk=instance.pk)
        if old_instance.comment != instance.comment:
            instance.comment_processed = False


@receiver([post_save, post_delete], sender=GroundwaterMonitoringWellStatic)
@receiver([post_save, post_delete], sender=GroundwaterMonitoringTubeStatic)
def clear_map_cache(sender, **kwargs):
    cache.clear()


@receiver(post_save, sender=GroundwaterMonitoringWellStatic)
def on_save_groundwater_monitoring_well_static(
    sender, instance: GroundwaterMonitoringWellStatic, created, **kwargs
):
    if created and not instance.state.exists():
        GroundwaterMonitoringWellDynamic.objects.create(
            groundwater_monitoring_well_static=instance,
            date_from=datetime.datetime.now(),
        )

    if instance.event.filter(event_name="constructie").count() == 0:
        Event.objects.get_or_create(
            groundwater_monitoring_well_static=instance,
            event_name="constructie",
            defaults={
                "event_date": instance.construction_date,
            },
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
def on_save_groundwater_monitoring_tube_static(
    sender, instance: GroundwaterMonitoringTubeStatic, created, **kwargs
):
    if created and not instance.state.exists():
        GroundwaterMonitoringTubeDynamic.objects.create(
            groundwater_monitoring_tube_static=instance,
            date_from=datetime.datetime.now(),
        )

    if (
        instance.groundwater_monitoring_well_static.in_management is True
        and instance.groundwaterleveldossier.count() == 0
        and instance.groundwater_monitoring_well_static.initial_function != "kwaliteit"
    ):
        instance.groundwaterleveldossier.create(
            groundwater_monitoring_tube=instance,
            quality_regime="IMBRO",
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
    if instance.delivery_accountable_party is None:
        return

    if (
        instance.delivery_accountable_party.company_number == int(KVK_USER)
        and instance.groundwater_monitoring_well_static_id is None
    ):
        instance.deliver_gmw_to_bro = True
        instance.in_management = True


### ---- FRD Automatiseringen ---- ###
@receiver(post_save, sender=GeoOhmCable)
def post_save_geo_ohmkabel(sender, instance: GeoOhmCable, created, **kwargs):
    nr_existing_elektrodes = instance.electrode.all().count()
    if nr_existing_elektrodes > instance.electrode_count:
        remove_excessive_electrodes(instance)
    elif nr_existing_elektrodes < instance.electrode_count:
        add_electrodes_deficit(instance)

    get_or_create_frd(instance)
    create_elektrode_pairs_for_geo_ohmkabel(instance)
    create_meetconfiguraties(instance)


def generate_list(x: int, y: int, step=1) -> list[int]:
    """
    Generates a list of numbers from x to y (inclusive) with a specified step size.

    Args:
        x (int): Starting value.
        y (int): Ending value.
        step (int, optional): Step size. Defaults to 1.

    Returns:
        list: List of numbers from x to y.
    """
    return list(range(x, y + 1, step))


def remove_excessive_electrodes(geo_ohmkabel: GeoOhmCable):
    # Delete all ElectrodePairs that reference any electrode on this cable.
    electrodes = Electrode.objects.filter(geo_ohm_cable=geo_ohmkabel)
    frd_models.ElectrodePair.objects.filter(elektrode1__in=electrodes).delete()
    frd_models.ElectrodePair.objects.filter(elektrode2__in=electrodes).delete()

    # Delete electrodes beyond the target count.
    target = len(elektrode_schema)
    for elektrode in geo_ohmkabel.electrode.all()[target:]:
        elektrode.delete()


def add_electrodes_deficit(geo_ohmkabel: GeoOhmCable):
    current_count = geo_ohmkabel.electrode.count()
    for nr in range(current_count, len(elektrode_schema)):
        geo_ohmkabel.electrode.create(
            electrode_number=nr + 1,
        )


def create_elektrode_pairs_for_geo_ohmkabel(geo_ohm_cable: GeoOhmCable):
    """Creates all ElectrodePairs for a GeoOhmCable based on pair_schema.

    Pairs for which the underlying Electrode does not yet exist are skipped.
    """
    electrode_count = geo_ohm_cable.electrode.count()
    counter = 0

    for pair_code, electrode_codes in pair_schema.items():
        if counter >= electrode_count:
            break

        elektrode1_number = int(electrode_codes[0])
        elektrode2_number = int(electrode_codes[1])

        try:
            elektrode1 = Electrode.objects.get(
                geo_ohm_cable=geo_ohm_cable, electrode_number=elektrode1_number
            )
            elektrode2 = Electrode.objects.get(
                geo_ohm_cable=geo_ohm_cable, electrode_number=elektrode2_number
            )
        except Electrode.DoesNotExist:
            logger.warning(
                f"Electrode {elektrode1_number} or {elektrode2_number} does not exist "
                f"for GeoOhmCable {geo_ohm_cable}. Pair {pair_code} skipped."
            )
            continue

        if frd_models.ElectrodePair.objects.filter(
            elektrode1=elektrode1,
            elektrode2=elektrode2,
        ).exists():
            counter += 1
            continue

        frd_models.ElectrodePair.objects.create(
            elektrode1=elektrode1,
            elektrode2=elektrode2,
        )
        counter += 1


def get_or_create_frd(geo_ohm_kabel: GeoOhmCable) -> frd_models.FormationResistanceDossier:
    tube = geo_ohm_kabel.groundwater_monitoring_tube_static
    return frd_models.FormationResistanceDossier.objects.get_or_create(
        groundwater_monitoring_tube=tube,
        defaults={
            "deliver_to_bro": False,
            "quality_regime": "IMBRO",
            "assessment_type": "geoohmkabelBepaling",
        },
    )[0]


def get_frd_or_none(tube) -> frd_models.FormationResistanceDossier | None:
    return frd_models.FormationResistanceDossier.objects.filter(
        groundwater_monitoring_tube=tube
    ).first()


def get_electrode_pair_for_cable(
    geo_ohm_cable: GeoOhmCable,
    pair_code: str,
) -> frd_models.ElectrodePair | None:
    """Return the ElectrodePair for *pair_code* on *geo_ohm_cable*, or None."""
    electrode_codes = pair_schema.get(pair_code)
    if electrode_codes is None:
        return None
    e1_number = int(electrode_codes[0])
    e2_number = int(electrode_codes[1])
    try:
        elektrode1 = Electrode.objects.get(
            geo_ohm_cable=geo_ohm_cable, electrode_number=e1_number
        )
        elektrode2 = Electrode.objects.get(
            geo_ohm_cable=geo_ohm_cable, electrode_number=e2_number
        )
        return frd_models.ElectrodePair.objects.get(
            elektrode1=elektrode1, elektrode2=elektrode2
        )
    except (Electrode.DoesNotExist, frd_models.ElectrodePair.DoesNotExist):
        return None


def create_meetconfiguraties(geo_ohm_kabel: GeoOhmCable):
    frd = get_frd_or_none(geo_ohm_kabel.groundwater_monitoring_tube_static)

    for i, pair_codes in enumerate(config_schema):
        meetpaar_code, stroompaar_code = pair_codes

        meetpaar = get_electrode_pair_for_cable(geo_ohm_kabel, meetpaar_code)
        stroompaar = get_electrode_pair_for_cable(geo_ohm_kabel, stroompaar_code)

        if meetpaar is None or stroompaar is None:
            logger.warning(
                f"Pair {meetpaar_code!r} or {stroompaar_code!r} not found for "
                f"{geo_ohm_kabel}. MeasurementConfiguration {i + 1} skipped."
            )
            continue

        config_code = f"EP{i + 1 + (geo_ohm_kabel.cable_number - 1) * len(config_schema)}"

        frd_models.MeasurementConfiguration.objects.update_or_create(
            formation_resistance_dossier=frd,
            measurement_pair=meetpaar,
            flowcurrent_pair=stroompaar,
            defaults={
                "configuration_name": f"{geo_ohm_kabel}{config_code}",
            },
        )
