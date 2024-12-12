from django.core.management.base import BaseCommand
from gmn.models import GroundwaterMonitoringNet, MeasuringPoint, Subgroup
from gmw.models import GroundwaterMonitoringWellStatic, GroundwaterMonitoringWellDynamic, GroundwaterMonitoringTubeDynamic, GroundwaterMonitoringTubeStatic
# import polars as pl
import pandas as pd
import os

def find_monitoring_tube(nitg_code: str, loc) -> GroundwaterMonitoringTubeStatic:
    # if nitg_code is given and not None
    if nitg_code:
        tubes = GroundwaterMonitoringTubeStatic.objects.filter(
            groundwater_monitoring_well_static__nitg_code = nitg_code,
        ).order_by('groundwater_monitoring_tube_static_id').all()
    # else, try to use the location if it is not None
    # by finding the well first and then the tubes using the well static
    elif loc:
        well = GroundwaterMonitoringWellStatic.objects.filter(
            coordinates = loc,
        ).order_by("groundwater_monitoring_well_static_id").first()
        tubes = GroundwaterMonitoringTubeStatic.objects.filter(
            groundwater_monitoring_well_static = well,
        ).order_by('groundwater_monitoring_well_static_id').all()
    # else no tubes found, return None
    else:
        tubes = None
    return tubes

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            help="Het path waar de CSV geplaatst wordt met informatie over de putten met missende informatie.",
        )

    # waar de filter diameter of diameter top buis ontbreekt
    # Buishoogte, filter diepte, diameters <- die zijn voor nu belangrijk om te checken
    
    def handle(self, *args, **options):
        output_path = str(options["output"])

        if not os.path.isdir(output_path):
            raise ValueError('Invalid output path supplied')
        

        wells = GroundwaterMonitoringWellStatic.objects.all()

        columns = ["Putcode", "NITG-code", "buis nummer", "RD_X", "RD_Y", "Lengte stijgbuis [m]", "Diameter buis [mm]", "Bovenkant buis [mNAP]", "Bovenkant filter [mNAP]", "Onderkant filter [mNAP]"]
        df = pd.DataFrame({}, columns=columns)
        i = 0
        j = 0
        k = 0
        for well in wells:
            well_code = well.well_code
            coordinates = well.coordinates
            RD_X, RD_Y = str(coordinates[0]), str(coordinates[1])
            # catch wells with None as nitg_code and how to handle those by looking using the location
            # only perform this on wells that are not surface wells (nitg_code starting with P)
            if well.nitg_code and well.nitg_code[0] != "P":
                nitg_code = well.nitg_code
                tubes = find_monitoring_tube(well.nitg_code, coordinates)

                if tubes:
                    for tube in tubes:
                        tube_number = str(tube.tube_number)
                        tube_state = tube.state.order_by('date_from').last()
                        j += 1
                        if tube_state:
                            plain_tube_part_length = tube_state.plain_tube_part_length
                            if plain_tube_part_length:
                                plain_tube_part_length = round(plain_tube_part_length, 2)

                            tube_top_diameter = tube_state.tube_top_diameter
                            if tube_top_diameter:
                                tube_top_diameter = round(tube_top_diameter, 2)

                            tube_top_position = tube_state.tube_top_position
                            if tube_top_position:
                                tube_top_position = round(tube_top_position, 2)

                            screen_top_position = tube_state.screen_top_position
                            if screen_top_position:
                                screen_top_position = round(screen_top_position, 2)

                            screen_bottom_position = tube_state.screen_bottom_position
                            if screen_bottom_position:
                                screen_bottom_position = round(screen_bottom_position, 2)
                            
                            parameters = [well_code, nitg_code, tube_number, RD_X, RD_Y, plain_tube_part_length, tube_top_diameter, tube_top_position, screen_top_position, screen_bottom_position]

                            if None in parameters:
                                df.loc[len(df)] = parameters
                        else:
                            plain_tube_part_length, tube_top_diameter, tube_top_position, screen_top_position, screen_bottom_position = None, None, None, None, None
                            
                            parameters = [well_code, nitg_code, tube_number, RD_X, RD_Y, plain_tube_part_length, tube_top_diameter, tube_top_position, screen_top_position, screen_bottom_position]

                            df.loc[len(df)] = parameters


                else:
                    k += 1
                    tube_number = None
                    plain_tube_part_length, tube_top_diameter, tube_top_position, screen_top_position, screen_bottom_position = None, None, None, None, None
                    parameters = [well_code, nitg_code, tube_number, RD_X, RD_Y, plain_tube_part_length, tube_top_diameter, tube_top_position, screen_top_position, screen_bottom_position]

                    df.loc[len(df)] = parameters
            
            else:
                i+=1
                nitg_code = None
                tube_number = None
                plain_tube_part_length, tube_top_diameter, tube_top_position, screen_top_position, screen_bottom_position = None, None, None, None, None

                parameters = [well_code, nitg_code, tube_number, RD_X, RD_Y, plain_tube_part_length, tube_top_diameter, tube_top_position, screen_top_position, screen_bottom_position]

                df.loc[len(df)] = parameters
                
        print(f"number of None nitg code wells: {i}, number of tubes: {j}, number of wells without tube {k}")

        savepath = output_path + f"\putten_met_lege_waardes.csv"
        df.to_csv(savepath)






