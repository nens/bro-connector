from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from django.db.models import Q
from gmw.models import GroundwaterMonitoringWellStatic, GroundwaterMonitoringTubeStatic
from gld.models import Observation, ObservationProcess
# import polars as pl
import csv
import re
import os
from datetime import datetime
import pandas as pd

class Command(BaseCommand):
    def handle(self, *args, **options):
        obs_process_ids = Observation.objects.values_list("observation_process__observation_process_id", flat=True).distinct()
        for process in ObservationProcess.objects.all():
            if process.observation_process_id not in obs_process_ids:
                process.delete()