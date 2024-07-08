from django.core.management.base import BaseCommand
from gld.models import MeasurementPointMetadata, MeasurementTvp

class Command(BaseCommand):
    help = 'Delete MeasurementPointMetadata entries not referenced by any MeasurementTvp'

    def handle(self, *args, **kwargs):
        # Find all MeasurementPointMetadata instances
        all_metadata = MeasurementPointMetadata.objects.all()
        # Find all MeasurementPointMetadata instances that are referenced by MeasurementTvp
        referenced_metadata_ids = MeasurementTvp.objects.values_list('measurement_point_metadata_id', flat=True).distinct()
        # Find all unreferenced MeasurementPointMetadata instances
        unreferenced_metadata = all_metadata.exclude(measurement_point_metadata_id__in=referenced_metadata_ids)
        # Count and delete unreferenced instances
        count = unreferenced_metadata.count()
        unreferenced_metadata.delete()
        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {count} unreferenced MeasurementPointMetadata entries'))