import datetime
from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.utils import timezone
from gld.models import (
    GroundwaterLevelDossier,
    MeasurementPointMetadata,
    MeasurementTvp,
    Observation,
    ObservationMetadata,
    ObservationProcess,
)


# ---------------------------------------------------------------------------
# GroundwaterLevelDossier
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_gld_str(default_groundwater_level_dossier, default_groundwater_monitoring_tube):
    expected = f"GLD_{default_groundwater_monitoring_tube.__str__()}_IMBRO"
    assert str(default_groundwater_level_dossier) == expected


@pytest.mark.django_db
def test_gld_gmw_bro_id_property(
    default_groundwater_level_dossier, default_groundwater_monitoring_well
):
    assert default_groundwater_level_dossier.gmw_bro_id == "GMW000000000001"


@pytest.mark.django_db
def test_gld_tube_number_property(
    default_groundwater_level_dossier, default_groundwater_monitoring_tube
):
    assert default_groundwater_level_dossier.tube_number == default_groundwater_monitoring_tube.tube_number


@pytest.mark.django_db
def test_gld_nr_measurements_zero_when_no_measurements(default_groundwater_level_dossier, default_observation):
    assert default_groundwater_level_dossier.nr_measurements == 0


@pytest.mark.django_db
def test_gld_nr_measurements_counts_all_tvps(default_groundwater_level_dossier, default_measurement_tvp):
    assert default_groundwater_level_dossier.nr_measurements == 1


@pytest.mark.django_db
def test_gld_has_open_observation_true(default_groundwater_level_dossier, default_observation):
    # Observation with no endtime → open observation exists
    assert default_groundwater_level_dossier.has_open_observation is True


@pytest.mark.django_db
def test_gld_has_open_observation_false_when_all_closed(default_groundwater_level_dossier, default_observation):
    Observation.objects.filter(pk=default_observation.pk).update(
        observation_endtime=timezone.now()
    )
    assert default_groundwater_level_dossier.has_open_observation is False


@pytest.mark.django_db
def test_gld_completely_delivered_true_when_no_closed_observations(
    default_groundwater_level_dossier, default_observation
):
    # Observation is open (no endtime), so no "closed and not delivered" ones
    assert default_groundwater_level_dossier.completely_delivered is True


@pytest.mark.django_db
def test_gld_completely_delivered_false_when_closed_observation_not_delivered(
    default_groundwater_level_dossier, default_observation
):
    Observation.objects.filter(pk=default_observation.pk).update(
        observation_endtime=timezone.now(),
        up_to_date_in_bro=False,
    )
    assert default_groundwater_level_dossier.completely_delivered is False


@pytest.mark.django_db
def test_gld_first_measurement_none_when_no_measurements(
    default_groundwater_level_dossier, default_observation
):
    assert default_groundwater_level_dossier.first_measurement is None


@pytest.mark.django_db
def test_gld_first_measurement_returns_value_when_measurement_exists(
    default_groundwater_level_dossier, default_measurement_tvp
):
    assert default_groundwater_level_dossier.first_measurement is not None


@pytest.mark.django_db
def test_gld_last_measurement_none_when_no_measurements(
    default_groundwater_level_dossier, default_observation
):
    assert default_groundwater_level_dossier.last_measurement is None


@pytest.mark.django_db
def test_gld_last_measurement_returns_value_when_measurement_exists(
    default_groundwater_level_dossier, default_measurement_tvp
):
    assert default_groundwater_level_dossier.last_measurement is not None


# ---------------------------------------------------------------------------
# ObservationMetadata
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_observation_metadata_str_with_responsible_party(default_observation_metadata, default_organisation):
    result = str(default_observation_metadata)
    assert default_organisation.name in result
    assert "reguliereMeting" in result
    assert "voorlopig" in result


@pytest.mark.django_db
def test_observation_metadata_str_controlemeting_omits_status(default_organisation):
    meta = ObservationMetadata.objects.create(
        observation_type="controlemeting",
        status="voorlopig",
        responsible_party=default_organisation,
    )
    result = str(meta)
    assert "controlemeting" in result
    assert "voorlopig" not in result


@pytest.mark.django_db
def test_observation_metadata_str_without_responsible_party():
    meta = ObservationMetadata.objects.create(
        observation_type="reguliereMeting",
        status="volledigBeoordeeld",
        responsible_party=None,
    )
    result = str(meta)
    assert "reguliereMeting" in result
    assert "volledigBeoordeeld" in result


# ---------------------------------------------------------------------------
# ObservationProcess
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_observation_process_str_with_air_pressure(default_observation_process):
    result = str(default_observation_process)
    assert "druksensor" in result
    assert "capillair" in result
    assert "oordeelDeskundige" in result


@pytest.mark.django_db
def test_observation_process_str_without_air_pressure():
    process = ObservationProcess.objects.create(
        measurement_instrument_type="analoogPeilklokje",
        evaluation_procedure="oordeelDeskundige",
        process_type="algoritme",
        process_reference="NEN5120v1991",
        air_pressure_compensation_type=None,
    )
    result = str(process)
    assert "analoogPeilklokje" in result
    assert "oordeelDeskundige" in result
    # air pressure type should not appear when None
    assert "capillair" not in result


@pytest.mark.django_db
def test_get_sourcedocument_data_druksensor_includes_air_pressure(default_observation_process):
    data = default_observation_process.get_sourcedocument_data()
    assert "airPressureCompensationType" in data
    assert data["airPressureCompensationType"] == "capillair"
    assert "evaluationProcedure" in data
    assert "measurementInstrumentType" in data


@pytest.mark.django_db
def test_get_sourcedocument_data_analoog_peilklokje_omits_air_pressure():
    process = ObservationProcess.objects.create(
        measurement_instrument_type="analoogPeilklokje",
        evaluation_procedure="oordeelDeskundige",
        process_type="algoritme",
        process_reference="NEN5120v1991",
        air_pressure_compensation_type=None,
    )
    data = process.get_sourcedocument_data()
    assert "airPressureCompensationType" not in data
    assert data["measurementInstrumentType"] == "analoogPeilklokje"


@pytest.mark.django_db
def test_get_sourcedocument_data_onbekend_peilklokje_omits_air_pressure():
    process = ObservationProcess.objects.create(
        measurement_instrument_type="onbekendPeilklokje",
        evaluation_procedure="oordeelDeskundige",
        process_type="algoritme",
        process_reference="NEN5120v1991",
        air_pressure_compensation_type="capillair",
    )
    data = process.get_sourcedocument_data()
    assert "airPressureCompensationType" not in data


# ---------------------------------------------------------------------------
# MeasurementPointMetadata
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_interpolation_code_always_discontinu(default_measurement_point_metadata):
    assert default_measurement_point_metadata.interpolation_code == "discontinu"


@pytest.mark.django_db
def test_measurement_point_metadata_str(default_measurement_point_metadata):
    result = str(default_measurement_point_metadata)
    assert "nogNietBeoordeeld" in result


@pytest.mark.django_db
def test_get_sourcedocument_data_without_censor(default_measurement_point_metadata):
    data = default_measurement_point_metadata.get_sourcedocument_data()
    assert "StatusQualityControl" in data
    assert data["StatusQualityControl"] == "nogNietBeoordeeld"
    assert data["interpolationType"] == "Discontinuous"
    assert "censoredReason" not in data


@pytest.mark.django_db
def test_get_sourcedocument_data_with_censor():
    mpm = MeasurementPointMetadata.objects.create(
        status_quality_control="afgekeurd",
        censor_reason="kleinerDanLimietwaarde",
    )
    data = mpm.get_sourcedocument_data()
    assert "censoredReason" in data
    assert data["censoredReason"] == "kleinerDanLimietwaarde"


# ---------------------------------------------------------------------------
# Observation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_observation_str_with_no_times(default_observation):
    result = str(default_observation)
    assert "Unknown" in result
    assert "Present" in result


@pytest.mark.django_db
def test_observation_str_with_times(default_observation):
    now = timezone.now()
    default_observation.observation_starttime = now
    default_observation.observation_endtime = now
    default_observation.save()
    result = str(default_observation)
    assert str(now.date()) in result


@pytest.mark.django_db
def test_observation_timestamp_first_measurement_none_when_no_measurements(default_observation):
    assert default_observation.timestamp_first_measurement is None


@pytest.mark.django_db
def test_observation_timestamp_first_measurement_returns_time(default_observation, default_measurement_tvp):
    result = default_observation.timestamp_first_measurement
    assert result is not None
    assert result == default_measurement_tvp.measurement_time


@pytest.mark.django_db
def test_observation_timestamp_last_measurement_none_when_no_measurements(default_observation):
    assert default_observation.timestamp_last_measurement is None


@pytest.mark.django_db
def test_observation_timestamp_last_measurement_returns_time(default_observation, default_measurement_tvp):
    result = default_observation.timestamp_last_measurement
    assert result is not None
    assert result == default_measurement_tvp.measurement_time


@pytest.mark.django_db
def test_observation_nr_measurements_zero(default_observation):
    assert default_observation.nr_measurements == 0


@pytest.mark.django_db
def test_observation_nr_measurements_counts_tvps(default_observation, default_measurement_tvp):
    assert default_observation.nr_measurements == 1


@pytest.mark.django_db
def test_observation_date_stamp_none_when_no_result_time(default_observation):
    assert default_observation.date_stamp is None


@pytest.mark.django_db
def test_observation_date_stamp_returns_date(default_observation):
    now = timezone.now()
    default_observation.result_time = now
    default_observation.save()
    assert default_observation.date_stamp == now.date()


@pytest.mark.django_db
def test_observation_observation_type_from_metadata(default_observation, default_observation_metadata):
    assert default_observation.observation_type == "reguliereMeting"


@pytest.mark.django_db
def test_observation_observation_type_dash_when_no_metadata(default_groundwater_level_dossier):
    obs = Observation.objects.create(
        groundwater_level_dossier=default_groundwater_level_dossier,
        observation_metadata=None,
        observation_process=None,
    )
    assert obs.observation_type == "-"


@pytest.mark.django_db
def test_observation_status_from_metadata(default_observation, default_observation_metadata):
    assert default_observation.status == "voorlopig"


@pytest.mark.django_db
def test_observation_measurement_type_from_process(default_observation, default_observation_process):
    assert default_observation.measurement_type == "druksensor"


@pytest.mark.django_db
def test_observation_addition_type_regulier(default_observation):
    # observation_type is "reguliereMeting" → addition_type is "regulier_reguliereMeting"
    assert default_observation.addition_type == "regulier_reguliereMeting"


@pytest.mark.django_db
def test_observation_addition_type_controlemeting(default_groundwater_level_dossier, default_organisation):
    meta = ObservationMetadata.objects.create(
        observation_type="controlemeting",
        status=None,
        responsible_party=default_organisation,
    )
    process = ObservationProcess.objects.create(
        measurement_instrument_type="analoogPeilklokje",
        evaluation_procedure="oordeelDeskundige",
        process_type="algoritme",
        process_reference="NEN5120v1991",
    )
    obs = Observation.objects.create(
        groundwater_level_dossier=default_groundwater_level_dossier,
        observation_metadata=meta,
        observation_process=process,
    )
    assert obs.addition_type == "controlemeting"


@pytest.mark.django_db
def test_observation_all_measurements_validated_no_measurements(default_observation):
    # No measurements → 0 unvalidated → "volledigBeoordeeld"
    assert default_observation.all_measurements_validated == "volledigBeoordeeld"


@pytest.mark.django_db
def test_observation_all_measurements_validated_with_unvalidated(default_observation, default_measurement_tvp):
    # default_measurement_tvp has status "nogNietBeoordeeld" (auto-created by signal)
    assert default_observation.all_measurements_validated == "voorlopig"


@pytest.mark.django_db
def test_observation_observationperiod_none_when_times_missing(default_observation):
    assert default_observation.observationperiod is None


@pytest.mark.django_db
def test_observation_observationperiod_calculated(default_observation):
    now = timezone.now()
    start = now - datetime.timedelta(days=10)
    default_observation.observation_starttime = start
    default_observation.observation_endtime = now
    default_observation.save()
    period = default_observation.observationperiod
    assert period is not None
    assert period.days == 10


# ---------------------------------------------------------------------------
# MeasurementTvp
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_measurement_tvp_str(default_measurement_tvp):
    result = str(default_measurement_tvp)
    assert result  # non-empty string


@pytest.mark.django_db
def test_measurement_tvp_unique_constraint(default_observation):
    measurement_time = timezone.now()
    MeasurementTvp.objects.create(
        observation=default_observation,
        measurement_time=measurement_time,
        field_value=Decimal("1.000"),
        field_value_unit="m",
    )
    with pytest.raises(IntegrityError):
        MeasurementTvp.objects.create(
            observation=default_observation,
            measurement_time=measurement_time,
            field_value=Decimal("2.000"),
            field_value_unit="m",
        )
