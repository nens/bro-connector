import datetime
import zipfile
from logging import getLogger

import polars as pl
from django.db.models.signals import (
    pre_save,
)
from django.dispatch import receiver
from gmn.models import (
    MeasuringPoint,
    Subgroup,
)
from tools.utils import (
    get_monitoring_tube,
    process_csv_file,
    process_zip_bro_file,
    process_zip_file,
    import_from_bro,
)

from .models import BroImport, GLDImport, GMNImport

logger = getLogger("general")


# common separators to test
SEPARATORS = [",", ";", "\t", "|"]


@receiver(pre_save, sender=BroImport)
def validate_and_process_bro_file(sender, instance: BroImport, **kwargs):
    # Reset the report field to start fresh for each save attempt
    instance.report = """"""
    instance.validated = True
    instance.executed = False

    if not instance.file:
        instance.report += (
            "Geen bestand geupload, daarom is er geen shape of de default shape gebruikt - wanneer in de settings aanwezig.\n"
        )
        import_from_bro(instance)
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


def normalize_sample(sample: bytes | str) -> str:
    """Ensure sample is always a string."""
    if isinstance(sample, bytes):
        return sample.decode("utf-8", errors="ignore")
    return sample


def determine_separator(sample: bytes | str) -> str:
    """Guess the most likely separator based on frequency."""
    text = normalize_sample(sample)
    counts = {sep: text.count(sep) for sep in SEPARATORS}
    return max(counts, key=counts.get)


def read_csv_or_zip(file_field) -> pl.DataFrame:
    filename = file_field.name.lower()

    if filename.endswith(".zip"):
        dfs = []
        with zipfile.ZipFile(file_field, "r") as z:
            for name in z.namelist():
                if name.endswith(".csv"):
                    with z.open(name) as f:
                        sample = f.read(1024)
                        separator = determine_separator(sample)
                        f.seek(0)
                        dfs.append(pl.read_csv(f, has_header=True, separator=separator))
        if not dfs:
            raise ValueError("No CSV files found in the ZIP archive.")
        return pl.concat(dfs)

    elif filename.endswith(".csv"):
        sample = file_field.read(1024)
        separator = determine_separator(sample)
        file_field.seek(0)
        return pl.read_csv(file_field, has_header=True, separator=separator)

    else:
        raise ValueError("Unsupported file type. Must be CSV or ZIP.")


def convert_str_to_datetime(
    string: str | datetime.datetime,
) -> datetime.datetime | None:
    if isinstance(string, datetime.datetime):
        return string

    # List of supported formats
    formats = [
        "%Y-%m-%d",  # Date only
        "%Y-%m-%d %H:%M:%S",  # Date + time (space separator)
        "%Y-%m-%dT%H:%M:%S",  # Date + time (ISO T separator)
        "%Y-%m-%d %H:%M",  # Date + time without seconds
        "%Y-%m-%dT%H:%M",  # ISO without seconds
        "%Y-%m-%d %H:%M:%S.%f",  # Date + time with microseconds
        "%Y-%m-%dT%H:%M:%S.%f",  # ISO with microseconds
        "%d/%m/%Y",  # European format (day/month/year)
        "%d-%m-%Y", # European format (day-month-year)
    ]

    for fmt in formats:
        try:
            return datetime.datetime.strptime(string, fmt)
        except ValueError:
            continue

    return None


@receiver(pre_save, sender=GMNImport)
def pre_save_gmn_import(sender, instance: GMNImport, **kwargs):
    if instance.executed:
        return

    df = read_csv_or_zip(instance.file)

    if len(df.columns) < 4:
        instance.validated = False
        instance.report += "Missende kolommen. Gebruik: meetpuntcode, gmwBroId, buisNummer, datum, subgroep*. Subgroep is niet verplicht.\n"

    columns = ["measuringPointCode", "gmwBroId", "tubeNumber", "date"]
    if len(df.columns) > 4:
        columns.append("subgroup")

    df.columns = columns

    # Create subgroups if column exists and has values
    if "subgroup" in df.columns:
        subgroups_series = df.select("subgroup").to_series()
        # Filter out nulls
        non_null_subgroups = subgroups_series.filter(subgroups_series.is_not_null())
        unique_subgroups = non_null_subgroups.unique()
        subgroups = unique_subgroups.to_list()

        for subgroup in subgroups:
            Subgroup.objects.update_or_create(
                gmn=instance.monitoring_network,
                name=subgroup,
                defaults={"code": subgroup},
            )

    executed = True
    for row in df.iter_rows():
        monitoring_tube = get_monitoring_tube(row[1], row[2])
        if not monitoring_tube:
            instance.report += f"Could not find tube for: {row[1]}-{row[2]}.\n"
            executed = False
            continue

        measuring_point = MeasuringPoint.objects.update_or_create(
            gmn=instance.monitoring_network,
            groundwater_monitoring_tube=monitoring_tube,
            code=row[0],
            defaults={"added_to_gmn_date": convert_str_to_datetime(row[3]).date()}
            ## Does this have to be the oldest date if a the measuring_point already exists? Or should it be overwritten?
        )[0]

        if len(row) > 4:
            raw_subgroup = row[4]
            if raw_subgroup is not None and str(raw_subgroup).strip() != "":
                subgroup = Subgroup.objects.get(
                    gmn=instance.monitoring_network, code=raw_subgroup
                )
                measuring_point.subgroup.add(subgroup)

    instance.executed = executed
