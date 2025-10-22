import logging

import polars as pl
from django.core.management.base import BaseCommand
from gmw.models import GroundwaterMonitoringTubeStatic, GroundwaterMonitoringWellStatic

logger = logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            type=str,
            help="Het path naar de CSV met informatie over de GMW's die toegevoegd moeten worden.",
        )

    def handle(self, *args, **options):
        logger.info("Ingesting GWL depth")

        csv_pad = str(options["csv"])
        csv = pl.read_csv(
            csv_pad, ignore_errors=True, truncate_ragged_lines=True, separator=","
        )

        aanwezige_putten = []
        afwezige_putten = []

        for i, row in enumerate(csv.iter_rows(named=True)):
            # For row in CSV
            csv_search = row["search"].split("_")
            nitg_csv = csv_search[0]
            tube_csv = csv_search[1]
            gw_csv = row["gw_lichaam"]
            diepte_csv = row["diepte_klasse"]

            # Lookup database
            gmw = GroundwaterMonitoringWellStatic.objects.filter(
                nitg_code=nitg_csv
            ).first()

            # if len == 0, write to df or logging that the object was not found
            if gmw is None:
                print(f"Geen put gevonden in db voor {nitg_csv}")
                afwezige_putten.append((nitg_csv, tube_csv))
                continue

            tube_db = GroundwaterMonitoringTubeStatic.objects.filter(
                groundwater_monitoring_well_static=gmw,
                tube_number=tube_csv,
                krw_body=gw_csv,
            )

            # If len gmw > 1, assign depth, aquifer_layer to all objects
            if tube_db is None:
                print(f"Geen filter voor de put in db {nitg_csv} - {tube_csv}")
                afwezige_putten.append((nitg_csv, tube_csv))
                continue

            # if len == 1, assign depth, aquifer_layer to the object
            if tube_db is not None:
                for t in tube_db:
                    t.gwl_depth = diepte_csv
                    t.save()
                    print(
                        f"gelukt voor put {nitg_csv} met gw-lichaam {t.krw_body} en diepte {t.gwl_depth}"
                    )

                    aanwezige_putten.append(
                        (t.groundwater_monitoring_tube_static_id, nitg_csv, tube_csv)
                    )

        logging.info(f"Afwezige putten: {afwezige_putten}")
        logging.info(f"Aangevulde putten: {aanwezige_putten}")

        # gmw.depth = ... # write the code from the e-mail depending on the excel column Grondwaterlichaam
        # gmw.aquifer_layer = ... # write the code from the e-mail depending on the excel column Grondwaterlichaam

        # # Save the object to the database
        # gmw.save()
