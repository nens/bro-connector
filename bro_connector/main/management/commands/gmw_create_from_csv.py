from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from gmw.models import GroundwaterMonitoringWellStatic
import polars as pl
import os

def find_monitoring_well(nitg: str, coordinates) -> GroundwaterMonitoringWellStatic:
    # split_string = tube_str.split(sep="-")
    # well_code = split_string[0]
    # tube_nr = split_string[1]

    # print(f'nitg: {nitg}.')
    if nitg == None:
        well = GroundwaterMonitoringWellStatic.objects.filter(
            coordinates = coordinates
        ).order_by('groundwater_monitoring_well_static_id').first()
    else:
        well = GroundwaterMonitoringWellStatic.objects.filter(
            nitg_code = nitg,
            coordinates = coordinates
        ).order_by('groundwater_monitoring_well_static_id').first()
    return well

# make function to create gmw
def create_monitoring_well(df: pl.DataFrame):

    exists = 0
    did_not_exist = 0

    for row in df.iter_rows(named=True):
        nitg_code = row['NITG_nr']
        x = row['Xcoord RD']
        y = row['Ycoord RD']
        longitude, latitude = x, y
        point = Point(longitude, latitude)

        if nitg_code == "[onbekend]" or nitg_code == None:
            well = find_monitoring_well(None, point)
        else:
            well = find_monitoring_well(nitg_code, point)

        if well:
            print(f'well: {nitg_code}; coordinates in RD: {x}, {y} exists')
            exists += 1

        else:
            print(f'well: {nitg_code}; coordinates in RD: {x}, {y} did not exist, creating well static')
            did_not_exist += 1

            if nitg_code == "[onbekend]" or nitg_code == None:
                well = GroundwaterMonitoringWellStatic.objects.create(
                    coordinates = point,
                )
            else:
                well = GroundwaterMonitoringWellStatic.objects.create(
                    nitg_code = nitg_code,
                    coordinates = point,
                )

    print(f'already exist: {exists}')
    print(f'did not exist: {did_not_exist}')



class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            type=str,
            help="Het path naar de CSV met informatie over de GMW's die toegevoegd moeten worden.",
        )
    
    def handle(self, *args, **options):
        csv_path = str(options["csv"])
        if not csv_path or not csv_path.endswith('.csv'):
            raise ValueError('Invalid CSV-file supplied.')
        
        df = pl.read_csv(csv_path, ignore_errors=True)



        create_monitoring_well(df)

        