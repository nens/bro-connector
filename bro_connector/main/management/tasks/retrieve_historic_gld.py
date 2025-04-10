from ..tasks.bro_handlers import GLDHandler
from ..tasks.kvk_handler import DataRetrieverKVK
from ..tasks.progressor import Progress
import datetime
from gmw.models import GroundwaterMonitoringTubeStatic, GroundwaterMonitoringWellStatic
import logging
from django.conf import settings

from bro.models import Organisation
from gld.models import (
    GroundwaterLevelDossier,
    Observation,
    ObservationProcess,
    ObservationMetadata,
    MeasurementTvp,
    MeasurementPointMetadata,
)

logger = logging.getLogger(__name__)


def gmw_get_or_none(bro_id: str):
    try:
        return GroundwaterMonitoringWellStatic.objects.get(
            bro_id=bro_id,
        )

    # In some cases the bro_id might not yet be in the GMW database
    # In the future this should retrieve the GMW information and create an object before continueing.
    except GroundwaterMonitoringWellStatic.DoesNotExist:
        return None

    # If the bro_id = None, multiple might be returned.
    except GroundwaterMonitoringWellStatic.MultipleObjectsReturned:
        return None


def within_bbox(coordinates) -> bool:
    print(f"x: {coordinates.x}, y: {coordinates.y}")
    if (
        coordinates.x > settings["BBOX_SETTINGS"]["xmin"]
        and coordinates.x < settings["BBOX_SETTINGS"]["xmax"]
        and coordinates.y > settings["BBOX_SETTINGS"]["ymin"]
        and coordinates.y < settings["BBOX_SETTINGS"]["ymax"]
    ):
        return True
    return False


def run(kvk_number: str = None, csv_file: str = None, bro_type: str = "gld"):
    progressor = Progress()
    gld = GLDHandler()

    if kvk_number:
        DR = DataRetrieverKVK(kvk_number)
        DR.request_bro_ids(bro_type)
        DR.get_ids_kvk()
        ids = DR.gld_ids
        ids_ini_count = len(ids)

    if ids_ini_count == 0:
        print(f"No IDs found for kvk: {kvk_number}.")
        return {"ids_found": ids_ini_count, "imported": ids_ini_count}

    print(f"{ids_ini_count} bro ids found for organisation.")

    imported = 0
    ids_count = len(ids)
    progressor.calibrate(ids, 25)

    # Import the well data
    for id in range(ids_count):
        glds = GroundwaterLevelDossier.objects.filter(gld_bro_id=ids[id])

        if len(glds) > 0:
            logger.info(f"{ids[id]} already in database.")
            continue

        gld.get_data(ids[id], False)
        # To debug the error
        gld.root_data_to_dictionary()
        gmw_dict = gld.dict

        # Start at observation 1
        ini = InitializeData(gmw_dict)
        ini.groundwater_level_dossier()
        ini.responsible_party()

        print("total points: ", gld.number_of_points)

        if gld.number_of_observations > 1:
            gld.count_dictionary[gld.number_of_observations] = (
                gld.number_of_points
                - gld.count_dictionary[gld.number_of_observations - 1]
            )
        else:
            gld.count_dictionary[1] = gld.number_of_points

        print(gld.count_dictionary)

        count = 1
        for observation_number in range(1, (1 + gld.number_of_observations)):
            ini.increment_observation_number()

            ini.observation_process()
            ini.metadata_observation()
            ini.observation()

            for measurement_number in range(gld.count_dictionary[observation_number]):
                if count % 100 == 0:
                    print(count)
                ini.metadata_measurement_tvp(measurement_number)
                ini.measurement_tvp(measurement_number)
                count += 1

        imported += 1
        gld.reset_values()
        ini.reset_values()
        progressor.next()
        progressor.progress()

    info = {
        "ids_found": ids_ini_count,
        "imported": imported,
    }

    return info


def get_censor_reason(
    dict: dict, observation_number: int, measurement_number: int
) -> str:
    censor_reasons = dict.get(
        f"{observation_number}_point_censoring_censoredReason", None
    )

    if censor_reasons is not None:
        censor_reason = censor_reasons[measurement_number]
        if censor_reason == "BelowDetectionRange":
            return "kleinerDanLimietwaarde"

        elif censor_reason == "AboveDetectionRange":
            return "groterDanLimietwaarde"

        else:
            return "onbekend"

    return None


def _calculate_value(field_value: float, unit: str):
    """
    For now only supports m / cm / mm.
    Conversion to
    """
    if field_value is None or unit is None:
        return None
    if unit == "m":
        return field_value
    elif unit == "cm":
        return field_value / 10
    elif unit == "mm":
        return field_value / 100
    else:
        return None


def get_tube(bro_id: str, tube_number: int) -> str:
    try:
        well = GroundwaterMonitoringWellStatic.objects.get(bro_id=bro_id)

        tube = GroundwaterMonitoringTubeStatic.objects.get(
            groundwater_monitoring_well_static=well,
            tube_number=tube_number,
        )

        return tube
    except (
        GroundwaterMonitoringWellStatic.DoesNotExist
        or GroundwaterMonitoringTubeStatic.DoesNotExist
    ):
        return None


def str_to_date(string: str | None) -> datetime.date | None:
    """
    From string [2024-05-03] to datetime conversion.
    """
    if string:
        return datetime.datetime.strptime(string, "%Y-%m-%d").date()


def str_to_datetime(string: str | None) -> datetime.datetime | None:
    """
    From string [2024-05-03T11:51:01+02:00] to datetime conversion.
    """
    if string:
        if len(string) == len("2024-05-03T11:51:01+02:00"):
            return datetime.datetime.strptime(string, "%Y-%m-%dT%H:%M:%S%z")
        elif len(string) == len("2024-05-03"):
            return datetime.datetime.strptime(string, "%Y-%m-%d")


class InitializeData:
    """
    Function that allow you to create initial data when reading data from the BRO.
    The xml converted to dictionary is read into the database.
    """

    def __init__(self, gmw_dict: dict) -> None:
        self.gmw_dict = gmw_dict
        self.observation_number = 0

    def increment_observation_number(self) -> None:
        self.observation_number += 1

    def groundwater_level_dossier(self) -> None:
        tube = get_tube(self.gmw_dict["0_broId"][1], self.gmw_dict["0_tubeNumber"])
        print(tube)
        self.groundwater_level_dossier_instance = (
            GroundwaterLevelDossier.objects.create(
                gld_bro_id=self.gmw_dict["0_broId"][0],
                groundwater_monitoring_tube=tube,
                research_start_date=str_to_date(
                    self.gmw_dict.get("0_researchFirstDate", None)
                ),
                research_last_date=str_to_date(
                    self.gmw_dict.get("0_researchLastDate", None)
                ),
                research_last_correction=str_to_datetime(
                    self.gmw_dict.get("0_latestCorrectionTime", None)
                ),
            )
        )
        print(
            self.groundwater_level_dossier_instance,
            self.groundwater_level_dossier_instance.groundwater_monitoring_tube,
        )

    def responsible_party(self) -> None:
        kvk = self.gmw_dict.get("0_deliveryAccountableParty", None)

        # Only make a new party if the KVK is not already in the database.
        # If it is already in the database
        if (
            len(
                Organisation.objects.filter(
                    company_number=kvk,
                )
            )
            != 0
        ):
            self.responsible_party_instance = Organisation.objects.filter(
                company_number=kvk,
            ).first()
            # Return without creating a new instance. Assign the found instance
            return

        # If None is found, get_or_create a new instance.
        self.responsible_party_instance = Organisation.objects.create(
            company_number=kvk,
            organisation_name=None,  # Naam staat niet in XML, achteraf zelf veranderen
        )

    def metadata_observation(self) -> None:
        self.observation_metadate_instance, created = ObservationMetadata.objects.get_or_create(
            observation_type=self.gmw_dict.get(
                f"{self.observation_number}_ObservationType", None
            ),
            status=self.gmw_dict.get(f"{self.observation_number}_status", None),
            responsible_party=self.responsible_party_instance,
        )

    def observation_process(self) -> None:
        self.observation_process_instance, created = ObservationProcess.objects.get_or_create(
            process_reference=self.gmw_dict.get(
                f"{self.observation_number}_processReference", None
            ),
            measurement_instrument_type=self.gmw_dict.get(
                f"{self.observation_number}_MeasurementInstrumentType", None
            ),
            process_type="algoritme",  # Standard, only option
            evaluation_procedure=self.gmw_dict.get(
                f"{self.observation_number}_EvaluationProcedure", None
            ),
            # air_pressure_compensation_type = self.gmw_dict.get(f"", None),    # Currently not known how to handle -> Not found in initial gld
        )

    def observation(self) -> None:
        start = self.gmw_dict.get(f"{self.observation_number}_beginPosition", None)
        end = self.gmw_dict.get(f"{self.observation_number}_endPosition", None)
        interval = None
        if start and end:
            interval = datetime.datetime.strptime(
                end, "%Y-%m-%d"
            ) - datetime.datetime.strptime(start, "%Y-%m-%d")

        end = str_to_datetime(end)
        start = str_to_datetime(start)
        result_time = str_to_datetime(
            self.gmw_dict.get(f"{self.observation_number}_timePosition", None)
        )
        self.observation_instance = Observation.objects.create(
            observationperiod=interval,
            observation_starttime=start,
            result_time=result_time,
            observation_endtime=end,
            observation_metadata=self.observation_metadate_instance,
            observation_process=self.observation_process_instance,
            groundwater_level_dossier=self.groundwater_level_dossier_instance,
            up_to_date_in_bro=True,
        )

    def metadata_measurement_tvp(self, measurement_number: int) -> None:
        censor_reason = get_censor_reason(
            self.gmw_dict, self.observation_number, measurement_number
        )
        self.metadata_measurement_tvp_instance = (
            MeasurementPointMetadata.objects.create(
                status_quality_control=self.gmw_dict.get(
                    f"{self.observation_number}_point_qualifier_value", "onbekend"
                )[measurement_number],
                interpolation_code="discontinu",  # Standard, only option
                censor_reason=censor_reason,
            )
        )

    def measurement_tvp(self, measurement_number: int) -> None:
        calculated_value = _calculate_value(
            self.gmw_dict.get(f"{self.observation_number}_point_value", None)[
                measurement_number
            ],
            self.gmw_dict.get(f"{self.observation_number}_unit", None)[
                measurement_number
            ],
        )
        self.measurement_tvp_instance = MeasurementTvp.objects.create(
            observation=self.observation_instance,
            measurement_time=str_to_datetime(
                self.gmw_dict.get(f"{self.observation_number}_point_time", [None])[
                    measurement_number
                ]
            ),
            field_value=self.gmw_dict.get(
                f"{self.observation_number}_point_value", None
            )[measurement_number],
            field_value_unit=self.gmw_dict.get(f"{self.observation_number}_unit", None)[
                measurement_number
            ],
            calculated_value=calculated_value,
            measurement_point_metadata=self.metadata_measurement_tvp_instance,
        )

    def reset_values(self) -> None:
        self.observation_number = 0
