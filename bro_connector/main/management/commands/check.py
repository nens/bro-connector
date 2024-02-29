from django.core.management.base import BaseCommand
from django.db import transaction

import pandas as pd
import requests
import bro_exchange as brx
import json
import os
import sys
import traceback
import datetime
import logging
import bisect

from main.settings.base import gld_SETTINGS
from gld import models

failed_update_strings = ["failed_once", "failed_twice", "failed_thrice"]


class Command(BaseCommand):
    help = """Custom command for import of GIS data."""

    def handle(self, *args, **options):
        for object in models.MeasurementPointMetadata.objects.all():
            print(
                models.TypeStatusQualityControl.objects.filter(
                    id=object.qualifier_by_category_id
                )
            )
