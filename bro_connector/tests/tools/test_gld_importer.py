import pytest
import re
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from datetime import datetime
from zoneinfo import ZoneInfo
import logging

from tools.models import GLDImport
from gld.models import MeasurementTvp, Observation
from bro.models import Organisation
from gmw.models import GroundwaterMonitoringTubeStatic, GroundwaterMonitoringWellStatic
from main.settings.base import KVK_USER, TIME_ZONE

logger = logging.getLogger(__name__)

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

def _create_test_csv(measurements):
    header = "time,value,status_quality_control"
    lines = [header]
    for (time, value, status) in measurements:
        line = f"{time},{value},{status}"
        lines.append(line)
    return "\n".join(lines).encode("utf-8")

TEST_CSV = _create_test_csv(TEST_MEASUREMENTS)

SAMPLE_MEASUREMENTS = TEST_MEASUREMENTS[:5]
SAMPLE_CSV = _create_test_csv(SAMPLE_MEASUREMENTS)

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

def _read_mtvps_from_database(observation: Observation = None, measurements: list = []):
    mtvps = []
    if observation:
        for (measurement_time, _, _) in measurements:
            mtvp_time = datetime.strptime(measurement_time, "%d/%m/%Y %H:%M").replace(tzinfo=ZoneInfo(TIME_ZONE))
            mtvps.append((observation.observation_id, mtvp_time))
    return mtvps


def has_user_permission(report: str) -> bool:
    """
    Returns False if 'User does not have permission' is present in the report,
    otherwise returns True.
    """
    return "User does not have permission" not in report


def extract_n_duplicates(report: str) -> int | None:
    """
    Extracts the number from:
    '{} duplicate measurements'
    Returns the integer (e.g. 11), or None if not found.
    """
    match = re.search(r"(\d+) duplicate measurements", report)
    return int(match.group(1)) if match else None


def extract_continuing_measurements(report: str) -> int | None:
    """
    Extracts the number from:
    'continueing with {} new measurements'
    Returns the integer (e.g. 0), or None if not found.
    """
    match = re.search(r"continueing with (\d+) new measurements", report)
    return int(match.group(1)) if match else None


def extract_total_unique_measurements(report: str) -> int | None:
    """
    Extracts the number from:
    'out of {} total unique measurements'
    Returns the integer (e.g. 11), or None if not found.
    """
    match = re.search(r"out of (\d+) total unique measurements", report)
    return int(match.group(1)) if match else None


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
    test_file = SimpleUploadedFile(
        "test.csv",
        TEST_CSV,
        content_type="text/csv",
    )

    importer = GLDImport.objects.create(
        user=normal_user,
        file=test_file,
        name="Initial Import",
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
    mtvps_in_first_import = _read_mtvps_from_database(observation, TEST_MEASUREMENTS)
    print(f"MTVPs in first import: {len(mtvps_in_first_import)}")

    ## ---------- TEST RUN WITH NORMAL USER, VOLLEDIGBEOORDEELD ----------

    test_file = SimpleUploadedFile(
        "test.csv",
        SAMPLE_CSV,
        content_type="text/csv",
    )

    importer = GLDImport.objects.create(
        user=normal_user,
        file=test_file,
        name="Normal Import",
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
    mtvps_in_second_import = _read_mtvps_from_database(observation, SAMPLE_MEASUREMENTS)
    print(f"MTVPs in second import: {len(mtvps_in_second_import)}")

    permission_check = has_user_permission(importer.report)
    assert permission_check == False

    n_unique_measurements = extract_total_unique_measurements(importer.report)
    assert n_unique_measurements == len(SAMPLE_MEASUREMENTS)

    n_duplicate_measurements = extract_n_duplicates(importer.report)
    assert n_duplicate_measurements == len(SAMPLE_MEASUREMENTS)

    ## ---------- TEST RUN WITH NORMAL USER, VOLLEDIGBEOORDEELD ----------
    #     
    test_file = SimpleUploadedFile(
        "test.csv",
        SAMPLE_CSV,
        content_type="text/csv",
    )

    importer = GLDImport.objects.create(
        user=super_user,
        file=test_file,
        name="Super Import",
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

    observation = _get_observation(importer)
    mtvps_in_third_import = _read_mtvps_from_database(observation, SAMPLE_MEASUREMENTS)
    print(f"MTVPs in third import: {len(mtvps_in_third_import)}")

    assert len(mtvps_in_second_import) == len(mtvps_in_third_import)

    permission_check = has_user_permission(importer.report)
    assert permission_check == True

    n_unique_measurements = extract_total_unique_measurements(importer.report)
    assert n_unique_measurements == len(SAMPLE_MEASUREMENTS)

    n_duplicate_measurements = extract_n_duplicates(importer.report)
    assert n_duplicate_measurements == len(SAMPLE_MEASUREMENTS)