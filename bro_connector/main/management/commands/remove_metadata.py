from typing import Any
from django.core.management.base import BaseCommand
from gld.models import (
    Observation,
    MeasurementTvp,
    MeasurementPointMetadata,
)
import reversion


class Command(BaseCommand):
    def handle(self, *args, **options):
        batch_size = 1000  # Adjust the batch size as needed
        metadata_ids_to_delete = set()
        tvp_metadata_ids = set(
            MeasurementTvp.objects.values_list(
                "measurement_point_metadata_id", flat=True
            )
        )

        metadata_queryset = MeasurementPointMetadata.objects.all()
        total_count = metadata_queryset.count()

        for i in range(0, total_count, batch_size):
            print(i)
            batch = metadata_queryset[i : i + batch_size]
            for metadata in batch:
                if metadata.measurement_point_metadata_id not in tvp_metadata_ids:
                    metadata_ids_to_delete.add(metadata.measurement_point_metadata_id)

            MeasurementPointMetadata.objects.filter(
                measurement_point_metadata_id__in=metadata_ids_to_delete
            ).delete()
            metadata_ids_to_delete.clear()
