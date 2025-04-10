from django.core.management.base import BaseCommand
from gld.models import Observation, ObservationMetadata
# import polars as pl


class Command(BaseCommand):
    def handle(self, *args, **options):
        obs_metadata = Observation.objects.values_list(
            "observation_metadata__observation_metadata_id", flat=True
        ).distinct()
        print(obs_metadata)

        for obs in Observation.objects.all():
            obs_metadata: ObservationMetadata = obs.observation_metadata
            metadata = (
                ObservationMetadata.objects.filter(
                    observation_type=obs_metadata.observation_type,
                    status=obs_metadata.status,
                    responsible_party=obs_metadata.responsible_party,
                )
                .order_by("observation_metadata_id")
                .first()
            )
            obs.observation_metadata = metadata
            obs.save()

        obs_metadata = Observation.objects.values_list(
            "observation_metadata__observation_metadata_id", flat=True
        ).distinct()
        print(obs_metadata)
