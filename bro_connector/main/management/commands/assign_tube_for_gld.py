from django.core.management.base import BaseCommand
from gld.models import (
    GroundwaterLevelDossier
)
from gmw.models import (
    GroundwaterMonitoringTubeStatic
)
import reversion

class Command(BaseCommand):
    def handle(self, *args, **options):
        for gld in GroundwaterLevelDossier.objects.all():
            print(gld)
            
            try:
                tube = GroundwaterMonitoringTubeStatic.objects.get(
                    groundwater_monitoring_tube_static_id = gld.groundwater_monitoring_tube_id
                )
            except GroundwaterMonitoringTubeStatic.DoesNotExist:
                print("DoesNotExist...")
                continue
            
            with reversion.create_revision():
                gld.groundwater_monitoring = tube
                gld.save()
                reversion.set_comment("Assign tube based on ID to foreign key")