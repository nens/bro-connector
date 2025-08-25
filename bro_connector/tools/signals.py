from django.db.models.signals import (
    pre_save,
)
import polars as pl
import numpy as np
from .models import GLDImport, GMNImport, BroImport
from django.dispatch import receiver
from io import BytesIO
import zipfile
import pandas as pd
import geopandas as gpd
import tempfile
import os
from pathlib import Path
from datetime import datetime
import shutil

from main.utils.bbox_extractor import BBOX_EXTRACTOR
from gmn.models import (
    GroundwaterMonitoringNet,
    Subgroup,
    MeasuringPoint,
)
from logging import getLogger
from gmw.models import GroundwaterMonitoringTubeStatic, GroundwaterMonitoringWellStatic
from gld.models import (
    Observation,
    MeasurementTvp,
    MeasurementPointMetadata,
    ObservationProcess,
    ObservationMetadata,
    GroundwaterLevelDossier,
)
from gld.choices import STATUSQUALITYCONTROL, CENSORREASON
from main.management.tasks import (
    retrieve_historic_gmw,
    retrieve_historic_frd,
    retrieve_historic_gld,
    retrieve_historic_gmn,
)
from tools.utils import (
    process_zip_bro_file,
    process_zip_file,
    process_csv_file,
    get_monitoring_tube,
)

logger = getLogger("general")

@receiver(pre_save, sender=BroImport)
def validate_and_process_bro_file(sender, instance: BroImport, **kwargs):
    # Reset the report field to start fresh for each save attempt
    instance.report = """"""
    instance.validated = True
    instance.executed = False

    if not instance.file:
        instance.validated = False
        instance.report += (
            "Geen bestand geupload. Alleen ZIP- of CSV-bestanden zijn toegestaan.\n"
        )
    elif instance.file.name.endswith(".zip"):
        process_zip_bro_file(instance)  # Process the ZIP file and update 'instance' as needed
    else:
        instance.validated = False
        instance.report += (
            "Ongeldig bestandstype. Alleen ZIP- of CSV-bestanden zijn toegestaan.\n"
        )  

@receiver(pre_save, sender=GLDImport)
def validate_and_process_file(sender, instance: GLDImport, **kwargs):
    # Reset the report field to start fresh for each save attempt
    instance.report = """"""
    instance.validated = True

    if not instance.file:
        instance.validated = False
        instance.report += (
            "Geen bestand geupload. Alleen ZIP- of CSV-bestanden zijn toegestaan.\n"
        )
    elif instance.file.name.endswith(".zip"):
        process_zip_file(
            instance
        )  # Process the ZIP file and update 'instance' as needed
    elif instance.file.name.endswith(".csv"):
        process_csv_file(
            instance
        )  # Process the CSV file and update 'instance' as needed
    else:
        instance.validated = False
        instance.report += (
            "Ongeldig bestandstype. Alleen ZIP- of CSV-bestanden zijn toegestaan.\n"
        )

@receiver(pre_save, sender=GMNImport)
def pre_save_gmn_import(sender, instance: GMNImport, **kwargs):
    if instance.executed:
        return

    gmn = GroundwaterMonitoringNet.objects.create(
        name=instance.name,
        delivery_context=instance.delivery_context,
        monitoring_purpose=instance.monitoring_purpose,
        start_date_monitoring=instance.start_date_monitoring,
        groundwater_aspect=instance.groundwater_aspect,
        quality_regime=instance.quality_regime,
    )

    subgroepen = False
    df = pl.read_csv(instance.file, has_header=True, separator=",")
    if len(df.columns) < 4:
        instance.validated = False
        instance.report += "Missende kolommen. Gebruik: meetpuntcode, gmwBroId, buisNummer, datum, subgroep*. Subgroep is niet verplicht.\n"

    if "subgroep" in df.columns:
        subgroepen = True
        subgroups = df.select("subgroep").to_series(0).unique().to_list()
        for subgroup in subgroups:
            Subgroup.objects.create(
                gmn=gmn,
                name=subgroup,
                code=subgroup,
            )

    # Create MeasuringPoints
    executed = True
    for row in df.iter_rows():
        monitoring_tube = get_monitoring_tube(row[1], row[2])
        if not monitoring_tube:
            instance.report += f"Could not find tube for: {row[1]}-{row[2]}.\n"
            executed = False
            continue

        subgroup = None
        if subgroepen:
            subgroup = Subgroup.objects.get(gmn=gmn, code=row[4])

        MeasuringPoint.objects.create(
            gmn=gmn,
            groundwater_monitoring_tube=monitoring_tube,
            code=row[0],
            added_to_gmn_date=row[3],
            subgroup=subgroup,
        )

    instance.executed = executed
