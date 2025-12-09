import logging
from datetime import datetime

import polars as pl
from bro.models import Organisation
from django.core.management.base import BaseCommand
from django.db import transaction
from gld.models import (
    GroundwaterLevelDossier,
    MeasurementPointMetadata,
    MeasurementTvp,
    Observation,
    ObservationMetadata,
    ObservationProcess,
)
from gmw.models import GroundwaterMonitoringTubeStatic

logger = logging.getLogger(__name__)


def read_sensorbucket_multiflexmeter_data(csv):
    df = pl.read_csv(csv, has_header=True, separator=";", ignore_errors=True)
    print(df.head())
    df_device = df.select(
        [
            "device code",
            "device description",
            "device latitude",
            "device longitude",
            "device properties installation_date",
            "device properties veldcode",
        ]
    ).filter(pl.col("device code").is_not_null())

    df_sensor = df.select(
        [
            "sensor properties veldcode",
            "sensor properties filter",
            "sensor properties module_serial_no",
            "sensor properties firmware_version",
        ]
    ).filter(pl.col("sensor properties veldcode").is_not_null())

    df_joined = df_device.join(
        df_sensor,
        left_on="device properties veldcode",
        right_on="sensor properties veldcode",
        how="inner",
    )

    df_dates = df_joined.select(
        [
            "device code",
            "device properties installation_date",
            "sensor properties filter",
        ]
    )
    df_dates = df_dates.rename(
        {
            "device code": "nitg_code",
            "device properties installation_date": "installation_date",
            "sensor properties filter": "filter_number",
        }
    )
    return df_dates


def get_imbroa_glds(tube):
    glds_imbroa = GroundwaterLevelDossier.objects.filter(
        groundwater_monitoring_tube=tube, quality_regime="IMBRO/A"
    )
    return glds_imbroa


def get_multiflex_installation_date(
    tube: GroundwaterMonitoringTubeStatic, df_multiflex: pl.DataFrame
):
    tube_number = tube.tube_number
    nitg_code = tube.groundwater_monitoring_well_static.nitg_code

    df_multiflex_tube = df_multiflex.filter(
        (pl.col("nitg_code") == nitg_code) & (pl.col("filter_number") == tube_number)
    )
    if df_multiflex_tube.height == 0:
        return None
    else:
        installation_date = (
            df_multiflex_tube.row(0, named=True)["installation_date"]
            + " 00:00:00+00:00"
        )
        return datetime.fromisoformat(installation_date)


def get_imbroa_measurements_after_2020(
    glds: list[GroundwaterLevelDossier], multiflex_date: datetime
) -> dict:
    """
    measurements dict:
    {
        gld.__str__(): {
            "multiflex_date": datetime,
            "regular_measurements": List[MeasurementTvp],
            "controle_measurements": List[MeasurementTvp]
        }
    }
    """
    measurements = {}

    if not glds:
        return measurements

    for gld in glds:
        gld_name = gld.__str__()

        observations_imbroa_regular = Observation.objects.filter(
            groundwater_level_dossier=gld,
            observation_metadata__observation_type="reguliereMeting",
        )
        measurements_imbroa_regular = MeasurementTvp.objects.filter(
            observation__in=observations_imbroa_regular
        ).order_by("measurement_time")
        measurements_imbroa_post_2020_regular = list(
            measurements_imbroa_regular.filter(
                measurement_time__gte=datetime(2021, 1, 1)
            )
        )

        observations_imbroa_control = Observation.objects.filter(
            groundwater_level_dossier=gld,
            observation_metadata__observation_type="controlemeting",
        )
        measurements_imbroa_control = MeasurementTvp.objects.filter(
            observation__in=observations_imbroa_control
        ).order_by("measurement_time")
        measurements_imbroa_post_2020_control = list(
            measurements_imbroa_control.filter(
                measurement_time__gte=datetime(2021, 1, 1)
            )
        )

        if (
            measurements_imbroa_post_2020_regular
            or measurements_imbroa_post_2020_control
        ):
            measurements[gld_name] = {
                "multiflex_date": multiflex_date,
                "regular_measurements": measurements_imbroa_post_2020_regular,
                "controle_measurements": measurements_imbroa_post_2020_control,
            }

    return measurements


def create_imbro_dossiers(
    tube: GroundwaterMonitoringTubeStatic, measurements: dict, summary
):
    if not measurements:
        return [], summary

    glds_imbro = []
    for gld_imbroa, measurement_data in measurements.items():
        measurements_regular = measurement_data["regular_measurements"]
        measurements_control = measurement_data["controle_measurements"]
        if measurements_regular or measurements_control:
            gld_imbro, created = GroundwaterLevelDossier.objects.get_or_create(
                groundwater_monitoring_tube=tube, quality_regime="IMBRO"
            )
            gld_imbro.save()
            glds_imbro.append(gld_imbro)
            summary["total_imbro_glds_processed"] += 1
            if created:
                summary["total_imbro_glds_created"] += 1

    return glds_imbro, summary


def create_regular_observations(glds, measurements, summary):
    if not glds:
        return {}, summary

    ## if in multiflex, then split obs

    observation_process_regular, created = ObservationProcess.objects.get_or_create(
        process_reference="STOWAgwst",
        measurement_instrument_type="druksensor",
        air_pressure_compensation_type="capillair",
        process_type="algoritme",
        evaluation_procedure="oordeelDeskundige",
    )
    observation_process_regular_analog, created = (
        ObservationProcess.objects.get_or_create(
            process_reference="STOWAgwst",
            measurement_instrument_type="analoogPeilklokje",
            air_pressure_compensation_type="capillair",
            process_type="algoritme",
            evaluation_procedure="oordeelDeskundige",
        )
    )
    observation_metadata_regular, created = ObservationMetadata.objects.get_or_create(
        observation_type="reguliereMeting",
        status="voorlopig",
        responsible_party=Organisation.objects.get(company_number="20168636"),
    )

    observations = {}
    for gld in glds:
        gld_name = gld.__str__()
        multiflex_date = measurements[gld_name]["multiflex_date"]
        regular_measurements: list[MeasurementTvp] = measurements[gld_name][
            "regular_measurements"
        ]
        regular_measurement_times = [
            mtvp.measurement_time for mtvp in regular_measurements
        ]

        observation_analog, created = Observation.objects.get_or_create(
            groundwater_level_dossier=gld,
            observation_process=observation_process_regular_analog,
            observation_metadata=observation_metadata_regular,
        )
        observations[gld_name] = observation_analog
        summary["total_imbro_regular_observations_processed"] += 1
        if created:
            summary["total_imbro_regular_observations_created"] += 1

        if (
            multiflex_date
            and regular_measurement_times
            and multiflex_date > regular_measurement_times[0]
        ):
            observation_multiflex, created = Observation.objects.get_or_create(
                groundwater_level_dossier=gld,
                observation_process=observation_process_regular,
                observation_metadata=observation_metadata_regular,
            )
            observations[gld_name] = [observation_analog, observation_multiflex]
            summary["total_imbro_regular_observations_processed"] += 1
            if created:
                summary["total_imbro_regular_observations_created"] += 1

    return observations, summary


def create_control_observations(glds, measurements, summary):
    if not glds:
        return {}, summary

    observation_process_control, created = ObservationProcess.objects.get_or_create(
        process_reference="STOWAgwst",
        measurement_instrument_type="analoogPeilklokje",
        process_type="algoritme",
        evaluation_procedure="oordeelDeskundige",
    )
    observation_metadata_control, created = ObservationMetadata.objects.get_or_create(
        observation_type="controlemeting",
        status="voorlopig",
        responsible_party=Organisation.objects.get(company_number="20168636"),
    )

    observations = {}
    for gld in glds:
        gld_name = gld.__str__()
        observation, created = Observation.objects.get_or_create(
            groundwater_level_dossier=gld,
            observation_process=observation_process_control,
            observation_metadata=observation_metadata_control,
        )
        observations[gld_name] = observation
        summary["total_imbro_control_observations_processed"] += 1
        if created:
            summary["total_imbro_control_observations_created"] += 1

    return observations, summary


def create_imbro_measurements(
    measurements, observation_type, observations_regular, observations_control, summary
):
    if not measurements:
        return summary

    measurements_imbro = []
    measurement_metadatas_imbro = []
    for gld_imbroa, measurement_data in measurements.items():
        measurements_regular = measurement_data["regular_measurements"]
        measurements_control = measurement_data["controle_measurements"]
        multiflex_date = measurement_data["multiflex_date"]

        if observation_type == "reguliereMeting":
            measurements_imbroa = measurements_regular
            dummy_observation = observations_regular.get(gld_imbroa, None)
        elif observation_type == "controlemeting":
            measurements_imbroa = measurements_control
            dummy_observation = observations_control.get(gld_imbroa, None)
        else:
            measurements_imbroa = []
            dummy_observation = None
        if not measurements_imbroa or not dummy_observation:
            # logger.info("No measurements or observation in data")
            return summary

        observations = [dummy_observation] * len(measurements_imbroa)
        measurements_imbroa: list[MeasurementTvp]
        if isinstance(dummy_observation, list) and multiflex_date:
            for i, (mtvp, obs) in enumerate(zip(measurements_imbroa, observations)):
                obs_analog = obs[0]
                obs_multiflex = obs[1]
                if mtvp.measurement_time < multiflex_date:
                    observations[i] = obs_analog
                else:
                    observations[i] = obs_multiflex

        measurement_metadatas_imbroa: list[MeasurementPointMetadata] = [
            mtvp.measurement_point_metadata for mtvp in measurements_imbroa
        ]
        measurement_metadatas_imbro.extend(
            [
                MeasurementPointMetadata(
                    status_quality_control=mm.status_quality_control,
                    censor_reason=mm.censor_reason,
                    censor_reason_datalens=mm.censor_reason_datalens,
                    value_limit=mm.value_limit,
                )
                if mm
                else MeasurementPointMetadata()
                for mm in measurement_metadatas_imbroa
            ]
        )
        measurements_imbro.extend(
            [
                MeasurementTvp(
                    observation=observation,
                    measurement_time=mtvp.measurement_time,
                    field_value=mtvp.field_value,
                    field_value_unit=mtvp.field_value_unit,
                    calculated_value=mtvp.calculated_value,
                    value_to_be_corrected=mtvp.initial_calculated_value,
                    correction_time=mtvp.correction_time,
                    correction_reason=mtvp.correction_reason,
                    measurement_point_metadata=mm,
                    comment=mtvp.comment,
                )
                for mtvp, mm, observation in zip(
                    measurements_imbroa, measurement_metadatas_imbro, observations
                )
            ]
        )
        if observation_type == "reguliereMeting":
            summary["total_imbro_regular_measurements_created"] += len(
                measurements_imbroa
            )
        elif observation_type == "controlemeting":
            summary["total_imbro_control_measurements_created"] += len(
                measurements_imbroa
            )

    with transaction.atomic():
        try:
            logger.info(
                f"Bulk creating measurements for for GLDs {list(measurements.keys())}"
            )
            MeasurementPointMetadata.objects.bulk_create(
                measurement_metadatas_imbro,
                update_conflicts=False,
                batch_size=5000,
            )
            MeasurementTvp.objects.bulk_create(
                measurements_imbro,
                update_conflicts=False,
                batch_size=5000,
            )
        except Exception:
            print("Bulk updating/creating failed.")

    for observation in observations:
        observation.observation_starttime = observation.timestamp_first_measurement
        observation.save(update_fields=["observation_starttime"])

    return summary


def create_imbro_glds(csv):
    """
    Creates IMBRO GLDs by taking data post 2021-01-01 from existing IMBRO/A GLDs.
    Args:
        -
    Returns:
        dict: Summary of split operations
    """

    summary = {
        "total_imbro_glds_processed": 0,
        "total_imbro_glds_created": 0,
        "total_imbro_regular_observations_processed": 0,
        "total_imbro_regular_observations_created": 0,
        "total_imbro_control_observations_processed": 0,
        "total_imbro_control_observations_created": 0,
        "total_imbro_regular_measurements_created": 0,
        "total_imbro_control_measurements_created": 0,
    }

    tubes = GroundwaterMonitoringTubeStatic.objects.filter(
        groundwater_monitoring_well_static__delivery_accountable_party=Organisation.objects.get(
            company_number="20168636"
        )
    )
    multiflex_sensors = read_sensorbucket_multiflexmeter_data(csv)
    # logger.info(f"Number of tubes: {len(tubes)}")

    for tube in tubes:
        # logger.info(f"Tube: {tube}")
        glds_imbroa = get_imbroa_glds(tube)
        # logger.info(f"Number of glds: {len(glds_imbroa)}")
        multiflex_installation_date = get_multiflex_installation_date(
            tube, multiflex_sensors
        )
        # logger.info(f"Multiflex installation date: {multiflex_installation_date}")
        measurements_imbro = get_imbroa_measurements_after_2020(
            glds_imbroa, multiflex_installation_date
        )
        # logger.info(measurements_imbro.keys())
        glds_imbro, summary = create_imbro_dossiers(tube, measurements_imbro, summary)
        # logger.info(glds_imbro)

        dummy_regular_observations, summary = create_regular_observations(
            glds_imbro, measurements_imbro, summary
        )
        dummy_control_observations, summary = create_control_observations(
            glds_imbro, measurements_imbro, summary
        )
        summary = create_imbro_measurements(
            measurements_imbro,
            "reguliereMeting",
            dummy_regular_observations,
            dummy_control_observations,
            summary,
        )
        summary = create_imbro_measurements(
            measurements_imbro,
            "controlemeting",
            dummy_regular_observations,
            dummy_control_observations,
            summary,
        )

    return summary


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            type=str,
            help="De Sensorbucket CSV.",
        )

    def handle(self, *args, **options):
        ## CAUTION!!!!!
        ## This script will create measurement duplicates from gld imbroa measurements after 2021-01-01 and store them in a new imbro gld
        ## In doing so this script will create duplicates of gld imbro measurements if this process has already been run
        ## Only accept the terms below if you are okay with this.

        I_WILLINGLY_RUN_THIS_SCRIPT_AND_REALISE_THAT_I_MIGHT_CREATE_MEASUREMENT_DUPLICATES = True

        if (
            I_WILLINGLY_RUN_THIS_SCRIPT_AND_REALISE_THAT_I_MIGHT_CREATE_MEASUREMENT_DUPLICATES
            == True
        ):
            result = create_imbro_glds(csv=options["csv"])
            logger.info("IMBRO/A to IMBRO Summary:")
            logger.info(f"Total GLDs Processed: {result['total_imbro_glds_processed']}")
            logger.info(f"Total GLDs Created: {result['total_imbro_glds_created']}")
            logger.info(
                f"Total Regular Observations Processed: {result['total_imbro_regular_observations_processed']}"
            )
            logger.info(
                f"Total Regular Observations Created: {result['total_imbro_regular_observations_created']}"
            )
            logger.info(
                f"Total Control Observations Processed: {result['total_imbro_control_observations_processed']}"
            )
            logger.info(
                f"Total Control Observations Created: {result['total_imbro_control_observations_created']}"
            )
            logger.info(
                f"Total Regular Measurements Created: {result['total_imbro_regular_measurements_created']}"
            )
            logger.info(
                f"Total Control Measurements Created: {result['total_imbro_control_measurements_created']}"
            )
