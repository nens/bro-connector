import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory
from gld.admin import ObservationAdmin
from gld.models import MeasurementTvp, Observation
from gld.quality_validation import (
    _segments,
    _validate_segment,
    validate_observation_quality,
)


def _measurement(pk, measurement_time, value):
    return MeasurementTvp(
        pk=pk,
        measurement_time=measurement_time,
        calculated_value=Decimal(str(value)) if value is not None else None,
    )


def test_quality_rules_match_flatline_and_spike_statuses():
    start = datetime.datetime(2021, 1, 1, tzinfo=datetime.UTC)
    flatline = [
        _measurement(index, start + datetime.timedelta(hours=index), value)
        for index, value in enumerate([0, 0, 0, 0, 0, 0, 10])
    ]
    flatline_statuses = _validate_segment(
        flatline, {measurement.pk: (None, None) for measurement in flatline}
    )
    assert [flatline_statuses[index] for index in range(6)] == ["afgekeurd"] * 6
    assert flatline_statuses[6] == "onbeslist"

    null_gap = [
        _measurement(index, start + datetime.timedelta(hours=index), value)
        for index, value in enumerate([0, 0, 0, None, 0, 0, 0, 0])
    ]
    null_gap_statuses = _validate_segment(
        null_gap, {measurement.pk: (None, None) for measurement in null_gap}
    )
    assert set(null_gap_statuses.values()) == {"onbeslist"}

    spike_values = [0] * 14 + [10, 10]
    spikes = [
        _measurement(index, start + datetime.timedelta(hours=index), value)
        for index, value in enumerate(spike_values)
    ]
    spike_statuses = _validate_segment(
        spikes, {measurement.pk: (None, None) for measurement in spikes}
    )
    assert spike_statuses[14] == "afgekeurd"


def test_measurement_segments_use_day_and_inferred_gap_cutoffs():
    start = datetime.datetime(2021, 1, 1, tzinfo=datetime.UTC)
    short_series = [
        _measurement(index, start + datetime.timedelta(days=day), 1)
        for index, day in enumerate([0, 1, 3])
    ]
    assert [len(segment) for segment in _segments(short_series)] == [2, 1]

    frequent_times = [
        start + datetime.timedelta(hours=2 * index) for index in range(49)
    ]
    frequent_times.append(frequent_times[-1] + datetime.timedelta(days=10))
    long_series = [
        _measurement(index, measurement_time, 1)
        for index, measurement_time in enumerate(reversed(frequent_times))
    ]
    assert [len(segment) for segment in _segments(long_series)] == [49, 1]


@pytest.mark.django_db
def test_quality_validation_updates_numeric_status_and_preserves_null_status(
    default_measurement_tvp, default_tube_dynamic
):
    observation = default_measurement_tvp.observation
    metadata_to_preserve = default_measurement_tvp.measurement_point_metadata
    metadata_to_preserve.status_quality_control = "afgekeurd"
    metadata_to_preserve.value_limit = Decimal("1.25")
    metadata_to_preserve.save(update_fields=["status_quality_control", "value_limit"])

    second = MeasurementTvp.objects.create(
        observation=observation,
        measurement_time=default_measurement_tvp.measurement_time
        + datetime.timedelta(hours=1),
        field_value=Decimal("-4"),
        field_value_unit="m",
    )
    third = MeasurementTvp.objects.create(
        observation=observation,
        measurement_time=default_measurement_tvp.measurement_time
        + datetime.timedelta(hours=2),
        field_value=Decimal("-3"),
        field_value_unit="m",
    )
    MeasurementTvp.objects.filter(pk=default_measurement_tvp.pk).update(
        calculated_value=Decimal("-5")
    )
    MeasurementTvp.objects.filter(pk=second.pk).update(calculated_value=Decimal("-4"))
    MeasurementTvp.objects.filter(pk=third.pk).update(calculated_value=None)
    third.measurement_point_metadata.status_quality_control = "afgekeurd"
    third.measurement_point_metadata.save(update_fields=["status_quality_control"])

    result = validate_observation_quality(observation)

    default_measurement_tvp.measurement_point_metadata.refresh_from_db()
    second.measurement_point_metadata.refresh_from_db()
    third.measurement_point_metadata.refresh_from_db()
    assert result.status_count == 2
    assert result.missing_value_count == 1
    assert (
        default_measurement_tvp.measurement_point_metadata.status_quality_control
        == "onbeslist"
    )
    assert second.measurement_point_metadata.status_quality_control == "afgekeurd"
    assert third.measurement_point_metadata.status_quality_control == "afgekeurd"
    assert default_measurement_tvp.measurement_point_metadata.value_limit == "1.25"


@pytest.mark.django_db
def test_quality_action_splits_shared_metadata_for_each_numeric_measurement(
    default_measurement_tvp, default_tube_dynamic
):
    observation = default_measurement_tvp.observation
    shared_metadata = default_measurement_tvp.measurement_point_metadata
    shared_metadata.value_limit = Decimal("2.5")
    shared_metadata.save(update_fields=["value_limit"])
    second = MeasurementTvp.objects.create(
        observation=observation,
        measurement_time=default_measurement_tvp.measurement_time
        + datetime.timedelta(hours=1),
        field_value=Decimal("-4"),
        field_value_unit="m",
    )
    MeasurementTvp.objects.filter(pk=default_measurement_tvp.pk).update(
        calculated_value=Decimal("-5")
    )
    MeasurementTvp.objects.filter(pk=second.pk).update(
        calculated_value=Decimal("-4"),
        measurement_point_metadata=shared_metadata,
    )
    shared_metadata.status_quality_control = "goedgekeurd"
    shared_metadata.save(update_fields=["status_quality_control"])

    request = RequestFactory().post("/")
    request.session = {}
    request._messages = FallbackStorage(request)
    admin = ObservationAdmin(Observation, AdminSite())
    admin.validate_measurement_quality(
        request, Observation.objects.filter(pk=observation.pk)
    )

    default_measurement_tvp.refresh_from_db()
    second.refresh_from_db()
    shared_metadata.refresh_from_db()
    assert default_measurement_tvp.measurement_point_metadata_id != shared_metadata.pk
    assert second.measurement_point_metadata_id != shared_metadata.pk
    assert (
        default_measurement_tvp.measurement_point_metadata_id
        != second.measurement_point_metadata_id
    )
    assert shared_metadata.status_quality_control == "goedgekeurd"
    assert default_measurement_tvp.measurement_point_metadata.value_limit == "2.5"
    assert second.measurement_point_metadata.value_limit == "2.5"


@pytest.mark.django_db
def test_quality_action_skips_observation_with_duplicate_timestamps(
    default_measurement_tvp,
):
    first = SimpleNamespace(
        pk=1, measurement_time=default_measurement_tvp.measurement_time
    )
    second = SimpleNamespace(
        pk=2, measurement_time=default_measurement_tvp.measurement_time
    )
    measurements = Mock()
    measurements.select_related.return_value.order_by.return_value = [first, second]
    observation = SimpleNamespace(measurement=measurements)

    result = validate_observation_quality(observation)

    assert result.skip_reason == "duplicate measurement timestamps"


@pytest.mark.django_db
def test_quality_validation_skips_observation_without_measurements(default_observation):
    result = validate_observation_quality(default_observation)

    assert result.skip_reason == "no measurements"
