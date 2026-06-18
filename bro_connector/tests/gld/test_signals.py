"""
Signal tests for the GLD app.

Each test verifies side-effects triggered by Django signals defined in
gld/signals.py. All tests use real database interaction (@pytest.mark.django_db)
and leave signals connected so that actual signal behaviour is exercised.
"""
import datetime
from decimal import Decimal

import pytest
from django.db.models.signals import post_save
from django.utils import timezone
from gld.models import (
    GroundwaterLevelDossier,
    MeasurementPointMetadata,
    MeasurementTvp,
    Observation,
    ObservationMetadata,
    ObservationProcess,
    gld_addition_log,
    gld_registration_log,
)
from gld.signals import on_save_groundwater_level_dossier
from gmw.models import (
    GroundwaterMonitoringTubeDynamic,
    GroundwaterMonitoringTubeStatic,
    GroundwaterMonitoringWellStatic,
)


# ---------------------------------------------------------------------------
# on_save_groundwater_level_dossier
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_auto_creates_observation_on_gld_creation(
    default_groundwater_monitoring_tube, default_tube_dynamic
):
    """
    Saving a new GLD with no existing observations triggers creation of at
    least one Observation via the post_save signal.
    """
    gld = GroundwaterLevelDossier.objects.create(
        groundwater_monitoring_tube=default_groundwater_monitoring_tube,
        quality_regime="IMBRO/A",
    )
    assert Observation.objects.filter(groundwater_level_dossier=gld).count() >= 1


@pytest.mark.django_db
def test_auto_creates_observation_metadata_reguliere_meting(
    default_groundwater_monitoring_tube, default_tube_dynamic
):
    """
    The auto-created observation should have an ObservationMetadata with
    observation_type='reguliereMeting' and status='voorlopig'.
    """
    gld = GroundwaterLevelDossier.objects.create(
        groundwater_monitoring_tube=default_groundwater_monitoring_tube,
        quality_regime="IMBRO/A",
    )
    obs = Observation.objects.filter(groundwater_level_dossier=gld).first()
    assert obs is not None
    assert obs.observation_metadata is not None
    assert obs.observation_metadata.observation_type == "reguliereMeting"
    assert obs.observation_metadata.status == "voorlopig"


@pytest.mark.django_db
def test_auto_creates_sensor_observation_and_controlemeting(
    default_groundwater_monitoring_tube, default_tube_dynamic
):
    """
    When the tube has a sensor (sensor_id is not None), the signal creates
    both a reguliereMeting observation and a controlemeting observation.
    """
    gld = GroundwaterLevelDossier.objects.create(
        groundwater_monitoring_tube=default_groundwater_monitoring_tube,
        quality_regime="IMBRO/A",
    )
    observations = Observation.objects.filter(groundwater_level_dossier=gld)
    observation_types = set(
        obs.observation_metadata.observation_type
        for obs in observations
        if obs.observation_metadata
    )
    assert "reguliereMeting" in observation_types
    assert "controlemeting" in observation_types


@pytest.mark.django_db
def test_no_duplicate_observation_on_gld_update(
    default_groundwater_monitoring_tube, default_tube_dynamic
):
    """
    Updating an existing GLD (which already has observations) does NOT create
    additional observations — the signal guard `if not instance.observation.exists()`
    prevents duplicates.
    """
    gld = GroundwaterLevelDossier.objects.create(
        groundwater_monitoring_tube=default_groundwater_monitoring_tube,
        quality_regime="IMBRO/A",
    )
    count_after_create = Observation.objects.filter(groundwater_level_dossier=gld).count()

    # Trigger another post_save by updating the GLD
    gld.quality_regime = "IMBRO/A"
    gld.save()

    count_after_update = Observation.objects.filter(groundwater_level_dossier=gld).count()
    assert count_after_update == count_after_create


# ---------------------------------------------------------------------------
# on_save_measurement_tvp  (pre_save signal)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_measurement_tvp_auto_creates_measurement_point_metadata(default_observation):
    """
    Saving a MeasurementTvp without an MPM causes the signal to create and
    link one automatically.
    """
    tvp = MeasurementTvp.objects.create(
        observation=default_observation,
        measurement_time=timezone.now(),
        field_value=Decimal("1.000"),
        field_value_unit="m",
    )
    assert tvp.measurement_point_metadata is not None
    assert MeasurementPointMetadata.objects.filter(
        pk=tvp.measurement_point_metadata.pk
    ).exists()


@pytest.mark.django_db
def test_measurement_tvp_calculated_value_unit_m(default_observation):
    """Unit 'm' → calculated_value equals field_value (passthrough)."""
    tvp = MeasurementTvp.objects.create(
        observation=default_observation,
        measurement_time=timezone.now(),
        field_value=Decimal("-1.500"),
        field_value_unit="m",
    )
    assert tvp.calculated_value == Decimal("-1.500")


@pytest.mark.django_db
def test_measurement_tvp_calculated_value_unit_cm(default_observation):
    """Unit 'cm' → calculated_value = field_value / 100."""
    tvp = MeasurementTvp.objects.create(
        observation=default_observation,
        measurement_time=timezone.now(),
        field_value=Decimal("150"),
        field_value_unit="cm",
    )
    assert tvp.calculated_value == Decimal("1.5")


@pytest.mark.django_db
def test_measurement_tvp_calculated_value_unit_mm(default_observation):
    """Unit 'mm' → calculated_value = field_value / 1000."""
    tvp = MeasurementTvp.objects.create(
        observation=default_observation,
        measurement_time=timezone.now(),
        field_value=Decimal("1500"),
        field_value_unit="mm",
    )
    assert tvp.calculated_value == Decimal("1.5")


@pytest.mark.django_db
def test_measurement_tvp_calculated_value_unit_bkb(default_observation, default_tube_dynamic):
    """
    Unit 'm t.o.v. bkb' → calculated_value = tube_top_position - field_value.
    tube_top_position is -5.0 (from default_tube_dynamic), field_value=2.0
    → calculated_value = -5.0 - 2.0 = -7.0
    """
    tvp = MeasurementTvp.objects.create(
        observation=default_observation,
        measurement_time=timezone.now(),
        field_value=Decimal("2.000"),
        field_value_unit="m t.o.v. bkb",
    )
    assert tvp.calculated_value == Decimal("-7.0")


# ---------------------------------------------------------------------------
# pre_save_observation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_pre_save_observation_sets_starttime_from_first_measurement(
    default_observation, default_measurement_tvp
):
    """
    When an Observation has no observation_starttime but has measurements,
    the pre_save signal populates observation_starttime from the first measurement.
    """
    assert default_observation.observation_starttime is None

    # Re-save the observation to trigger the pre_save signal
    default_observation.save()
    default_observation.refresh_from_db()

    assert default_observation.observation_starttime == default_measurement_tvp.measurement_time


@pytest.mark.django_db
def test_pre_save_observation_sets_result_time_for_voorlopig(
    default_observation, default_measurement_tvp
):
    """
    For a 'voorlopig' observation, result_time is set to the last measurement time
    when the observation is closed (observation_endtime is set).
    """
    default_observation.observation_endtime = timezone.now()
    default_observation.save()
    default_observation.refresh_from_db()

    assert default_observation.result_time == default_measurement_tvp.measurement_time


@pytest.mark.django_db
def test_pre_save_observation_creates_continuation_on_endtime_set(
    default_observation, default_measurement_tvp
):
    """
    Setting observation_endtime on an open Observation triggers creation of a new
    open Observation for the same GLD/metadata/process (continuation).
    """
    gld = default_observation.groundwater_level_dossier
    count_before = Observation.objects.filter(groundwater_level_dossier=gld).count()

    default_observation.observation_endtime = timezone.now()
    default_observation.save()

    count_after = Observation.objects.filter(groundwater_level_dossier=gld).count()
    assert count_after == count_before + 1

    # The new observation should be open (no endtime)
    new_obs = Observation.objects.filter(
        groundwater_level_dossier=gld,
        observation_endtime__isnull=True,
    ).exclude(pk=default_observation.pk).first()
    assert new_obs is not None


# ---------------------------------------------------------------------------
# pre_delete_measurement_tvp
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_delete_measurement_tvp_cascades_measurement_point_metadata(
    default_observation,
):
    """
    Deleting a MeasurementTvp also deletes its associated MeasurementPointMetadata
    via the pre_delete signal (to avoid orphaned MPM records).
    """
    tvp = MeasurementTvp.objects.create(
        observation=default_observation,
        measurement_time=timezone.now(),
        field_value=Decimal("1.000"),
        field_value_unit="m",
    )
    mpm_pk = tvp.measurement_point_metadata.pk
    assert MeasurementPointMetadata.objects.filter(pk=mpm_pk).exists()

    tvp.delete()

    assert not MeasurementPointMetadata.objects.filter(pk=mpm_pk).exists()


# ---------------------------------------------------------------------------
# on_save_gld_registration_log
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_registration_log_syncs_bro_id_to_gld(
    default_groundwater_monitoring_well,
    default_groundwater_monitoring_tube,
    default_groundwater_level_dossier,
):
    """
    When a gld_registration_log has a gld_bro_id set and is saved, the signal
    copies that BRO ID to the linked GroundwaterLevelDossier.
    """
    reg_log = gld_registration_log.objects.create(
        gmw_bro_id="GMW000000000001",
        filter_number=1,
        quality_regime="IMBRO",
        gld_bro_id="GLD000000000001",
        delivery_type="register",
    )

    default_groundwater_level_dossier.refresh_from_db()
    assert default_groundwater_level_dossier.gld_bro_id == "GLD000000000001"


# ---------------------------------------------------------------------------
# on_save_gld_addition_log
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_addition_log_sets_observation_id_bro(default_observation):
    """
    Saving a gld_addition_log with an observation_identifier updates
    Observation.observation_id_bro via the post_save signal.
    """
    log = gld_addition_log.objects.create(
        broid_registration="GLD000000000001",
        observation=default_observation,
        observation_identifier="OBS-001",
        delivery_type="register",
    )

    default_observation.refresh_from_db()
    assert default_observation.observation_id_bro == "OBS-001"


@pytest.mark.django_db
def test_addition_log_sets_observation_up_to_date_on_doorgeleverd(default_observation):
    """
    When a gld_addition_log delivery_status transitions to 'DOORGELEVERD',
    Observation.up_to_date_in_bro is set to True.
    """
    log = gld_addition_log.objects.create(
        broid_registration="GLD000000000001",
        observation=default_observation,
        observation_identifier="OBS-002",
        delivery_type="register",
        delivery_status="DOORGELEVERD",
    )

    default_observation.refresh_from_db()
    assert default_observation.up_to_date_in_bro is True
