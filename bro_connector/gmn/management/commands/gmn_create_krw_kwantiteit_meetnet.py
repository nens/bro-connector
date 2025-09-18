import logging
from datetime import datetime

import polars as pl
from django.core.management.base import BaseCommand
from gmn.models import GroundwaterMonitoringNet, MeasuringPoint
from gmw.models import GroundwaterMonitoringTubeStatic, GroundwaterMonitoringWellStatic

logger = logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            type=str,
            help="pad naar het csv",
        )

    def handle(self, *args, **options):
        logger.info("Creating/updating KRW-kwantiteit 2021 GMN")

        meetnet_naam = "KRW-kwantiteit 2021"
        groundwater_aspect = "kwantiteit"  # Aangenomen waarde, klopt dit?

        # 1. Meetnet aanmaken of ophalen
        gmn, created = GroundwaterMonitoringNet.objects.update_or_create(
            name=meetnet_naam,
            quality_regime="IMBRO",
            deliver_to_bro=False,
            object_id_accountable_party=groundwater_aspect,
            province_name="Zeeland",
            bro_domain="GMW",
            delivery_context="kaderrichtlijnWater",
            monitoring_purpose="strategischBeheerKwantiteitRegionaal",
            groundwater_aspect=groundwater_aspect,
            start_date_monitoring="2021-01-01",
        )

        if created:
            logger.info(f"Meetnet '{meetnet_naam}' is aangemaakt.")
        else:
            logger.info(f"Meetnet '{meetnet_naam}' bestond al, wordt hergebruikt.")

        # 2. CSV inlezen en koppelen aan database
        csv_pad = str(options["csv"])
        csv = pl.read_csv(
            csv_pad, ignore_errors=True, truncate_ragged_lines=True, separator=";"
        )

        afwezige_putten = []
        aanwezige_putten = []

        for i, row in enumerate(csv.iter_rows(named=True)):
            if i == 0:
                continue

            NITGCode = row["NITGCode"]
            tube = row["FilterNo"]

            # Haal de codes en de filter nummers uit de database
            gmw = GroundwaterMonitoringWellStatic.objects.filter(
                nitg_code=NITGCode
            ).first()

            if gmw is None:
                print(f"Er is geen put voor {NITGCode} - {tube}")
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
                defaults={"added_to_gmn_date": datetime(2021, 1, 1)},
            )

            aanwezige_putten.append((NITGCode, tube))
            if created:
                logger.info(f"MeasuringPoint aangemaakt: {mp.code}")
            else:
                logger.info(f"MeasuringPoint bestaat al: {mp.code}")

        logger.info(f"Ingevulde putten: {len(aanwezige_putten)}")
        logger.info(f"Afwezige putten: {len(afwezige_putten)}")
