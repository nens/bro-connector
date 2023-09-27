from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import division

from django.core.management.base import BaseCommand

import bro_uitgifte


from gmw_aanlevering.models import (
    GroundwaterMonitoringWellStatic,
)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("kvk_number", type=int)

    def handle(self, *args, **options):
        kvk_number = options["kvk_number"]

        bro_ids = bro_uitgifte.get_bro_ids(kvk_number)
        gmw_ids = bro_uitgifte.get_gmw_ids(bro_ids)
        gmw_ids_ini_count = len(gmw_ids)

        print(f"{gmw_ids_ini_count} bro ids found for organisation.")

        for well in GroundwaterMonitoringWellStatic.objects.all():
            if well.bro_id in gmw_ids:
                gmw_ids.remove(well.bro_id)

        gmw_ids_count = len(gmw_ids)
        print(f"{gmw_ids_count} not in database.")

        # Import the well data
        for id in range(gmw_ids_count):
            gmw_element = bro_uitgifte.get_gmw_data(gmw_ids[id], True)
            gmw_dict, number_of_events, number_of_tubes = bro_uitgifte.make_dict(
                gmw_element
            )

            # Invullen initiële waarden.
            gmws = bro_uitgifte.get_initial_well_static_data(gmw_dict)
            bro_uitgifte.get_initial_well_dynamic_data(gmw_dict, gmws)


            try:
                for tube_number in range(number_of_tubes):
                    tube_number = tube_number + 1
                    gmts = bro_uitgifte.get_initial_tube_static_data(gmw_dict, gmws, tube_number)
                    bro_uitgifte.get_initial_tube_dynamic_data(gmw_dict, gmts, tube_number)

                    try:
                        if int(gmts.number_of_geo_ohm_cables) == 1:
                            bro_uitgifte.get_initial_geo_ohm_data(gmw_dict, gmts, tube_number)
                            bro_uitgifte.get_initial_electrode_static_data(gmw_dict, gmws, tube_number)
                            bro_uitgifte.get_initial_electrode_dynamic_data(gmw_dict, gmws, tube_number)

                        elif int(gmts.number_of_geo_ohm_cables) > 1:
                            print(gmw_dict)
                            exit(print("Multiple Ohm Cables found for the first time. Adjust script. Message steven.hosper@nelen-schuurmans.nl"))
                    except:
                        pass
            except:
                pass

            bro_uitgifte.get_construction_event(gmw_dict, gmws)
            

            # Update based on the events
            for nr in range(number_of_events):
                nr = nr + 1
                bro_uitgifte.get_intermediate_events(gmw_dict, gmws, nr)
                

            if gmw_dict.get("removal_date", None) is not None:
                bro_uitgifte.get_removal_event(gmw_dict, gmws)

            if id % 25 == 0:
                print(round(id / len(gmw_ids), 2) * 100, "% Complete")