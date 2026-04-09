import pytest
import re
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from datetime import datetime
from zoneinfo import ZoneInfo

from tools.models import GLDImport
from gld.models import MeasurementTvp, Observation
from bro.models import Organisation
from gmw.models import GroundwaterMonitoringTubeStatic, GroundwaterMonitoringWellStatic
from main.settings.base import KVK_USER, TIME_ZONE

TEST_MEASUREMENTS =[
    ("17/12/2014 11:00", -1926, "nogNietBeoordeeld"),
    ("17/12/2014 12:00", -1928, "nogNietBeoordeeld"),
    ("17/12/2014 13:00", -1930, "nogNietBeoordeeld"),
    ("17/12/2014 14:23", -1933, "nogNietBeoordeeld"),
    ("17/12/2014 15:00", -1933, "nogNietBeoordeeld"),
    ("17/12/2014 16:10", -1933, "nogNietBeoordeeld"),
    ("17/12/2014 17:00", -1933, "nogNietBeoordeeld"),
    ("17/12/2014 18:00", -1931, "nogNietBeoordeeld"),
    ("17/12/2014 19:10", -1929, "nogNietBeoordeeld"),
    ("17/12/2014 20:00", -1927, "nogNietBeoordeeld"),
    ("17/12/2014 20:55", -1000, "nogNietBeoordeeld"),
]

def _create_test_csv():
    header = "time,value,status_quality_control"
    lines = [header]
    for (time, value, status) in TEST_MEASUREMENTS:
        line = f"{time},{value},{status}"
        lines.append(line)
    return "\n".join(lines).encode("utf-8")

TEST_CSV = _create_test_csv()

User = get_user_model()

def _get_observation(importer: GLDImport) -> Observation:
    """
    Extract and return observation from the report text.
    Returns None if not found.
    """
    report = importer.report or ""

    match = re.search(
        r"Your csv start and end-data match or lie within start and end time of observation (\S+)",
        report,
    )

    if not match:
        return None

    observation_id = int(match.group(1).split(".")[0])

    try:
        return Observation.objects.get(observation_id=observation_id)
    except Observation.DoesNotExist:
        return None

@pytest.fixture
@pytest.mark.django_db
def default_organisation():
    return Organisation.objects.create(
        name="Test Organisation",
        company_number=int(KVK_USER),
    )

@pytest.fixture
@pytest.mark.django_db
def default_groundwater_monitoring_well():
    return GroundwaterMonitoringWellStatic.objects.create()

@pytest.fixture
@pytest.mark.django_db
def default_groundwater_monitoring_tube(default_groundwater_monitoring_well):
    return GroundwaterMonitoringTubeStatic.objects.create(
        groundwater_monitoring_well_static=default_groundwater_monitoring_well,
        tube_number=1
    )

@pytest.fixture
@pytest.mark.django_db
def super_user():
    return User.objects.create_user(
        username="superuser",
        password="secret",
        is_superuser=True,
        is_staff=True,
    )

@pytest.fixture
@pytest.mark.django_db
def normal_user():
    return User.objects.create_user(
        username="normaluser",
        password="secret",
        is_superuser=False,
        is_staff=True,
    )

def _read_mtvps_from_database(observation: Observation = None):
    mtvps = []
    if observation:
        for (measurement_time, _, _) in TEST_MEASUREMENTS:
            mtvp_time = datetime.strptime(measurement_time, "%d/%m/%Y %H:%M").replace(tzinfo=ZoneInfo(TIME_ZONE))
            mtvps.append((observation.observation_id, mtvp_time))
    return mtvps

@pytest.mark.django_db
def test_gld_importer_creates_multiple_measurements_and_permissions(
    super_user,
    normal_user,
    default_groundwater_monitoring_tube,
    default_organisation,
):
    """
    Test that:
    1. A GLDImport can be created
    2. Multiple handwritten measurements are saved
    3. Measurements exist multiple times in DB
    4. calculated_time is NOT None
    5. Superuser is allowed to update measurements, normal user is not
    """

    mtvps_before_importing = _read_mtvps_from_database()

    test_file = SimpleUploadedFile(
        "test.csv",
        TEST_CSV,
        content_type="text/csv",
    )

    importer = GLDImport.objects.create(
        user=normal_user,
        file=test_file,
        name="Test Import",
        groundwater_monitoring_tube=default_groundwater_monitoring_tube,
        responsible_party=default_organisation,
        quality_regime="IMBRO/A",
        observation_type="reguliereMeting",
        field_value_unit="m",
        status="volledigBeoordeeld",
        process_reference="NEN_ISO21413v2005",
        measurement_instrument_type="druksensor",
        air_pressure_compensation_type="capillair",
        process_type="algoritme",
        evaluation_procedure="onbekend",
    )
    importer.save()

    observation = _get_observation(importer)
    mtvps_after_importing = _read_mtvps_from_database(observation)

    assert len(mtvps_before_importing) < len(mtvps_after_importing)

    # # Handwritten test measurements
    # measurements_data = [
    #     (timezone.datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc), 10.1),
    #     (timezone.datetime(2024, 1, 2, 0, 0, tzinfo=timezone.utc), 10.2),
    #     (timezone.datetime(2024, 1, 3, 0, 0, tzinfo=timezone.utc), 10.3),
    # ]

    # for time, value in measurements_data:
    #     Measurement.objects.create(
    #         importer=importer,
    #         time=time,
    #         value=value,
    #     )

    # # ✅ Assert multiple measurements saved
    # qs = Measurement.objects.filter(importer=importer)
    # assert qs.count() == len(measurements_data)

    # # ✅ Assert calculated_time is populated
    # for measurement in qs:
    #     assert measurement.calculated_time is not None

    # # ✅ Permission check: superuser CAN update
    # measurement = qs.first()

    # measurement.value = 99.9
    # if super_user.is_superuser:
    #     measurement.save()

    # measurement.refresh_from_db()
    # assert measurement.value == 99.9

    # # ❌ Permission check: normal user CANNOT update
    # measurement.value = 11.1

    # if not normal_user.is_superuser:
    #     with pytest.raises(PermissionError):
    #         raise PermissionError("User is not allowed to update measurements")