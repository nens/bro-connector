from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from gmw.models import GroundwaterMonitoringWellStatic
import polars as pl
import os

class Command(BaseCommand):
    help = "Fixes internal_id of GroundwaterMonitoringWellStatic after creating internal_id."

    def handle(self, *args, **options):
        for well in GroundwaterMonitoringWellStatic.objects.all():
            well.internal_id = str(well)
            well.save()