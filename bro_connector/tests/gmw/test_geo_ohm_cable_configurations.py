"""
Tests that all MeasurementConfiguration objects are created when a GeoOhmCable
is saved, and that two cables produce twice the number of configurations.

Expected counts for a 24-electrode cable:
  - 21 short configurations (n=1..21 in config_schema)
  -  9 long  configurations (a=1,3,...,17 in config_schema)
  = 30 configurations per cable
"""

import pytest
from bro.models import Organisation
from django.contrib.gis.geos import Point
from frd.models import FormationResistanceDossier, MeasurementConfiguration
from gmw.choices import config_schema, cross_cable_config_schema
from gmw.models import GeoOhmCable, GroundwaterMonitoringTubeStatic, GroundwaterMonitoringWellStatic
from main.settings.base import KVK_USER

CONFIGS_PER_CABLE = len(config_schema)          # 30
CROSS_CABLE_CONFIGS = len(cross_cable_config_schema)  # 6


@pytest.fixture
@pytest.mark.django_db
def default_organisation():
    return Organisation.objects.create(
        name="Test Organisation",
        company_number=int(KVK_USER),
    )


@pytest.fixture
@pytest.mark.django_db
def tube(default_organisation):
    gmw = GroundwaterMonitoringWellStatic.objects.create(
        delivery_accountable_party=default_organisation,
        coordinates=Point(0, 0),
    )
    return gmw.tube.create(tube_number="1")


@pytest.mark.django_db
def test_single_cable_creates_all_configurations(tube: GroundwaterMonitoringTubeStatic):
    """A single 24-electrode cable should produce 30 MeasurementConfigurations."""
    cable = GeoOhmCable.objects.create(
        groundwater_monitoring_tube_static=tube,
        cable_number=1,
        electrode_count=24,
    )

    frd = FormationResistanceDossier.objects.get(groundwater_monitoring_tube=tube)
    configs = MeasurementConfiguration.objects.filter(formation_resistance_dossier=frd)

    assert configs.count() == CONFIGS_PER_CABLE, (
        f"Expected {CONFIGS_PER_CABLE} configurations, got {configs.count()}. "
        f"Missing: {CONFIGS_PER_CABLE - configs.count()}"
    )


@pytest.mark.django_db
def test_two_cables_create_all_configurations(tube: GroundwaterMonitoringTubeStatic):
    """Two 24-electrode cables should produce 30 + 30 + 6 = 66 configurations total."""
    GeoOhmCable.objects.create(
        groundwater_monitoring_tube_static=tube,
        cable_number=1,
        electrode_count=24,
    )
    GeoOhmCable.objects.create(
        groundwater_monitoring_tube_static=tube,
        cable_number=2,
        electrode_count=24,
    )

    frd = FormationResistanceDossier.objects.get(groundwater_monitoring_tube=tube)
    configs = MeasurementConfiguration.objects.filter(formation_resistance_dossier=frd)

    expected = 2 * CONFIGS_PER_CABLE + CROSS_CABLE_CONFIGS
    assert configs.count() == expected, (
        f"Expected {expected} configurations for 2 cables "
        f"(30 cable1 + 30 cable2 + {CROSS_CABLE_CONFIGS} cross-cable), "
        f"got {configs.count()}."
    )


@pytest.mark.django_db
def test_two_cables_cross_cable_configurations(tube: GroundwaterMonitoringTubeStatic):
    """Exactly 6 cross-cable boundary configurations should be created."""
    GeoOhmCable.objects.create(
        groundwater_monitoring_tube_static=tube,
        cable_number=1,
        electrode_count=24,
    )
    GeoOhmCable.objects.create(
        groundwater_monitoring_tube_static=tube,
        cable_number=2,
        electrode_count=24,
    )

    frd = FormationResistanceDossier.objects.get(groundwater_monitoring_tube=tube)
    cross_configs = MeasurementConfiguration.objects.filter(
        formation_resistance_dossier=frd,
        configuration_name__contains="XEP",
    )

    assert cross_configs.count() == CROSS_CABLE_CONFIGS, (
        f"Expected {CROSS_CABLE_CONFIGS} cross-cable configurations, "
        f"got {cross_configs.count()}."
    )


@pytest.mark.django_db
def test_cable_configuration_names_are_unique(tube: GroundwaterMonitoringTubeStatic):
    """Configuration names must be unique across both cables."""
    GeoOhmCable.objects.create(
        groundwater_monitoring_tube_static=tube,
        cable_number=1,
        electrode_count=24,
    )
    GeoOhmCable.objects.create(
        groundwater_monitoring_tube_static=tube,
        cable_number=2,
        electrode_count=24,
    )

    frd = FormationResistanceDossier.objects.get(groundwater_monitoring_tube=tube)
    names = list(
        MeasurementConfiguration.objects.filter(
            formation_resistance_dossier=frd
        ).values_list("configuration_name", flat=True)
    )

    assert len(names) == len(set(names)), "Duplicate configuration names found."
