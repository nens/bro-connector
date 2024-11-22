from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from gmw.models import GroundwaterMonitoringWellStatic
import polars as pl
import os
def find_monitoring_well(nitg: str) -> GroundwaterMonitoringWellStatic:
    well = GroundwaterMonitoringWellStatic.objects.filter(
        nitg_code = nitg
    ).order_by('groundwater_monitoring_well_static_id').first()
    return well

# make function to create gmw
def create_monitoring_well(df: pl.DataFrame):

    exists = 0
    no_or_invalid_nitg = 0
    did_not_exist = 0

    for row in df.iter_rows(named=True):
        nitg_code = row['NITG_nr']
        x = row['Xcoord RD']
        y = row['Ycoord RD']
        longitude, latitude = x, y
        point = Point(longitude, latitude)

        # if the nitg code is unknown or empty, or it does not start with a "B" to indicate a groundwater monitoring well, skip adding it.
        # else, check if it is already in the dataset, if not, add it with the nitg code and coordinates
        if (nitg_code == "[onbekend]") or (nitg_code == None) or (not nitg_code.startswith("B")):
            no_or_invalid_nitg += 1
            print(f'well: {nitg_code}; \tcoordinates in RD: {x}, {y} \tis invalid and will not be created')
            continue
        else:
            well = find_monitoring_well(nitg_code)

        if well:
            print(f'well: {nitg_code}; \tcoordinates in RD: {x}, {y} \texists')
            exists += 1

        else:
            print(f'well: {nitg_code}; \tcoordinates in RD: {x}, {y} \tdid not exist')
            did_not_exist += 1
        
            well = GroundwaterMonitoringWellStatic.objects.create(
                nitg_code = nitg_code,
                coordinates = point,
            )

    print(f'already exist: {exists}')
    print(f'no or invalid nitg code: {no_or_invalid_nitg}')
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
        if not os.path.isdir(csv_path):
            raise ValueError("Invalid path to csv's supplied")
        
        df = pl.read_csv(csv_path+"\Peilbuizen natuur.csv", ignore_errors=True)
        create_monitoring_well(df)
        df = pl.read_csv(csv_path+"\Peilbuizen Natuurmonumenten Zeeland Dino TNO.csv", ignore_errors=True)
        create_monitoring_well(df)



        