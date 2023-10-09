from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import division

from django.core.management.base import BaseCommand

import bro_connector.gmw_aanlevering.management.commands.tasks.bro_uitgifte as bro


from gmw_aanlevering.models import (
    GroundwaterMonitoringWellStatic,
)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--kvk_number",
            type=int,
            help="Gebruik een KVK-nummer om de data in te spoelen")
        parser.add_argument(
            "--csv_file",
            type=str,
            help="Gebruik een csv bestand met putinformatie om data in te spoelen")

    def handle(self, *args, **options):
        progressor = bro.Progress()
        gmw        = bro.GMWHandler()

        kvk_number = options["kvk_number"]
        csv_file   = options["csv_file"]

        if kvk_number != None:
            DR = bro.DataRetrieverKVK(kvk_number)
            DR.get_ids_kvk()
            gmw_ids = DR.gmw_ids
            gmw_ids_ini_count = len(gmw_ids)
        
        elif csv_file != None:
            DR = bro.DataRetrieverFile(csv_file)
            DR.retrieve()
            exit()



        print(f"{gmw_ids_ini_count} bro ids found for organisation.")

        for well in GroundwaterMonitoringWellStatic.objects.all():
            if well.bro_id in gmw_ids:
                gmw_ids.remove(well.bro_id)

        gmw_ids_count = len(gmw_ids)
        print(f"{gmw_ids_count} not in database.")

        progressor.calibrate(gmw_ids, 25)

        # Import the well data
        for id in range(gmw_ids_count):
            gmw.get_data(gmw_ids[id], True)
            gmw.make_dict()
            gmw_dict = gmw.dict

            # Invullen initiële waarden.
            ini = bro.InitializeData(gmw_dict)
            ini.well_static()
            gmws = ini.gmws
            ini.well_dynamic()


            try:
                for tube_number in range(gmw.number_of_tubes):
                    ini.increment_tube_number()
                    ini.tube_static()
                    ini.tube_dynamic()

                    try:
                        for geo_ohm_cable in range(int(ini.gmts.number_of_geo_ohm_cables)):
                            ini.geo_ohm()
                            ini.electrode_static()
                            ini.electrode_dynamic()

                    except:
                        raise Exception("Failed")
            except:
                raise Exception("Failed")

            bro.get_construction_event(gmw_dict, gmws)

            # Update based on the events
            for nr in range(int(gmw.number_of_events)):
                updater = bro.Updater(gmw.dict, gmws)
                updater.intermediate_events()

            gmw.reset_values()
            ini.reset_tube_number()
            progressor.next()
            progressor.progress()