from django.core.management.base import BaseCommand

from main.utils.gar_fieldform import FieldFormGenerator
from gmn.models import GroundwaterMonitoringNet


class Command(BaseCommand):
    help = "Generate a FieldForm Locations document."

    def handle(self, *args, **options):
        # Create HMN FieldFrom
        try:
            generator1 = FieldFormGenerator()
            generator1.monitoringnetworks = GroundwaterMonitoringNet.objects.filter(
                name = 'GAR_MEETNET_NAME'
            )
            generator1.generate()
            # generator2.delete_old_files_from_ftp()
        except Exception as e:
            print(f"Error during HMN FieldForm: {e}")