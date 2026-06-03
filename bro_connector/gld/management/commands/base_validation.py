import datetime

from django.core.management.base import BaseCommand, CommandParser
from gld.models import (
    MeasurementPointMetadata,
    MeasurementTvp,
    Observation,
    Organisation,
)
from gmw.models import GroundwaterMonitoringTubeDynamic
from main.settings.base import KVK_USER
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Buffer in meters (3 cm). Measurements outside tube_top + BUFFER or tube_bottom - BUFFER are rejected.
BUFFER = 0.03


def _check_tube_top(value: float, tube_top: float, buffer: float) -> bool:
    """Return True when the measurement value exceeds the tube top (plus buffer)."""
    return value > tube_top + buffer


def _check_tube_bottom(value: float, tube_bottom: float, buffer: float) -> bool:
    """Return True when the measurement value falls below the tube bottom (minus buffer)."""
    return value < tube_bottom - buffer



class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        # Add delta t as argument
        parser.add_argument(
            "--delta_t",
            type=int,
            help="Delta t in hours to check if measurements lie within tube top and tube bottom for that period.",
        )
        return super().add_arguments(parser)

    def handle(self, *args, **options):
        # Check if the measurements are higher then the tube_top for that period, or lower then the tube_bottom.
        # Could also add a check to see if measurements are below the sensor height when those are available.

        user_organisation = Organisation.objects.get_or_create(company_number=KVK_USER)[0]
        # For all measurements within the last period, delta_t should be an argument of this command.
        delta_t = options["delta_t"]

        window_end = datetime.datetime.now()
        window_start = window_end - datetime.timedelta(hours=delta_t)
        window_start = window_start.replace(tzinfo=datetime.timezone.utc)

        observations_with_new_measurements = Observation.objects.filter(
            measurement__measurement_time__gte=window_start,
        ).distinct()

        for observation in observations_with_new_measurements:
            logger.info(f"Checking observation {observation.observation_id} for measurements within tube top and tube bottom.")
            if observation.status == "volledigBeoordeeld":
                continue

            # 1) Retrieve the tube_static linked to this observation
            tube_static = observation.groundwater_level_dossier.groundwater_monitoring_tube

            # 2) Retrieve all TubeDynamic states whose date_from falls before the window end,
            #    ordered chronologically. date_till is a Python property, so overlap with
            #    window_start is checked in Python below.
            tube_dynamics = list(
                GroundwaterMonitoringTubeDynamic.objects.filter(
                    groundwater_monitoring_tube_static=tube_static,
                    date_from__lte=window_end,
                ).order_by("date_from")
            )

            for dyn in tube_dynamics:
                logger.info(f"Checking dynamic with date_from {dyn.date_from} and date_till {dyn.date_till} (None means still active) for tube top and tube bottom checks.")
                dyn_end = dyn.date_till  # None means still active

                # Skip dynamics that ended before the check window started
                if dyn_end is not None and dyn_end <= window_start:
                    continue

                # Clamp the measurement window to this dynamic's validity period
                dyn_start = max(dyn.date_from, window_start)
                dyn_window_end = min(dyn_end, window_end) if dyn_end is not None else window_end

                tube_top = dyn.tube_top_position
                tube_bottom = dyn.tube_bottom_position

                # 3 & 4) Retrieve measurements within this dynamic's clamped window
                measurements = observation.measurement.filter(
                    measurement_time__gte=dyn_start,
                    measurement_time__lt=dyn_window_end,
                )
                logger.info(f"Found {measurements.count()} measurements for this dynamic. Checking if they lie within tube top and tube bottom.")
                measurements_to_update = []
                metadata_to_update = []

                for measurement in measurements:
                    if measurement.calculated_value is None:
                        continue

                    value = float(measurement.calculated_value)
                    rejected = False

                    if tube_top is not None and _check_tube_top(value, tube_top, BUFFER):
                        rejected = True

                    if tube_bottom is not None and _check_tube_bottom(value, tube_bottom, BUFFER):
                        rejected = True

                    if not rejected:
                        continue

                    if measurement.measurement_point_metadata is not None:
                        metadata = measurement.measurement_point_metadata
                        metadata.status_quality_control = "afgekeurd"
                        metadata_to_update.append(metadata)

                    else:
                        metadata = MeasurementPointMetadata.objects.create(
                            groundwater_level_dossier=observation.groundwater_level_dossier,
                            status_quality_control="afgekeurd",
                        )
                        measurement.measurement_point_metadata = metadata
                        measurements_to_update.append(measurement)

                # 5) Update all rejected measurements in bulk
                logger.info(f"Updating {len(measurements_to_update)} measurements that were rejected based on tube top and tube bottom checks.")
                if measurements_to_update:
                    MeasurementTvp.objects.bulk_update(
                        measurements_to_update, ["measurement_point_metadata"]
                    )

                if metadata_to_update:
                    MeasurementPointMetadata.objects.bulk_update(
                        metadata_to_update, ["status_quality_control"]
                    )
