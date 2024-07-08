import reversion

from django.core.management.base import BaseCommand
from logging import getLogger

from gld.models import MeasurementTvp, MeasurementPointMetadata

logger = getLogger(__name__)

class Command(BaseCommand):
    def handle(self, *args, **options):
        for mtvp in MeasurementTvp.objects.filter(measurement_point_metadata_id__isnull=True):
            self.stdout.write(f"Adjusting mtvp: {mtvp}.")
            metadata = MeasurementPointMetadata.objects.create(
                status_quality_control = "nogNietBeoordeeld"
            )

            with reversion.create_revision():
                mtvp.measurement_point_metadata_id = metadata.measurement_point_metadata_id
                mtvp.save(update_fields=["measurement_point_metadata_id"])
                reversion.set_comment("Corrected the metadata.")

