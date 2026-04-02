from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Min
from gld.models import MeasurementTvp, Observation


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
        "up_to_date_in_bro",
        # Add more fields as needed
    ]

    for i, observation in enumerate(large_observations):
        print(f"Splitting observation {int(i + 1)}/{len(large_observations)}")
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


def split_observations_older_than_two_weeks_with_data():
    """
    Split observations older than two weeks with more than 7000 measurements.
    """
    from datetime import timedelta

    from django.utils import timezone

    # time from first measurement in observation is older than two weeks
    old_observations = Observation.objects.filter(
        observation_endtime__isnull=True
    ).annotate(measurement_first_time=Min("measurement__measurement_time"))

    for observation in old_observations:
        if (
            observation.measurement_first_time
            and observation.measurement_first_time < timezone.now() - timedelta(weeks=2)
        ):
            print(
                f"Observation {observation.observation_id} is older than two weeks with first measurement at {observation.measurement_first_time} and current startdate {observation.observation_starttime}"
            )
            observation.observation_endtime = observation.timestamp_last_measurement
            observation.result_time = observation.timestamp_last_measurement
            observation.save(update_fields=["observation_endtime", "result_time"])
            print(
                f"Updated observation {observation.observation_id} with endtime {observation.observation_endtime} and result_time {observation.result_time}"
            )


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

        split_observations_older_than_two_weeks_with_data()
