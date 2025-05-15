from django.db import transaction
from django.core.management.base import BaseCommand
from django.db.models import Count
from gld.models import Observation, MeasurementTvp
import time

def split_large_observations(max_measurements_per_observation=7000):
    """
    Split observations with more than max_measurements_per_observation
    into multiple observations.

    Args:
        max_measurements_per_observation (int): Maximum number of measurements
        per observation before splitting. Defaults to 7000.

    Returns:
        dict: Summary of split operations
    """
    # Track the results of the splitting process
    split_summary = {
        "total_observations_processed": 0,
        "observations_split": 0,
        "total_new_observations_created": 0,
    }

    # Find observations with more than max_measurements_per_observation
    large_observations = Observation.objects.annotate(
        measurement_count=Count("measurement")
    ).filter(measurement_count__gt=max_measurements_per_observation)

    split_summary["total_observations_processed"] = large_observations.count()

    # List all fields to copy — including FKs as instances
    FIELDS_TO_COPY = [
        "observation_starttime",
        "observation_endtime",
        "result_time",
        "observation_id_bro",
        "groundwater_level_dossier",
        "observation_metadata",
        "observation_process",
        # Add more fields as needed
    ]

    for observation in large_observations:        
        measurements = observation.measurement.order_by("measurement_time")
        total_measurements = measurements.count()
        num_new_observations = (
            total_measurements + max_measurements_per_observation - 1
        ) // max_measurements_per_observation
        
        with transaction.atomic():
            # Prepare values to copy
            base_data = {field: getattr(observation, field) for field in FIELDS_TO_COPY}
            new_observations = [
                Observation.objects.create(**base_data)
                for _ in range(num_new_observations)
            ]

            # Distribute measurements across new observations
            updated = []
            for i, measurement in enumerate(measurements):
                target_index = i // max_measurements_per_observation
                measurement.observation = new_observations[target_index]
                updated.append(measurement)

            MeasurementTvp.objects.bulk_update(updated, ["observation"])
            observation.delete()

            split_summary["observations_split"] += 1
            split_summary["total_new_observations_created"] += len(new_observations)

    return split_summary


class Command(BaseCommand):
    def handle(self, *args, **options):
        # Example usage
        result = split_large_observations()
        print("Split Operation Summary:")
        print(f"Total Observations Processed: {result['total_observations_processed']}")
        print(f"Observations Split: {result['observations_split']}")
        print(
            f"Total New Observations Created: {result['total_new_observations_created']}"
        )
