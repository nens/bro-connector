from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from gmw.models import GroundwaterMonitoringWellStatic
from gmw.models import GroundwaterMonitoringTubeStatic
import polars as pl
import os

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            type=str,
            help="Het path naar de Excel met informatie over de GMW's die toegevoegd moeten worden.",
        )

    def handle(self, *args, **options):
        # Read Excel file
        csv_pad = str(options["csv"])
        csv = pl.read_csv(csv_pad, ignore_errors=True, truncate_ragged_lines=True, separator=";")

        # For row in Excel file
        i = 0
        for i, row in enumerate(csv.iter_rows(named=True)):
            if i == 0:
                continue

            grondwaterlichaam = row['Grondwaterlichaam']
            NITGCode = row['NITGCode']
            tube = row['FilterNo']

        # Lookup in database
            gmw = GroundwaterMonitoringWellStatic.objects.filter(
                nitg_code = NITGCode
            )
            if len(gmw) == 0:
                print('er is geen put')
                continue
            

            filter = GroundwaterMonitoringTubeStatic.objects.filter(groundwater_monitoring_well_static = gmw, tube_number = tube)            

        # if len == 0, write to df or logging that the object was not found
            if len(filter) == 0:
                print('koekoek deze rij gaat mis')

            # If len gmw > 1, assign krw to all objects
            filter = filter.first()
            if len(gmw) >= 0:
                filter.grondwaterlichaam = grondwaterlichaam
                filter.save()

        # if len == 1, assign krw to the object

        gmw = gmw.first()

        gmw.krw_body = ... # write the code from the e-mail depending on the excel column Grondwaterlichaam
        
        # Save the object to the database
        gmw.save()
