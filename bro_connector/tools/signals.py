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
from main.settings.user import get_current_user
from tools.utils import (
    get_monitoring_tube,
    import_from_bro,
    process_csv_file,
    process_zip_bro_file,
    process_zip_file,
)

from .models import BroImport, GLDImport, GMNImport

logger = getLogger("general")


# common separators to test
SEPARATORS = [",", ";", "\t", "|"]


@receiver(pre_save, sender=BroImport)
def validate_and_process_bro_file(sender, instance: BroImport, **kwargs):
    """Validate and process the uploaded BRO shapefile before saving."""
    # Reset the report field to start fresh for each save attempt
    instance.report = """"""
    instance.validated = True
    instance.executed = False

    if not instance.file:
        instance.report += "Geen bestand geupload, daarom is er geen shape of de default shape gebruikt - wanneer in de settings aanwezig.\n"
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
def save_user(sender, instance: GLDImport, **kwargs):
    """Attach the current user to a GLD import when no user is set."""
    if not instance.user:
        user = get_current_user()
        instance.user = user

@receiver(pre_save, sender=GLDImport)
def validate_and_process_file(sender, instance: GLDImport, **kwargs):
    """Validate and process the uploaded GLD CSV or ZIP before saving."""
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
    """Return a decoded string for a CSV sample read from a file."""
    if isinstance(sample, bytes):
        return sample.decode("utf-8", errors="ignore")
    return sample


def determine_separator(sample: bytes | str) -> str:
    """Return the supported separator occurring most often in ``sample``."""
    text = normalize_sample(sample)
    counts = {sep: text.count(sep) for sep in SEPARATORS}
    return max(counts, key=counts.get)


def read_csv_or_zip(file_field) -> pl.DataFrame:
    """Read one CSV or all CSV files from an uploaded file into Polars."""
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
    string: str | datetime.date | datetime.datetime,
) -> datetime.datetime | None:
    """Convert supported date representations to a naive ``datetime``."""
    if isinstance(string, datetime.datetime):
        return string
    if isinstance(string, datetime.date):
        return datetime.datetime.combine(string, datetime.time.min)
    if string is None:
        return None

    string = str(string).strip()

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
        "%d-%m-%Y",  # European format (day-month-year)
    ]

    for fmt in formats:
        try:
            return datetime.datetime.strptime(string, fmt)
        except ValueError:
            continue

    return None


def _validate_gmn_columns(df: pl.DataFrame) -> tuple[list[str], list[str]]:
    """Return the accepted GMN columns and validation messages for ``df``."""
    required_columns = {"measuringPointCode", "gmwBroId", "tubeNumber", "date"}
    optional_columns = {"subgroup"}
    columns = set(df.columns)
    missing_columns = required_columns - columns
    unexpected_columns = columns - required_columns - optional_columns
    messages = []
    if missing_columns or unexpected_columns:
        if missing_columns:
            messages.append(
                f"Missende kolommen: {', '.join(sorted(missing_columns))}.\n"
            )
        if unexpected_columns:
            messages.append(
                f"Onverwachte kolommen: {', '.join(sorted(unexpected_columns))}.\n"
            )
        return [], messages

    columns = ["measuringPointCode", "gmwBroId", "tubeNumber", "date"]
    if "subgroup" in df.columns:
        columns.append("subgroup")
    return columns, messages


def _filter_gmn_rows(
    df: pl.DataFrame, columns: list[str]
) -> tuple[list[dict], list[str], bool]:
    """Validate GMN rows, deduplicate dates, and return rows ready for import."""
    df = df.select(columns)
    valid_rows = []
    seen_dates = set()
    messages = []
    validated = True
    for row_number, row in enumerate(df.iter_rows(named=True), start=2):
        date_value = convert_str_to_datetime(row["date"])
        if date_value is None:
            validated = False
            messages.append(
                f"Rij {row_number} verwijderd: ongeldige datum '{row['date']}'.\n"
            )
            continue

        date_key = date_value.replace(tzinfo=None)
        if date_key in seen_dates:
            messages.append(
                f"Rij {row_number} verwijderd: dubbele datum '{row['date']}' "
                "(eerste voorkomen behouden).\n"
            )
            continue

        if any(
            row[column] is None or str(row[column]).strip() == ""
            for column in columns[:4]
        ):
            validated = False
            messages.append(
                f"Rij {row_number} verwijderd: verplichte waarde ontbreekt.\n"
            )
            continue

        seen_dates.add(date_key)
        row["date"] = date_value
        row["_source_row"] = row_number
        valid_rows.append(row)
    return valid_rows, messages, validated


def _create_gmn_subgroups(instance: GMNImport, rows: list[dict]) -> None:
    """Create or update non-empty subgroups found in validated GMN rows."""
    subgroup_names = {
        row["subgroup"]
        for row in rows
        if row.get("subgroup") is not None and str(row["subgroup"]).strip()
    }
    for subgroup in subgroup_names:
        Subgroup.objects.update_or_create(
            gmn=instance.monitoring_network,
            name=subgroup,
            defaults={"code": subgroup},
        )


def _import_gmn_rows(instance: GMNImport, rows: list[dict]) -> bool:
    """Import validated GMN rows and return whether every row was imported."""
    executed = True
    for row in rows:
        row_number = row["_source_row"]
        monitoring_tube = get_monitoring_tube(
            row["gmwBroId"], row["tubeNumber"]
        )
        if not monitoring_tube:
            instance.validated = False
            instance.report += (
                f"Rij {row_number} verwijderd: filterbuis niet gevonden voor "
                f"{row['gmwBroId']}-{row['tubeNumber']}.\n"
            )
            executed = False
            continue

        date_value = convert_str_to_datetime(row["date"])
        if date_value is None:
            instance.validated = False
            instance.report += f"Rij {row_number} verwijderd: datum kon niet worden verwerkt.\n"
            executed = False
            continue

        measuring_point = MeasuringPoint.objects.update_or_create(
            gmn=instance.monitoring_network,
            groundwater_monitoring_tube=monitoring_tube,
            code=row["measuringPointCode"],
            defaults={"added_to_gmn_date": date_value.date()},
        )[0]

        if "subgroup" in row:
            raw_subgroup = row["subgroup"]
            if raw_subgroup is not None and str(raw_subgroup).strip() != "":
                subgroup = Subgroup.objects.get(
                    gmn=instance.monitoring_network, code=raw_subgroup
                )
                measuring_point.subgroup.add(subgroup)
    return executed


@receiver(pre_save, sender=GMNImport)
def pre_save_gmn_import(sender, instance: GMNImport, **kwargs):
    """Validate and import a GMN CSV/ZIP exactly once before saving."""
    if instance.executed:
        return

    instance.report = ""
    instance.validated = True

    if not instance.file:
        instance.validated = False
        instance.report += "Geen bestand geupload.\n"
        return

    try:
        df = read_csv_or_zip(instance.file)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        instance.validated = False
        instance.report += f"Bestand kon niet worden gelezen: {error}\n"
        return

    columns, column_messages = _validate_gmn_columns(df)
    if column_messages:
        instance.validated = False
        instance.report += "".join(column_messages)
    if not columns:
        return

    rows, row_messages, rows_validated = _filter_gmn_rows(df, columns)
    instance.validated = instance.validated and rows_validated
    instance.report += "".join(row_messages)
    _create_gmn_subgroups(instance, rows)
    instance.executed = _import_gmn_rows(instance, rows)

