import re
from collections import defaultdict
from django.db import models
from django.db.models.query import QuerySet
from django.core.management.base import BaseCommand
from gmn.models import GroundwaterMonitoringNet, MeasuringPoint, Subgroup
from gmw.models import GroundwaterMonitoringTubeStatic, GroundwaterMonitoringWellStatic, GeoOhmCable
import numpy as np
from datetime import datetime, timedelta, tzinfo
import polars as pl


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            type=str,
            help="pad naar het csv",
        )


    def handle(self, *args, **options):
        meetnet_naam = "KRW-kwantiteit 2021"
        groundwater_aspect = "kwantiteit"  # Aangenomen waarde, klopt dit?

        # 1. Meetnet aanmaken of ophalen
        gmn, created = GroundwaterMonitoringNet.objects.update_or_create(
            name=meetnet_naam,
            quality_regime="IMBRO/A",
            deliver_to_bro= False,
            object_id_accountable_party= groundwater_aspect, 
            province_name= "Zeeland", 
            bro_domain= "GMW", 
            delivery_context= "kaderrichtlijnWater",
            monitoring_purpose= "strategischBeheerKwantiteitRegionaal",
            groundwater_aspect= groundwater_aspect,
            start_date_monitoring= "2021-01-01",
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"Meetnet '{meetnet_naam}' is aangemaakt."))
        else:
            self.stdout.write(self.style.WARNING(f"Meetnet '{meetnet_naam}' bestond al, wordt hergebruikt."))

        # 2. CSV inlezen en koppelen aan database
        csv_pad = str(options["csv"])        
        csv = pl.read_csv(csv_pad, ignore_errors=True, truncate_ragged_lines=True, separator=";")

        afwezige_putten = []
        aanwezige_putten = []

        for i, row in enumerate(csv.iter_rows(named=True)):
            if i == 0:
                continue

            NITGCode = row['NITGCode']
            tube = row['FilterNo']

            # Haal de codes en de filter nummers uit de database
            gmw = GroundwaterMonitoringWellStatic.objects.filter(nitg_code=NITGCode).first()

            if gmw is None:
                print(f'Er is geen put voor {NITGCode} - {tube}')
                afwezige_putten.append((NITGCode, tube))
                continue

            filter = GroundwaterMonitoringTubeStatic.objects.filter(
                groundwater_monitoring_well_static=gmw, tube_number=tube
            ).first()

            if filter is None:
                print(f"Geen filter gevonden voor {NITGCode} - {tube}")
                continue

            # Maak MeasuringPoint aan of haal hem op
            mp, created = MeasuringPoint.objects.get_or_create(
                gmn=gmn,
                groundwater_monitoring_tube=filter,
                defaults={
                    "code": f"{NITGCode}_{tube}",
                },
            )

            if created:
                aanwezige_putten.append((NITGCode, tube))
                print(f"MeasuringPoint aangemaakt: {mp.code}")
            else:
                print(f"MeasuringPoint bestaat al: {mp.code}")

        print(f"Ingevulde putten: {len(aanwezige_putten)}")
        print(f"Afwezige putten: {len(afwezige_putten)}")





