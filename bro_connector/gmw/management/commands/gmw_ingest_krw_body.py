from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from gmw.models import GroundwaterMonitoringWellStatic
from gmw.models import GroundwaterMonitoringTubeStatic
import polars as pl
import logging

logger = logger = logging.getLogger(__name__)

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            type=str,
            help="Het path naar de Excel met informatie over de GMW's die toegevoegd moeten worden.",
        )

    def handle(self, *args, **options):
        logger.info("Ingesting KRW body")
        # Read csv file
        csv_pad = str(options["csv"])
        csv = pl.read_csv(csv_pad, ignore_errors=True, truncate_ragged_lines=True, separator=";")

        krw_code = {
            "Zoet grondwater in duingebieden": "NLGWSC0001",
            "Zoet grondwater in dekzand": "NLGWSC0002",
            "Zoet grondwater in kreekgebieden": "NLGWSC0003",
            "Zout grondwater in ondiepe zandlagen": "NLGWSC0004",
            "Grondwater in diepe zandlagen": "NLGWSC0005",
        }

        # Loop over de rijen in het csv bestand. Maak lijsten van de juiste kolommen.
        i = 0
        afwezige_putten = []
        aanwezige_putten = []
        for i, row in enumerate(csv.iter_rows(named=True)):
            if i == 0:
                continue

            grondwaterlichaam = row['Grondwaterlichaam']
            grondwater_code = krw_code.get(grondwaterlichaam)
            NITGCode = row['NITGCode']
            tube = row['FilterNo']

            # Haal de codes en de filter nummers uit de database
            gmw = GroundwaterMonitoringWellStatic.objects.filter(nitg_code = NITGCode).first()

            if gmw is None:
                afwezige_putten.append((NITGCode, tube))
                continue
            
            filter = GroundwaterMonitoringTubeStatic.objects.filter(
                groundwater_monitoring_well_static = gmw, 
                tube_number = tube
            )            

            # if len == 0, write to df or logging that the object was not found
            if len(filter) == 0:
                afwezige_putten.append((NITGCode, tube))
                continue

            # If len gmw > 1, assign krw to all objects
            if filter is not None:
                for f in filter:
                    f.krw_body = grondwater_code  
                    f.save()
                    aanwezige_putten.append((f.groundwater_monitoring_tube_static_id ,NITGCode, tube))                

        logging.info(f"Afwezige putten: {afwezige_putten}")
        logging.info(f'Aangevulde putten: {aanwezige_putten}')
        # Save the object to the database

