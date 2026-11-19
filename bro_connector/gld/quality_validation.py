from bisect import bisect_right
from collections import Counter
from dataclasses import dataclass
from datetime import timedelta
from statistics import mean, median, pstdev

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Count

from .models import MeasurementPointMetadata, MeasurementTvp, Observation

FLATLINE_INTERVAL_COUNT = 5
FLATLINE_SIGMA_MULTIPLIER = 0.1
SPIKE_SIGMA_MULTIPLIER = 3.0
PHYSICAL_TOLERANCE = 0.1
MINIMUM_MEASUREMENTS_FOR_INTERVAL_INFERENCE = 50
MAX_INFERRED_INTERVAL = timedelta(days=1)


@dataclass(frozen=True)
class ObservationValidationResult:
    measurement_count: int
    status_count: int = 0
    missing_metadata_count: int = 0
    missing_value_count: int = 0
    skip_reason: str | None = None


def _gap_cutoff(measurements: list[MeasurementTvp]) -> timedelta:
    if len(measurements) < MINIMUM_MEASUREMENTS_FOR_INTERVAL_INFERENCE:
        return timedelta(days=1)

    intervals = [
        (current.measurement_time - previous.measurement_time).total_seconds()
        for previous, current in zip(measurements, measurements[1:])
        if current.measurement_time > previous.measurement_time
    ]
    inferred_seconds = (
        median(intervals) if intervals else MAX_INFERRED_INTERVAL.total_seconds()
    )
    inferred_interval = min(timedelta(seconds=inferred_seconds), MAX_INFERRED_INTERVAL)
    return inferred_interval * 24


def _segments(measurements: list[MeasurementTvp]) -> list[list[MeasurementTvp]]:
    ordered = sorted(measurements, key=lambda item: (item.measurement_time, item.pk))
    cutoff = _gap_cutoff(ordered)
    segments: list[list[MeasurementTvp]] = [[ordered[0]]]

    for measurement in ordered[1:]:
        if measurement.measurement_time - segments[-1][-1].measurement_time > cutoff:
            segments.append([])
        segments[-1].append(measurement)

    return segments


def _combine_statuses(statuses: list[str]) -> str:
    if "afgekeurd" in statuses:
        return "afgekeurd"
    if "onbeslist" in statuses:
        return "onbeslist"
    if statuses:
        return "goedgekeurd"
    return "onbeslist"


def _apply_flatline_run(
    run: list[tuple[int, int, float]], findings: list[list[str]]
) -> None:
    if len(run) < FLATLINE_INTERVAL_COUNT:
        return
    findings[run[0][0]].append("afgekeurd")
    for _, right_index, _ in run:
        findings[right_index].append("afgekeurd")


def _validate_segment(
    measurements: list[MeasurementTvp],
    geometries: dict[int, tuple[float | None, float | None]],
) -> dict[int, str]:
    values = [
        float(measurement.calculated_value)
        if measurement.calculated_value is not None
        else None
        for measurement in measurements
    ]
    findings: list[list[str]] = [[] for _ in measurements]
    deltas = [
        (index, index + 1, values[index + 1] - values[index])
        for index in range(len(values) - 1)
        if values[index] is not None and values[index + 1] is not None
    ]

    delta_values = [delta for _, _, delta in deltas]
    delta_mean = mean(delta_values) if delta_values else 0.0
    delta_stddev = pstdev(delta_values) if len(delta_values) > 1 else 0.0

    if deltas:
        flatline_threshold = FLATLINE_SIGMA_MULTIPLIER * delta_stddev
        flatline_run: list[tuple[int, int, float]] = []
        for pair in deltas:
            low_change = abs(pair[2]) <= flatline_threshold
            if low_change and (not flatline_run or pair[0] == flatline_run[-1][1]):
                flatline_run.append(pair)
            else:
                _apply_flatline_run(flatline_run, findings)
                flatline_run = [pair] if low_change else []
        _apply_flatline_run(flatline_run, findings)

    if delta_stddev > 0:
        spike_threshold = SPIKE_SIGMA_MULTIPLIER * delta_stddev
        for left_index, right_index, delta in deltas:
            if abs(delta - delta_mean) > spike_threshold:
                findings[right_index].append("afgekeurd")

    for index, (measurement, value) in enumerate(zip(measurements, values)):
        if value is None:
            continue

        tube_top, tube_bottom = geometries[measurement.pk]
        if tube_top is not None:
            if abs(value - tube_top) <= PHYSICAL_TOLERANCE:
                findings[index].append("onbeslist")
            elif value > tube_top + PHYSICAL_TOLERANCE:
                findings[index].append("afgekeurd")
            else:
                findings[index].append("goedgekeurd")

        if tube_bottom is not None:
            if abs(value - tube_bottom) <= PHYSICAL_TOLERANCE:
                findings[index].append("onbeslist")
            elif value < tube_bottom - PHYSICAL_TOLERANCE:
                findings[index].append("afgekeurd")
            else:
                findings[index].append("goedgekeurd")

    return {
        measurement.pk: _combine_statuses(findings[index])
        for index, measurement in enumerate(measurements)
        if values[index] is not None
    }


def _measurement_geometries(
    observation: Observation, measurements: list[MeasurementTvp]
) -> dict[int, tuple[float | None, float | None]]:
    geometries = {measurement.pk: (None, None) for measurement in measurements}
    if not measurements:
        return geometries

    try:
        dossier = observation.groundwater_level_dossier
    except ObjectDoesNotExist:
        return geometries
    if dossier is None:
        return geometries

    tube = dossier.groundwater_monitoring_tube
    if tube is None:
        return geometries

    states = list(
        tube.state.filter(date_from__lte=measurements[-1].measurement_time).order_by(
            "date_from", "pk"
        )
    )
    state_dates = [state.date_from for state in states]

    for measurement in measurements:
        state_index = bisect_right(state_dates, measurement.measurement_time) - 1
        if state_index < 0:
            continue
        state = states[state_index]
        top = state.tube_top_position
        bottom = state.tube_bottom_position
        geometries[measurement.pk] = (
            float(top) if top is not None else None,
            float(bottom) if bottom is not None else None,
        )

    return geometries


def find_shared_metadata_ids(observation_ids: list[int]) -> set[int]:
    selected_metadata_ids = MeasurementTvp.objects.filter(
        observation_id__in=observation_ids,
        measurement_point_metadata__isnull=False,
    ).values_list("measurement_point_metadata_id", flat=True)
    return set(
        MeasurementTvp.objects.filter(
            measurement_point_metadata_id__in=selected_metadata_ids
        )
        .values("measurement_point_metadata_id")
        .annotate(reference_count=Count("pk"))
        .filter(reference_count__gt=1)
        .values_list("measurement_point_metadata_id", flat=True)
    )


@transaction.atomic
def validate_observation_quality(
    observation: Observation, shared_metadata_ids: set[int] | None = None
) -> ObservationValidationResult:
    measurements = list(
        observation.measurement.select_related("measurement_point_metadata").order_by(
            "measurement_time", "pk"
        )
    )
    if not measurements:
        return ObservationValidationResult(
            measurement_count=0, skip_reason="no measurements"
        )

    timestamp_counts = Counter(
        measurement.measurement_time for measurement in measurements
    )
    if any(count > 1 for count in timestamp_counts.values()):
        return ObservationValidationResult(
            measurement_count=len(measurements),
            skip_reason="duplicate measurement timestamps",
        )

    geometries = _measurement_geometries(observation, measurements)
    statuses: dict[int, str] = {}
    for segment in _segments(measurements):
        statuses.update(_validate_segment(segment, geometries))

    metadata_ids = {
        measurement.measurement_point_metadata_id
        for measurement in measurements
        if measurement.pk in statuses
        and measurement.measurement_point_metadata_id is not None
    }
    metadata_reference_counts = dict(
        MeasurementTvp.objects.filter(measurement_point_metadata_id__in=metadata_ids)
        .values("measurement_point_metadata_id")
        .annotate(reference_count=Count("pk"))
        .values_list("measurement_point_metadata_id", "reference_count")
    )

    status_count = 0
    missing_metadata_count = 0
    for measurement in measurements:
        status = statuses.get(measurement.pk)
        if status is None:
            continue

        metadata = measurement.measurement_point_metadata
        if metadata is None:
            missing_metadata_count += 1
            continue

        if (
            metadata.pk in shared_metadata_ids
            if shared_metadata_ids is not None
            else metadata_reference_counts[metadata.pk] > 1
        ):
            metadata = MeasurementPointMetadata.objects.create(
                status_quality_control=status,
                censor_reason=metadata.censor_reason,
                status_quality_control_reason_datalens=(
                    metadata.status_quality_control_reason_datalens
                ),
                value_limit=metadata.value_limit,
            )
            MeasurementTvp.objects.filter(pk=measurement.pk).update(
                measurement_point_metadata=metadata
            )
        else:
            MeasurementPointMetadata.objects.filter(pk=metadata.pk).update(
                status_quality_control=status
            )
        status_count += 1

    missing_value_count = sum(
        measurement.calculated_value is None for measurement in measurements
    )
    return ObservationValidationResult(
        measurement_count=len(measurements),
        status_count=status_count,
        missing_metadata_count=missing_metadata_count,
        missing_value_count=missing_value_count,
    )
