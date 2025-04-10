from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from django.db.models import Q
from gmw.models import GroundwaterMonitoringWellStatic, GroundwaterMonitoringTubeStatic
from gld.models import Observation, ObservationMetadata
# import polars as pl
import csv
import re
import os
from datetime import datetime
import pandas as pd

class Command(BaseCommand):
    def handle(self, *args, **options):
        obs_metadata_ids = Observation.objects.values_list("observation_metadata__observation_metadata_id", flat=True).distinct()
        for metadata in ObservationMetadata.objects.all():
            if metadata.observation_metadata_id not in obs_metadata_ids:
                metadata.delete()