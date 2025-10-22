import zipfile
from datetime import datetime
from logging import getLogger

import polars as pl
from django.db.models.signals import (
    pre_save,
)
from django.dispatch import receiver
from gmn.models import (
    GroundwaterMonitoringNet,
    MeasuringPoint,
    Subgroup,
)
from tools.utils import (
    get_monitoring_tube,
    process_csv_file,
    process_zip_bro_file,
    process_zip_file,
)

from .models import BroImport, GLDImport, GMNImport

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
        process_zip_bro_file(
            instance
        )  # Process the ZIP file and update 'instance' as needed
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
    if not instance.groundwater_monitoring_tube:
        instance.validated = False
        instance.report += "Geen filterbuis geselecteerd om de GLD aan te koppelen.\n"
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


def read_csv_or_zip(file_field) -> pl.DataFrame:
    filename = file_field.name.lower()
    if filename.endswith(".zip"):
        with zipfile.ZipFile(file_field, "r") as z:
            dfs = []
            for name in z.namelist():
                if name.endswith(".csv"):
                    with z.open(name) as f:
                        dfs.append(pl.read_csv(f, has_header=True, separator=","))
            if not dfs:
                raise ValueError("No CSV files found in the ZIP archive.")
            return pl.concat(dfs)
    elif filename.endswith(".csv"):
        return pl.read_csv(file_field, has_header=True, separator=",")
    else:
        raise ValueError("Unsupported file type. Must be CSV or ZIP.")


@receiver(pre_save, sender=GMNImport)
def pre_save_gmn_import(sender, instance: GMNImport, **kwargs):
    if instance.executed:
        return

    gmn = GroundwaterMonitoringNet.objects.create(
        name=instance.name,
        province_name=instance.province_name,
        bro_domain=instance.bro_domain,
        regio=instance.regio,
        delivery_context=instance.delivery_context,
        monitoring_purpose=instance.monitoring_purpose,
        start_date_monitoring=instance.start_date_monitoring,
        groundwater_aspect=instance.groundwater_aspect,
        quality_regime=instance.quality_regime,
    )

    df = read_csv_or_zip(instance.file)

    if len(df.columns) < 4:
        instance.validated = False
        instance.report += "Missende kolommen. Gebruik: meetpuntcode, gmwBroId, buisNummer, datum, subgroep*. Subgroep is niet verplicht.\n"

    # Create subgroups if column exists and has values
    if "subgroep" in df.columns:
        subgroepen = True
        subgroups_series = df.select("subgroep").to_series()
        # Filter out nulls
        non_null_subgroups = subgroups_series.filter(subgroups_series.is_not_null())
        unique_subgroups = non_null_subgroups.unique()
        subgroups = unique_subgroups.to_list()

        for subgroup in subgroups:
            Subgroup.objects.create(
                gmn=gmn,
                name=subgroup,
                code=subgroup,
            )

    executed = True
    for row in df.iter_rows():
        monitoring_tube = get_monitoring_tube(row[1], row[2])
        if not monitoring_tube:
            instance.report += f"Could not find tube for: {row[1]}-{row[2]}.\n"
            executed = False
            continue

        measuring_point = MeasuringPoint.objects.create(
            gmn=gmn,
            groundwater_monitoring_tube=monitoring_tube,
            code=row[0],
            added_to_gmn_date=datetime.strptime(row[3], "%Y-%m-%d").date(),
        )

        if subgroepen:
            raw_subgroup = row[4]
            if raw_subgroup is not None and str(raw_subgroup).strip() != "":
                subgroup = Subgroup.objects.get(gmn=gmn, code=raw_subgroup)
                measuring_point.subgroup.add(subgroup)

    instance.executed = executed
