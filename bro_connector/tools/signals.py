from django.db.models.signals import (
    pre_save,
)
from datetime import datetime
import polars as pl
from .models import GLDImport, GMNImport
from django.dispatch import receiver
from io import BytesIO
import zipfile
import pandas as pd
from gmn.models import (
    GroundwaterMonitoringNet,
    Subgroup,
    MeasuringPoint,
)
from gmw.models import GroundwaterMonitoringTubeStatic, GroundwaterMonitoringWellStatic
from gld.models import (
    Observation,
    MeasurementTvp,
    MeasurementPointMetadata,
    ObservationProcess,
    ObservationMetadata,
)
from gld.choices import STATUSQUALITYCONTROL, CENSORREASON, INTERPOLATIONTYPE


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

    # Log the validated state
    # instance.report += f"instance.validated = {instance.validated}\n"


# @receiver(post_save, sender=GLDImport)
# def show_message(sender, instance: GLDImport, **kwargs):
#     if not instance.validated:
#         raise ValidationError("importeren niet gelukt, check logging")


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
    (
        reader,
        time_col,
        status_quality_control_col,
        censor_reason_col,
        interpolation_code_col,
    ) = validate_csv(instance.file, instance.file.name, instance)

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
            date_stamp=datetime.today(),  # creatiedatum van de metadata over de observatie
            observation_type=instance.observation_type,
            status=instance.status,
            responsible_party=instance.responsible_party,
        )[0]

        first_datetime = reader[time_col].min()
        last_datetime = reader[time_col].max()

        # Create Observation
        Obs = Observation.objects.update_or_create(
            observation_metadata=Obs_Meta,
            observation_process=Obs_Pro,
            observation_starttime=first_datetime,
            observation_endtime=last_datetime,
        )[0]

        # itter over file
        for index, row in reader.iterrows():
            value = row["values"]
            time = row[time_col]

            # create basic MeasurementPointMetadata
            mp_meta = MeasurementPointMetadata.objects.create()

            # Add the present fields to the metadata if they are given in the CSV
            if status_quality_control_col:
                st_quality_control_tvp = row.get(status_quality_control_col)
                if st_quality_control_tvp:
                    mp_meta.status_quality_control = st_quality_control_tvp

            if censor_reason_col:
                censor_reason_tvp = row.get(censor_reason_col)
                if censor_reason_tvp:
                    mp_meta.censor_reason = censor_reason_tvp

            if interpolation_code_col:
                interpolation_code_tvp = row.get(interpolation_code_col)
                if interpolation_code_tvp:
                    mp_meta.interpolation_code = interpolation_code_tvp

            # Save the metadata after all fields are set
            mp_meta.save()

            # create time-value pair
            tvp = MeasurementTvp.objects.update_or_create(
                observation=Obs,
                measurement_time=time,
                field_value=value,
                field_value_unit=instance.field_value_unit,
                measurement_point_metadata=mp_meta,
            )

        instance.executed = True
        instance.name = (
            f"({Obs_Meta.date_stamp.strftime('%Y-%m-%d')}) - ({instance.file.name})"
        )
    else:
        instance.name = (
            f"({datetime.today().strftime('%Y-%m-%d')}) - ({instance.file.name})"
        )


def validate_csv(file, filename: str, instance: GLDImport):
    try:
        time_col = None
        status_quality_control_col = None
        censor_reason_col = None
        interpolation_code_col = None
        reader = pd.read_csv(file, header=0, index_col=False)
        required_columns = ["values"]
        missing_columns = [col for col in required_columns if col not in reader.columns]
        if missing_columns:
            instance.validated = False
            instance.report += f"Missende verplichte kolommen in {filename}: {', '.join(missing_columns)}\n"

        # Check if CSV has any rows
        if reader.empty:
            instance.validated = False
            instance.report += f"{filename} bevat geen gegevens.\n"

        # Validate the first column format for datetimes
        else:
            time_col = reader.columns[0]

            try:
                reader[time_col] = pd.to_datetime(
                    reader[time_col], format="%Y-%m-%d %H:%M:%S", errors="raise"
                )  # This will raise an error if invalid format
            except Exception as e:
                instance.validated = False
                instance.report += (
                    f"Eerste kolom moet de tijd bevatten van {filename}: {str(e)}\n"
                )

        # Validate 'values' column format (numeric values)
        if "values" in reader.columns:
            if (
                not pd.to_numeric(reader["values"], errors="coerce").notnull().all()
            ):  # Check if all values are numeric
                instance.validated = False
                instance.report += f"Fout in 'values' kolom van {filename}: Bevat niet-numerieke waarden.\n"

        # validate the status_quality_control column if given in csv
        if "status_quality_control" in reader.columns:
            STATUSQUALITYCONTROL_LIST = [status[0] for status in STATUSQUALITYCONTROL]
            # Validate that all values in the column are in the allowed set
            status_quality_control_col = "status_quality_control"
            if (
                not reader["status_quality_control"]
                .isin(STATUSQUALITYCONTROL_LIST)
                .all()
            ):
                instance.validated = False
                instance.report += f"Fout in 'status_quality_control' kolom van {filename}: Ongeldige waarden gevonden.\n"
                status_quality_control_col = None
        else:
            instance.report += f"De kolom 'status_quality_control' kan gegeven worden in {filename} om extra metadata toe te voegen aan elke tijd-waardepaar\n"

        # validate the censor_reason column if given in csv
        if "censor_reason" in reader.columns:
            CENSORREASON_LIST = [status[0] for status in CENSORREASON]
            censor_reason_col = "censor_reason"
            # Validate that all values in the column are in the allowed set
            if not reader["censor_reason"].isin(CENSORREASON_LIST).all():
                instance.validated = False
                instance.report += f"Fout in 'censor_reason' kolom van {filename}: Ongeldige waarden gevonden.\n"
                censor_reason_col = None
        else:
            instance.report += f"De kolom 'censor_reason' kan gegeven worden in {filename} om extra metadata toe te voegen aan elke tijd-waardepaar\n"

        # validate the interpolation_code column if given in csv
        if "interpolation_code" in reader.columns:
            INTERPOLATIONTYPE_LIST = [status[0] for status in INTERPOLATIONTYPE]
            # Validate that all values in the column are in the allowed set
            interpolation_code_col = "interpolation_code"
            if not reader["interpolation_code"].isin(INTERPOLATIONTYPE_LIST).all():
                instance.validated = False
                instance.report += f"Fout in 'interpolation_code' kolom van {filename}: Ongeldige waarden gevonden.\n"
                interpolation_code_col = None
        else:
            instance.report += f"De kolom 'interpolation_code' kan gegeven worden in {filename} om extra metadata toe te voegen aan elke tijd-waardepaar\n"

    except Exception as e:
        instance.validated = False
        instance.report += f"CSV processing error in {filename}: {e}\n"
        reader = pd.DataFrame({})
        time_col = None
        status_quality_control_col = None
        censor_reason_col = None
        interpolation_code_col = None

    instance.report += (
        f"{status_quality_control_col}, {censor_reason_col}, {interpolation_code_col}\n"
    )

    return (
        reader,
        time_col,
        status_quality_control_col,
        censor_reason_col,
        interpolation_code_col,
    )


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
