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

    """
    nodig voor totaal overzicht:
        - well_code
        - bro_id
        - nitg_code
        - tube_number
        - RD_X
        - RD_Y
        - delivery_accountable_party
        - gmw (None, één of meer, vang af en hoe dat te doen?)
        - subgroup (None, één of meer, vang af en hoe dat te doen?)
        - deliver_gmw_to_bro ()
        - complete_bro

        Opzoeken van gmn en subgroup kan gedaan worden door een query van alle measuring points te doen, daar overheen te loopen,
        te checken of de gelinkte tube gelijk is aan de tube waar je op dit moment mee bezig bent, zo ja, pak dan de gmw/subgroup
        en voeg deze toe aan de lijst, zoek nog uit hoe je ze erin gaat zetten

        bij het invoeren van gmn en subgroep kan je spaties tussen de namen laten, dan werkt csv omzetten waarschijnlijk goed

        Nog van oude well_check, kan ook erbij gedaan worden
        - plain_tube_part_length
        - tube_top_diameter
        - tube_top_position
        - screen_top_position
        - screen_bottom_position
    """
    
    def handle(self, *args, **options):
        output_path = str(options["output"])

        if not os.path.isdir(output_path):
            raise ValueError('Invalid output path supplied')
        

        wells = GroundwaterMonitoringWellStatic.objects.all()

        columns = ["Interne Putcode", "BRO ID", "NITG-code", "Tube nummer", "RD_X", "RD_Y", "Bronhouder", "Meetnetten", "Subgroepen", "Moet naar de BRO", "BRO Compleet", "Lengte stijgbuis [m]", "Diameter buis [mm]", "Bovenkant buis [mNAP]", "Bovenkant filter [mNAP]", "Onderkant filter [mNAP]"]
        
        df = pd.DataFrame({}, columns=columns)

        i = 0
        for well in wells:
            # well properties
            well_code = well.well_code # Interne Putcode
            bro_id = well.bro_id # BRO ID
            nitg_code = well.nitg_code # NITG-code
            coordinates = well.coordinates
            RD_X, RD_Y = str(coordinates[0]), str(coordinates[1]) # RD_X, RD_Y
            delivery_accountable_party = well.delivery_accountable_party # Bronhouder
            deliver_gmw_to_bro = well.deliver_gmw_to_bro # Moet naar de BRO
            complete_bro = well.complete_bro # BRO Compleet

            # print(nitg_code)

            # filter properties
            tube_number = None # Tube number
            plain_tube_part_length = None # Lengte stijgbuis [m]
            tube_top_diameter = None # Diameter buis [mm]
            tube_top_position = None # Bovenkant buis [mNAP]
            screen_top_position = None # Bovenkant filter [mNAP]
            screen_bottom_position = None # Onderkant filter [mNAP]

            # check for this well if there are tubes
            tubes = find_monitoring_tube(nitg_code, coordinates)

            if tubes:
                for tube in tubes:
                    tube_number = str(tube.tube_number)
                    tube_state = tube.state.order_by('date_from').last()
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


                    # GMN properties
                    gmn = None # Meetnetten
                    subgroup = None # Subgroepen

                    measuring_points = MeasuringPoint.objects.filter(groundwater_monitoring_tube=tube)

                    # loop over all MeasuringPoints for this tube to collect all gmn's and subgroups for this tube
                    for measuring_point in measuring_points:
                        measuring_point_gmn = measuring_point.gmn.name
                        if not gmn:
                            gmn = measuring_point_gmn
                        else:
                            gmn += f" {measuring_point_gmn}"
                        
                        # query all subgroups in the measuring_point and add them together
                        subgroups = measuring_point.subgroup.all()
                        for subgroup_i in subgroups:
                            subgroup_i_name = subgroup_i.name
                            if not subgroup:
                                subgroup = subgroup_i_name
                            elif subgroup_i_name not in subgroup:
                                subgroup += f" {subgroup_i_name}"
                        
                
                    parameters = [well_code, bro_id, nitg_code, tube_number, RD_X, RD_Y, delivery_accountable_party, gmn, subgroup, deliver_gmw_to_bro, complete_bro, plain_tube_part_length, tube_top_diameter, tube_top_position, screen_top_position, screen_bottom_position]
                    df.loc[len(df)] = parameters


        savepath = output_path + f"\putten_overzicht.csv"
        df.to_csv(savepath, index=False)






