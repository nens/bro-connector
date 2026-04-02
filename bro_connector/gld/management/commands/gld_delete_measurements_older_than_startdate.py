from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction
from gld.models import MeasurementTvp, Observation


class Command(BaseCommand):
    help = "Remove MeasurementTvps for an open observation that are older than the observation starttime."

    def handle(self, *args, **options):
        self.stdout.write("Looking for observations...")

        open_observations = Observation.objects.filter(
            groundwater_level_dossier__quality_regime="IMBRO",
            observation_starttime__isnull=False,
            observation_endtime__isnull=True,
        )
        ids_to_delete = []
        for obs in open_observations:
            if obs.timestamp_first_measurement == None:
                continue
            first_measurement = obs.timestamp_first_measurement
            obs_starttime = obs.observation_starttime
            if first_measurement < obs_starttime:
                old_mtvps = MeasurementTvp.objects.filter(observation=obs, measurement_time__lt=obs_starttime)
                ids_to_delete += list(old_mtvps.values_list("measurement_tvp_id"))
        if not ids_to_delete:
            self.stdout.write(self.style.SUCCESS("No old measurements found."))
            return

        # Delete in one transaction
        with transaction.atomic():
            deleted_count, _ = MeasurementTvp.objects.filter(
                id__in=ids_to_delete
            ).delete()

        self.stdout.write(
            self.style.SUCCESS(f"Deleted {deleted_count} too old measurements.")
        )
