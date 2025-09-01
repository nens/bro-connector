from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from gmw.models import GroundwaterMonitoringWellStatic, GroundwaterMonitoringTubeStatic
import polars as pl
import os


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            type=str,
            help="Het path naar de CSV met informatie over de GMW's die toegevoegd moeten worden.",
        )

    def handle(self, *args, **options):
        csv_pad = str(options["csv"])
        csv = pl.read_csv(csv_pad, ignore_errors=True, truncate_ragged_lines=True, separator=",")

        afwezige_putten = []

        for i, row in enumerate(csv.iter_rows(named=True)):

            # For row in CSV    
            csv_search = row["search"].split("_")
            nitg_csv = csv_search[0]
            tube_csv = csv_search[1]
            gw_csv = row["gw_lichaam"]
            diepte_csv = row["diepte_klasse"]

            # Lookup database
            gmw = GroundwaterMonitoringWellStatic.objects.filter(nitg_code=nitg_csv).first()

            # if len == 0, write to df or logging that the object was not found
            if gmw is None:
                print(f'Geen put gevonden in db voor {nitg_csv}')
                afwezige_putten.append((nitg_csv))
                continue

            tube_db = GroundwaterMonitoringTubeStatic.objects.filter(groundwater_monitoring_well_static=gmw, tube_number=tube_csv).first()
        
            # If len gmw > 1, assign depth, aquifer_layer to all objects
            if tube_db is None:
                print(f'Geen filter voor de put in db {nitg_csv} - {tube_csv}')
                continue

            # if len == 1, assign depth, aquifer_layer to the object
            if tube_db is not None:
                tube_db.krw_body = gw_csv
                gmw.depth = diepte_csv

                gmw.save()
                tube_db.save()

                print(f'gelukt voor put {nitg_csv} met gw-lichaam {tube_db.krw_body} en diepte {gmw.depth}')    

        print(f'niet gelukt voor {afwezige_putten}')

            # gmw.depth = ... # write the code from the e-mail depending on the excel column Grondwaterlichaam
            # gmw.aquifer_layer = ... # write the code from the e-mail depending on the excel column Grondwaterlichaam
            
            # # Save the object to the database
            # gmw.save()
