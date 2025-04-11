from django.core.management.base import BaseCommand
from gld.models import Observation, ObservationProcess
# import polars as pl


class Command(BaseCommand):
    def handle(self, *args, **options):
        obs_process_ids = Observation.objects.values_list(
            "observation_process__observation_process_id", flat=True
        ).distinct()
        for process in ObservationProcess.objects.all():
            if process.observation_process_id not in obs_process_ids:
                process.delete()
