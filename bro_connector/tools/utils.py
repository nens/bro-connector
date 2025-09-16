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
import logging
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
from django.db import transaction

logger = logging.getLogger(__name__)


def detect_csv_separator(file):
    """
    Detect the separator/delimiter used in a CSV file.

    Args:
        filename (str): Path to the CSV file

    Returns:
        str: Detected separator character or , if not detected
    """
    import csv

    # Common CSV delimiters to check
    possible_delimiters = [",", ";", "\t", "|", ":"]

    try:
        # Read the first few lines
        sample = "".join([file.readline() for _ in range(5)])

        if not sample:
            return ","

        # Count occurrences of each delimiter
        delimiter_counts = {
            delimiter: sample.count(delimiter) for delimiter in possible_delimiters
        }

        # Get the delimiter with the highest count and consistent presence
        max_delimiter = max(delimiter_counts.items(), key=lambda x: x[1])

        # If the delimiter appears consistently across lines, it's likely the separator
        if max_delimiter[1] > 0:
            # Validate by trying to parse with the detected delimiter
            file.seek(0)  # Reset file pointer
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=possible_delimiters)
                if dialect.delimiter in possible_delimiters:
                    return dialect.delimiter
                else:
                    return max_delimiter[0]
            except csv.Error:
                # If sniffer fails, return the most frequent delimiter
                return max_delimiter[0]

            return ","

    except Exception as e:
        print(f"Error reading file: {e}")
        return ","
    
def format_message(handler: str, type: str, kvk: int, shp: str, count: int, imported: int) -> dict:
    if type in ["gar", "gmn", "frd"]:
        return {"message": f"BRO type {type} is nog niet geimplementeerd.", "level": "WARNING"}
    elif count == 0:
        if handler == "KvK":
            return {"message": f"Geen {type}-objecten gevonden voor kvk {kvk}.", "level": "ERROR"}
        if handler == "Shape":
            if kvk:
                return {"message": f"Geen {type}-objecten gevonden voor kvk {kvk} binnen {shp}.", "level": "ERROR"}
            else:
                return {"message": f"Geen {type}-objecten gevonden binnen {shp}.", "level": "ERROR"}
    elif count == imported:
        if handler == "KvK":
            return {
                "message": f"Alle {type}-objecten geimporteerd voor kvk {kvk}. ({imported})",
                "level": "SUCCESS",
            }
        if handler == "Shape":
            if kvk:
                return {
                    "message": f"Alle {type}-objecten geimporteerd voor kvk {kvk} binnen {shp}. ({imported})",
                    "level": "SUCCESS",
                }
            else:
                return {
                    "message": f"Alle {type}-objecten geimporteerd binnen {shp}. ({imported})",
                    "level": "SUCCESS",
                }

    elif imported == 0:
        if handler == "KvK":
            return {
                "message": f"Geen {type}-objecten geimporteerd voor kvk {kvk}. {count} objecten gevonden.",
                "level": "ERROR",
            }
        if handler == "Shape":
            if kvk:
                return {
                    "message": f"Geen {type}-objecten geimporteerd voor kvk {kvk} binnen {shp}. {count} objecten gevonden.",
                    "level": "ERROR",
                }
            else:
                return {
                    "message": f"Geen {type}-objecten geimporteerd binnen {shp}. {count} objecten gevonden.",
                    "level": "ERROR",
                }
    elif count > imported:
        if handler == "KvK":
            return {
                "message": f"{imported} van de {count} {type}-objecten geimporeerd voor kvk {kvk}.",
                "level": "WARNING",
            }
        if handler == "Shape":
            if kvk:
                return {
                    "message": f"{imported} van de {count} {type}-objecten geimporeerd voor kvk {kvk} binnen {shp}.",
                    "level": "WARNING",
                }
            else:
                return {
                    "message": f"{imported} van de {count} {type}-objecten geimporeerd binnen {shp}.",
                    "level": "WARNING",
                }
            
def has_necessary_helper_files(filenames):
    """
    Check if the list of filenames contains exactly one file
    for each of the required shapefile extensions.
    """
    required_extensions = [".dbf", ".prj", ".shx"]

    # Count occurrences of each required extension
    counts = {ext: 0 for ext in required_extensions}
    for f in filenames:
        ext = f.lower()[-4:]
        if ext in counts:
            counts[ext] += 1

    # Check conditions
    all_present = all(counts[ext] == 1 for ext in required_extensions)
    return all_present, counts

def process_zip_bro_file(instance: BroImport):
    # Read ZIP file
    zip_buffer = BytesIO(instance.file.read())
    try:
        with zipfile.ZipFile(zip_buffer) as zip_file:
            # Get all files inside the ZIP
            all_files = zip_file.namelist()

            # Filter out CSV files
            shp_files = [f for f in all_files if f.endswith(".shp")]
            not_shp_files = [f for f in all_files if not f.endswith(".shp")]

            if not shp_files:
                instance.report += "Geen SHP-bestanden gevonden in het ZIP-bestand.\n"
                instance.validated = False

            if len(shp_files) > 1:
                instance.report += "Meer dan 1 SHP-bestand gevonden in het ZIP-bestand. Maximaal 1 toegestaan.\n"
                instance.validated = False

            if not has_necessary_helper_files(not_shp_files):
                instance.report += "Geen of meerdere SHX, DBF, or PRJ-bestanden gevonden in het ZIP-bestand. 1 van elk benodigd/toegestaan.\n"
                instance.validated = False

            # timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
            basename = Path(shp_files[0]).stem
            output_folder = (
                Path(__file__).resolve().parent.parent.parent / "data" / "shapefile" / f"{basename}"#_{timestamp}"
            )
            output_folder.mkdir(parents=True, exist_ok=True)
            shp_filename = shp_files[0]
            extensions = [".shp", ".dbf", ".prj", ".shx"]
            for ext in extensions:
                filename = [f for f in all_files if f.endswith(ext)][0]
                file_path = output_folder / Path(filename).name
                try:
                    with zip_file.open(filename) as src, open(file_path, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                except PermissionError as e:
                    logger.info("Shape files and helper files are in use and locked. Unable to overwrite with new shape file.")
                    logger.exception(e)

            ## start a new loop and validate the shp file and then process it
            POLYGON_SHAPEFILE = output_folder / Path(shp_filename).name
            gdf = validate_shp(POLYGON_SHAPEFILE, instance)
            if gdf is not None:
                import_info = {}
                if instance.bro_type.lower() == "gmw":
                    import_info = retrieve_historic_gmw.run(
                        kvk_number=instance.kvk_number, 
                        handler=instance.handler,
                        shp_file=POLYGON_SHAPEFILE,
                        delete=instance.delete_outside,
                    )
                if instance.bro_type.lower() == "gld":
                    import_info = retrieve_historic_gld.run(
                        kvk_number=instance.kvk_number, 
                        handler=instance.handler,
                        shp_file=POLYGON_SHAPEFILE,
                        delete=instance.delete_outside,
                    )
            
                report = format_message(
                    handler=instance.handler, 
                    type=instance.bro_type, 
                    kvk=instance.kvk_number, 
                    shp=shp_filename,
                    count=import_info.get("ids_found"), 
                    imported=import_info.get("imported"),
                )
                instance.report += report.get("message") + "\n"
                instance.executed = True

    except zipfile.BadZipFile:
        instance.report += "Ongeldig ZIP-bestand.\n"
        instance.validated = False
    finally:
        zip_buffer.close()

def validate_shp(file_path, instance: BroImport):
    """
    Validate a shapefile using GeoPandas.
    """

    try:
        # Try loading shapefile with geopandas
        gdf = gpd.read_file(file_path)
        filename = Path(file_path).stem

        # Check if shapefile has rows
        if gdf.empty:
            instance.validated = False
            instance.report += f"{filename} bevat geen geometrieën.\n"
            return None

        # Validate geometries
        invalid_geoms = gdf[~gdf.geometry.is_valid]
        if not invalid_geoms.empty:
            instance.validated = False
            instance.report += (
                f"{filename} bevat {len(invalid_geoms)} ongeldige geometrieën.\n"
            )
            return None

        # Optional: check if CRS is defined
        if gdf.crs is None:
            instance.report += f"Waarschuwing: {filename} heeft geen CRS (coördinaatreferentiesysteem).\n"
            return None

        return gdf

    except Exception as e:
        instance.validated = False
        instance.report += f"{filename} is ongeldig of corrupt: {str(e)}\n"
        return None  
    


def process_zip_file(instance: GLDImport):
    # Read ZIP file
    zip_buffer = BytesIO(instance.file.read())
    try:
        with zipfile.ZipFile(zip_buffer) as zip_file:
            # Get all files inside the ZIP
            all_files = zip_file.namelist()

            # Filter out CSV files
            csv_files = [f for f in all_files if f.endswith(".csv")]

            # Identify non-CSV files
            non_csv_files = [f for f in all_files if not f.endswith(".csv")]

            if not csv_files:
                instance.report += "Geen CSV-bestanden gevonden in het ZIP-bestand.\n"
                instance.validated = False

            if non_csv_files:
                instance.report += (
                    f"Niet-CSV bestanden in ZIP: {', '.join(non_csv_files)}\n"
                )

            for filename in csv_files:
                with zip_file.open(filename) as csv_file:
                    validate_csv(csv_file, filename, instance)

    except zipfile.BadZipFile:
        instance.report += "Ongeldig ZIP-bestand.\n"
        instance.validated = False
    finally:
        zip_buffer.close()



def process_csv_file(instance: GLDImport):
    # Validate CSV file
    reader = validate_csv(instance.file, instance.file.name, instance)
    time_col = "time" if "time" in reader.columns else "tijd"
    value_col = "value" if "value" in reader.columns else "waarde"
    gld = GroundwaterLevelDossier.objects.filter(
        groundwater_monitoring_tube=instance.groundwater_monitoring_tube,
        quality_regime = instance.quality_regime
    ).first()
    if not gld:
        gld = GroundwaterLevelDossier.objects.update_or_create(
            gld_bro_id=instance.gld_bro_id,
            groundwater_monitoring_tube = instance.groundwater_monitoring_tube,
            quality_regime = instance.quality_regime,
        )[0]
        instance.report += f"GroundwaterLevelDossier aangemaakt: {gld}.\n"
    
    if instance.validated:
        # Create ObservationProces
        Obs_Pro = ObservationProcess.objects.update_or_create(
            process_reference=instance.process_reference,
            measurement_instrument_type=instance.measurement_instrument_type,
            air_pressure_compensation_type=instance.air_pressure_compensation_type,
            process_type=instance.process_type,
            evaluation_procedure=instance.evaluation_procedure,
        )[0]
        # Create ObservationMetadata
        Obs_Meta = ObservationMetadata.objects.update_or_create(
            observation_type=instance.observation_type,
            status=instance.status,
            responsible_party=instance.responsible_party,
        )[0]

        first_datetime = reader[time_col].min()
        last_datetime = reader[time_col].max()

        # Create Observation
        Obs = Observation.objects.update_or_create(
            groundwater_level_dossier=gld,
            observation_metadata=Obs_Meta,
            observation_process=Obs_Pro,
            observation_starttime=first_datetime,
            observation_endtime=last_datetime,
        )[0]

        # itter over file
        times = []
        mms = []
        mtvps = []
        duplicates = False
        for index, row in reader.iterrows():
            value = row[value_col]
            time = row[time_col]
            if time in times: 
                if not duplicates:
                    instance.report += "Duplicaten gevonden in de tijd waardes. Alleen de eerste voorgekomen waardes gebruikt.\n\n"
                duplicates = True
                continue
            else:
                times.append(time)

            # create basic MeasurementPointMetadata
            mp_meta = MeasurementPointMetadata(value_limit=None)

            # Add the present fields to the metadata if they are given in the CSV
            st_quality_control_tvp = row.get("status_quality_control", None)
            if st_quality_control_tvp:
                mp_meta.status_quality_control = st_quality_control_tvp

            censor_reason_tvp = row.get("censor_reason", None)
            if censor_reason_tvp:
                mp_meta.censor_reason = censor_reason_tvp

            censor_limit_tvp = row.get("censor_limit", None)
            if censor_limit_tvp:
                if not pd.isna(censor_limit_tvp):
                    mp_meta.value_limit = censor_limit_tvp

            # Save the metadata after all fields are set
            mms.append(mp_meta)

            # create time-value pair
            mtvp = MeasurementTvp(
                observation=Obs,
                measurement_time=time,
                field_value=value,
                field_value_unit=instance.field_value_unit,
                measurement_point_metadata=mp_meta,
            )

            mtvps.append(mtvp)

        with transaction.atomic():
            try:
                MeasurementPointMetadata.objects.bulk_create(
                    mms,
                    update_conflicts=False,
                    batch_size=5000,
                )
                MeasurementTvp.objects.bulk_create(
                    mtvps,
                    update_conflicts=False,
                    ## IMPORTANT: Temporarily turned off the unique constraint of mtvps due to complications with Zeeland DB. 
                    # update_conflicts=True, 
                    # update_fields=[
                    #     "field_value", 
                    #     "field_value_unit", 
                    #     "calculated_value", 
                    #     "measurement_point_metadata"
                    # ],
                    # unique_fields=[
                    #     "observation", 
                    #     "measurement_time"
                    # ],
                    batch_size=5000,
                )
            except Exception as e:
                instance.report += f"Bulk updating/creating failed for observation: {Obs}"
                logger.info(f"Bulk updating/creating failed for observation: {Obs}")
                logger.exception(e)
                instance.executed = False
                return

        if instance.groundwater_monitoring_tube:
            glds = GroundwaterLevelDossier.objects.filter(
                groundwater_monitoring_tube=instance.groundwater_monitoring_tube,
                gld_bro_id=instance.gld_bro_id
            )
            for gld in glds:
                if gld.first_measurement:
                    gld.research_start_date = gld.first_measurement.date()
                else:
                    gld.research_start_date = datetime.now().date()
                if gld.last_measurement:
                    gld.research_last_date = gld.last_measurement.date()
                else:
                    gld.research_last_date = datetime.now().date()
                gld.research_last_correction = datetime.now().date()
                gld.save()

        instance.executed = True


def validate_csv(file, filename: str, instance: GLDImport):
    time_col = None
    seperator = ","  # detect_csv_separator(file)
    reader = pd.read_csv(file, header=0, index_col=False, sep=seperator)
    required_columns = ["time", "value"]
    missing_columns = [col for col in required_columns if col not in reader.columns]
    if missing_columns:
        instance.validated = False
        instance.report += f"Missende kolommen: {', '.join(missing_columns)}\n\n"

    # Check if CSV has any rows
    if reader.empty:
        instance.validated = False
        instance.report += f"{filename} bevat geen gegevens.\n"
        return reader

    # Validate the first column format for datetimes
    time_col = reader.columns[0]
    try:
        # print(reader[time_col])
        reader[time_col] = pd.to_datetime(
            reader[time_col], errors="raise", utc=True
        )  # This will raise an error if invalid format
        # Convert to Europe/Amsterdam
        reader[time_col] = reader[time_col].dt.tz_convert("Europe/Amsterdam")
    except Exception as e:
        instance.validated = False
        instance.report += (
            f"Eerste kolom moet de tijd bevatten van {filename}: {str(e)}\n\n"
        )

    # Validate 'value' column format (numeric values)
    if "value" in reader.columns:
        if (
            not pd.to_numeric(reader["value"], errors="coerce").notnull().all()
        ):  # Check if all values are numeric
            instance.validated = False
            instance.report += f"Fout in 'value' kolom van {filename}: Bevat niet-numerieke waarden.\n\n"

    # validate the status_quality_control column if given in csv
    if "status_quality_control" in reader.columns:
        STATUSQUALITYCONTROL_LIST = [status[0] for status in STATUSQUALITYCONTROL]
        if not reader["status_quality_control"].isin(STATUSQUALITYCONTROL_LIST).all():
            instance.validated = False
            instance.report += "Fout in 'status_quality_control' kolom: Ongeldige waarden gevonden.\n\n"
    else:
        instance.report += "De kolom 'status_quality_control' kan worden toegevoegd  om te duiden wat de kwaliteit van de meting is.\n\n"

    # validate the censor_reason column if given in csv
    if "censor_reason" in reader.columns:
        CENSORREASON_LIST = [status[0] for status in CENSORREASON] + [np.nan]
        # Validate that all values in the column are in the allowed set
        if not reader["censor_reason"].isin(CENSORREASON_LIST).all():
            instance.validated = False
            instance.report += (
                "Fout in 'censor_reason': Ongeldige waarden gevonden.\n\n"
            )
    else:
        instance.report += "De kolom 'censor_reason' kan worden toegevoegd om de censuur reden aan te geven.\n\n"

    # validate the censor_reason column if given in csv
    if "censor_limit" in reader.columns:
        if not (
            pd.api.types.is_float_dtype(reader["censor_limit"])
            | pd.api.types.is_integer_dtype(reader["censor_limit"])
        ):
            instance.validated = False
            instance.report += (
                "Fout in 'censor_limit' kolom: waarden zijn niet int of float.\n\n"
            )
    else:
        instance.report += "De kolom 'censor_limit' kan worden toegevoegd om aan te geven welke limiet waarde is gebruikt\n\n"

    return reader


def get_monitoring_tube(
    bro_id: str, buis_nummer: int
) -> GroundwaterMonitoringTubeStatic | None:
    try:
        well = GroundwaterMonitoringWellStatic.objects.get(bro_id=bro_id)
    except GroundwaterMonitoringWellStatic.DoesNotExist:
        return None

    try:
        return GroundwaterMonitoringTubeStatic.objects.get(
            groundwater_monitoring_well_static=well, tube_number=buis_nummer
        )
    except GroundwaterMonitoringTubeStatic.DoesNotExist:
        return None

