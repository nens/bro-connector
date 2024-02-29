from django.core.management.base import BaseCommand
from gld.models import GroundwaterLevelDossier
from gmw.models import (
    GroundwaterMonitoringTubeStatic,
    GroundwaterMonitoringWellStatic,
)
import reversion


class Command(BaseCommand):
    def handle(self, *args, **options):
        for gld in GroundwaterLevelDossier.objects.all():
            print(gld)

            try:
                well = GroundwaterMonitoringWellStatic.objects.get(
                    bro_id=gld.gmw_bro_id,
                )
                tube = GroundwaterMonitoringTubeStatic.objects.get(
                    groundwater_monitoring_well_static=well,
                    tube_number=gld.tube_number,
                )
            except GroundwaterMonitoringWellStatic.DoesNotExist:
                print("WellDoesNotExist...")
                continue
            except GroundwaterMonitoringTubeStatic.DoesNotExist:
                print("TubeDoesNotExist...")
                continue

            with reversion.create_revision():
                gld.groundwater_monitoring_tube = tube
                gld.save()
                reversion.set_comment("Assign tube based on ID to foreign key")
