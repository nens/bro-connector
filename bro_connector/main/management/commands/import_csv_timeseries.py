import csv
import logging
from typing import Union
from django.core.management.base import BaseCommand
import datetime
from gmw import models as gmw_models
from gld import models as gld_models

logger = logging.getLogger(__name__)


def convert_value_to_float(val: str) -> Union[float, None]:
    if val == "dry":
        return None
    try:
        return float(str(val).replace(",", "."))
    except ValueError:
        return None


def create_measurement(
    observation: gld_models.Observation,
    tube_height: float,
    data: dict,
    datum: datetime.datetime,
) -> None:
    meta = gld_models.MeasurementPointMetadata.objects.create(
        status_quality_control="onbekend",
        interpolation_code="discontinu",
    )

    measurement_value = convert_value_to_float(data["value"])
    if measurement_value is not None:
        value_mNAP = tube_height - measurement_value
    else:
        value_mNAP = None

    gld_models.MeasurementTvp.objects.create(
        observation=observation,
        measurement_time=datum,
        field_value=value_mNAP,
        measurement_point_metadata=meta,
    )


def create_new_observation(
    tube: gmw_models.GroundwaterMonitoringTubeStatic, datum: datetime.datetime
):
    # Find GLD
    gld = gld_models.GroundwaterLevelDossier.objects.get(
        groundwater_monitoring_tube=tube
    )

    # Create Observatie process
    obs_process = gld_models.ObservationProcess.objects.create(
        process_reference="onbekend",
        measurement_instrument_type="onbekend",
        air_pressure_compensation_type="onbekend",
        process_type="algoritme",
        evaluation_procedure="oordeelDeskundige",
    )

    # Create Observatie metadata
    obs_metadata = gld_models.ObservationMetadata.objects.create(
        status="voorlopig",
        observation_type="controlemeting",
        date_stamp=datum.date(),
        responsible_party_id=1,
    )

    print(obs_metadata, obs_process, gld)
    # Create Observatie
    observatie = gld_models.Observation.objects.create(
        observation_starttime=datum,
        observation_metadata=obs_metadata,
        observation_process=obs_process,
        groundwater_level_dossier=gld,
        up_to_date_in_bro=False,
    )

    return observatie


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            help="the location of the csv file you would like to use.",
        )

    def handle(self, *args, **kwargs):
        # First it should accept a csv file
        file_path = kwargs.get("file")
        nitg_oud = "None"
        filter_oud = "None"
        new = False

        if not file_path:
            raise ValueError("No file_path provided.")

        with open(file_path, encoding="utf-8") as file:
            try:
                dialect = csv.Sniffer().sniff(file.readline())
            except OSError as e:
                logger.error(f"{e}")

            file.seek(0, 0)
            reader = csv.reader(file, dialect)
            for index, row in enumerate(reader):
                print(f"{index}: {row}")

                if index == 0:
                    header = [column_name.replace("\ufeff", "") for column_name in row]
                    continue

                data = dict(zip(header, row))

                if data["NITG"] != nitg_oud or data["filter"] != filter_oud:
                    new = True

                datum = datetime.datetime.strptime(data["date"], "%d/%m/%Y %H:%M")

                well = gmw_models.GroundwaterMonitoringWellStatic.objects.filter(
                    nitg_code=data["NITG"]
                ).first()

                if well is None:
                    logger.info(f"Well not found for {data['NITG']}")
                    continue

                tube = gmw_models.GroundwaterMonitoringTubeStatic.objects.filter(
                    groundwater_monitoring_well_static=well,
                    tube_number=data["filter"],
                ).first()

                tube_history = (
                    gmw_models.GroundwaterMonitoringTubeDynamic.objects.filter(
                        groundwater_monitoring_tube_static=tube,
                    )
                    .order_by("date_from")
                    .last()
                )

                if new is True:
                    nitg_oud = data["NITG"]
                    filter_oud = data["filter"]
                    observatie = create_new_observation(tube, datum)
                    new = False

                create_measurement(
                    observatie, tube_history.tube_top_position, data, datum
                )
