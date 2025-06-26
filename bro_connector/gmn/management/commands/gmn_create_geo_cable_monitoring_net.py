import re
from collections import defaultdict
from django.db import models
from django.db.models.query import QuerySet
from django.core.management.base import BaseCommand
from gmn.models import GroundwaterMonitoringNet, MeasuringPoint, Subgroup
from gmw.models import GroundwaterMonitoringTubeStatic, GroundwaterMonitoringWellStatic, GeoOhmCable
import numpy as np
from datetime import datetime, timedelta, tzinfo

class Command(BaseCommand):
    """This command handles all 4 type of registrations for GMN's
    It uses the IntermediateEvents table as input.
    In this table, the event_type column holds the information for which BRO request to handle.
    The synced_to_bro column is the administration for whether the information is allready sent to the BRO.
    The deliver_to_bro in the event determines whether a event should be synced.

    The 4 requests that are handled are:
        - GMN_StartRegistration
        - GMN_MeasuringPoint
        - GMN_MeasuringPointEndDate
        - GMN_Closure


    GMNs:
    - krw_kwal_{year}
    - GAR_{year}
    - krw_kantiteit{year}
    - kmg_kwal_{year}
    - PMG_kwantiteit_{extra}

    """
    def add_arguments(self, parser):
        parser.add_argument(
            "--name",
            type=str,
            help="Naam van het meetnet",
        )

    def handle(self, *args, **options):
        name = options["naam"]
        print(name)
        stop

        tubes = get_tubes_with_geo_ohm_cable()
        gmn = create_monitoring_net(name, tubes)


def get_tubes_with_geo_ohm_cable():
    tube_ids = []
    tubes = GroundwaterMonitoringTubeStatic.objects.all()
    for tube in tubes:
        if GeoOhmCable.objects.filter(groundwater_monitoring_tube_static=tube):
            tube_ids.append(tube.groundwater_monitoring_tube_static_id)
    geo_cable_tubes = GroundwaterMonitoringTubeStatic.objects.filter(groundwater_monitoring_tube_static_id__in=tube_ids)

    return geo_cable_tubes

def create_monitoring_net(name, tubes):
    if not name:
        name = "Zoutwachter Meetnet"

    gmn, created = GroundwaterMonitoringNet.objects.update_or_create(
        name=name,
        deliver_to_bro=False,
        description="Meetnet dat alle putten met een zoutwachter weergeeft",
        quality_regime="IMBRO/A",
        delivery_context="waterwetPeilbeheer",
        monitoring_purpose="strategischBeheerKwantiteitRegionaal",
        groundwater_aspect="kwaliteit",
    )
    if created:
        gmn.start_date_monitoring = datetime.now()
    
    for tube in tubes:
        measuring_point, created = MeasuringPoint.objects.get_or_create(
            gmn = gmn,
            groundwater_monitoring_tube = tube,
        )
        if created: 
            measuring_point.added_to_gmn_date = datetime.now()
        