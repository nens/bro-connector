from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from gmw.models import GroundwaterMonitoringWellStatic
import polars as pl
import os


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--excel",
            type=str,
            help="Het path naar de Excel met informatie over de GMW's die toegevoegd moeten worden.",
        )

    def handle(self, *args, **options):
        # Read Excel file

        # For row in Excel file

        # Lookup in database

        gmw = GroundwaterMonitoringWellStatic.objects.filter(
            nitg_code = excel["nitg_code"]
        )
        # if len == 0, write to df or logging that the object was not found
        

        # If len gmw > 1, assign krw to all objects

        # if len == 1, assign krw to the object

        gmw = gmw.first()

        gmw.krw_body = ... # write the code from the e-mail depending on the excel column Grondwaterlichaam
        
        # Save the object to the database
        gmw.save()
