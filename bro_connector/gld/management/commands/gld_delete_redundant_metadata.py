from django.core.management.base import BaseCommand
from gld.models import Observation, ObservationMetadata

# import polars as pl


class Command(BaseCommand):
    def handle(self, *args, **options):
        obs_metadata_ids = Observation.objects.values_list(
            "observation_metadata__observation_metadata_id", flat=True
        ).distinct()
        for metadata in ObservationMetadata.objects.all():
            if metadata.observation_metadata_id not in obs_metadata_ids:
                metadata.delete()
