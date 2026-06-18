import datetime
from decimal import Decimal

import pytest
from bro.models import Organisation
from django.db.models.signals import post_save
from django.utils import timezone
from gld.models import (
    GroundwaterLevelDossier,
    MeasurementPointMetadata,
    MeasurementTvp,
    Observation,
    ObservationMetadata,
    ObservationProcess,
)
from gld.signals import on_save_groundwater_level_dossier
from gmw.models import (
    GroundwaterMonitoringTubeDynamic,
    GroundwaterMonitoringTubeStatic,
    GroundwaterMonitoringWellStatic,
)


@pytest.fixture
@pytest.mark.django_db
def default_organisation():
    return Organisation.objects.create(
        name="Test Organisation",
        company_number=20168636,
    )


@pytest.fixture
@pytest.mark.django_db
def default_groundwater_monitoring_well(default_organisation):
    return GroundwaterMonitoringWellStatic.objects.create(
        delivery_accountable_party=default_organisation,
        bro_id="GMW000000000001",
    )


@pytest.fixture
@pytest.mark.django_db
def default_groundwater_monitoring_tube(default_groundwater_monitoring_well):
    return GroundwaterMonitoringTubeStatic.objects.create(
        groundwater_monitoring_well_static=default_groundwater_monitoring_well,
        tube_number=1,
    )


@pytest.fixture
@pytest.mark.django_db
def default_tube_dynamic(default_groundwater_monitoring_tube):
    """Tube dynamic state required for bar/bkb unit conversion signal tests."""
    return GroundwaterMonitoringTubeDynamic.objects.create(
        groundwater_monitoring_tube_static=default_groundwater_monitoring_tube,
        date_from=timezone.now() - datetime.timedelta(days=365),
        tube_top_position=-5.0,
        sensor_depth=10.0,
        sensor_id="sensor-001",
    )


@pytest.fixture
@pytest.mark.django_db
def default_observation_metadata(default_organisation):
    return ObservationMetadata.objects.create(
        observation_type="reguliereMeting",
        status="voorlopig",
        responsible_party=default_organisation,
    )


@pytest.fixture
@pytest.mark.django_db
def default_observation_process():
    return ObservationProcess.objects.create(
        measurement_instrument_type="druksensor",
        evaluation_procedure="oordeelDeskundige",
        process_type="algoritme",
        process_reference="STOWAgwst",
        air_pressure_compensation_type="capillair",
    )


@pytest.fixture
@pytest.mark.django_db
def default_groundwater_level_dossier(default_groundwater_monitoring_tube):
    """
    Creates a GLD with the on_save_groundwater_level_dossier signal disconnected.
    This prevents the auto-Observation creation, giving model tests full control
    over what observations exist.
    """
    post_save.disconnect(on_save_groundwater_level_dossier, sender=GroundwaterLevelDossier)
    try:
        gld = GroundwaterLevelDossier.objects.create(
            groundwater_monitoring_tube=default_groundwater_monitoring_tube,
            quality_regime="IMBRO",
        )
    finally:
        post_save.connect(on_save_groundwater_level_dossier, sender=GroundwaterLevelDossier)
    return gld


@pytest.fixture
@pytest.mark.django_db
def default_observation(
    default_groundwater_level_dossier,
    default_observation_metadata,
    default_observation_process,
):
    return Observation.objects.create(
        groundwater_level_dossier=default_groundwater_level_dossier,
        observation_metadata=default_observation_metadata,
        observation_process=default_observation_process,
    )


@pytest.fixture
@pytest.mark.django_db
def default_measurement_point_metadata():
    return MeasurementPointMetadata.objects.create(
        status_quality_control="nogNietBeoordeeld",
    )


@pytest.fixture
@pytest.mark.django_db
def default_measurement_tvp(default_observation):
    """
    Creates a MeasurementTvp with field_value in meters.
    The on_save_measurement_tvp pre_save signal will automatically:
    - Create and assign a MeasurementPointMetadata
    - Set calculated_value = field_value (passthrough for unit "m")
    """
    return MeasurementTvp.objects.create(
        observation=default_observation,
        measurement_time=timezone.now() - datetime.timedelta(hours=1),
        field_value=Decimal("-1.234"),
        field_value_unit="m",
    )
