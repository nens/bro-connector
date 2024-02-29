from typing import Any
from django.core.management.base import BaseCommand
from gld.models import GroundwaterLevelDossier
from gmw.models import GroundwaterMonitoringWellStatic, GroundwaterMonitoringTubeStatic
from ..tasks.bro_handlers import GLDHandler
import reversion


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> str | None:
        glds = GroundwaterLevelDossier.objects.filter(groundwater_monitoring_tube=None)
        handler = GLDHandler()

        for gld in glds:
            print(gld, gld.groundwater_level_dossier_id)
            handler.get_data(gld.gld_bro_id, True)
            # To debug the error
            handler.root_data_to_dictionary()
            gld_dict = handler.dict

            bro_id = gld_dict["0_broId"][1]
            tube_number = gld_dict["0_tubeNumber"]

            well = GroundwaterMonitoringWellStatic.objects.get(bro_id=bro_id)
            tube = GroundwaterMonitoringTubeStatic.objects.get(
                groundwater_monitoring_well_static=well,
                tube_number=tube_number,
            )
            print(tube)
            gld.groundwater_monitoring_tube = tube
            gld.save()
            print(gld.groundwater_monitoring_tube)
