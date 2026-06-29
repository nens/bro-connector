import datetime
from decimal import Decimal

import pytest
from bro.models import Organisation
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.utils import timezone
from rest_framework.test import APIClient
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
        # Avoid gmw's on_save_groundwater_monitoring_tube_static signal
        # auto-creating a GroundwaterLevelDossier (and its ObservationMetadata)
        # for this well's tube, which the gld fixtures create explicitly.
        in_management=False,
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
    return ObservationMetadata.objects.get_or_create(
        observation_type="reguliereMeting",
        status="voorlopig",
        responsible_party=default_organisation,
    )[0]


@pytest.fixture
@pytest.mark.django_db
def default_observation_process():
    return ObservationProcess.objects.get_or_create(
        measurement_instrument_type="druksensor",
        evaluation_procedure="oordeelDeskundige",
        process_type="algoritme",
        process_reference="STOWAgwst",
        air_pressure_compensation_type="capillair",
    )[0]


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
            gld_bro_id="GLD000000000012",
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
    return Observation.objects.get_or_create(
        groundwater_level_dossier=default_groundwater_level_dossier,
        observation_metadata=default_observation_metadata,
        observation_process=default_observation_process,
    )[0]


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


@pytest.fixture
@pytest.mark.django_db
def api_user():
    """External partner credentials used for Basic Auth against the API."""
    return get_user_model().objects.create_user(
        username="external-partner", password="s3cret-pass"
    )


@pytest.fixture
def api_client(api_user):
    """An authenticated DRF test client using HTTP Basic Auth."""
    client = APIClient()
    client.credentials(**_basic_auth_header("external-partner", "s3cret-pass"))
    return client


@pytest.fixture
def anonymous_api_client():
    return APIClient()


def _basic_auth_header(username, password):
    import base64

    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"HTTP_AUTHORIZATION": f"Basic {credentials}"}
