from ..tasks.bro_handlers import GLDHandler
from ..tasks.kvk_handler import DataRetrieverKVK
from ..tasks.progressor import Progress
import datetime
from gmw.models import GroundwaterMonitoringTubeStatic, GroundwaterMonitoringWellStatic


from gld.models import (
    GroundwaterLevelDossier,
    Observation,
    ObservationProcess,
    ObservationMetadata,
    MeasurementTvp,
    MeasurementPointMetadata,
    ResponsibleParty,
)

# BBOX VALUES ZEELAND
XMIN = 10000
XMAX = 80000
YMIN = 355000
YMAX = 420000


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
        coordinates.x > XMIN
        and coordinates.x < XMAX
        and coordinates.y > YMIN
        and coordinates.y < YMAX
    ):
        return True
    return False


def run(kvk_number: str = None, csv_file: str = None, bro_type: str = "gld"):
    progressor = Progress()
    gld = GLDHandler()

    if kvk_number != None:
        DR = DataRetrieverKVK(kvk_number)
        DR.request_bro_ids(bro_type)
        DR.get_ids_kvk()
        ids = DR.gld_ids
        ids_ini_count = len(ids)

    print(f"{ids_ini_count} bro ids found for organisation.")

    ids_count = len(ids)
    progressor.calibrate(ids, 25)

    # Import the well data
    for id in range(ids_count):
        print(ids[id])
        gld.get_data(ids[id], True)
        # To debug the error
        gld.root_data_to_dictionary()
        gmw_dict = gld.dict

        # Start at observation 1
        ini = InitializeData(gmw_dict)
        ini.groundwater_level_dossier()
        gld.reset_values()
        ini.reset_values()
        progressor.next()
        progressor.progress()
        continue
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

        gld.reset_values()
        ini.reset_values()
        progressor.next()
        progressor.progress()


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


def get_tube(bro_id: str, tube_number: int) -> str:
    try:
        well = GroundwaterMonitoringWellStatic.objects.get(bro_id=bro_id)

        tube = GroundwaterMonitoringTubeStatic.objects.get(
            groundwater_monitoring_well_static=well,
            tube_number=tube_number,
        )

        return tube
    except GroundwaterMonitoringWellStatic.DoesNotExist or GroundwaterMonitoringTubeStatic.DoesNotExist:
        return None


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
            GroundwaterLevelDossier.objects.update_or_create(
                gld_bro_id=self.gmw_dict["0_broId"][0],
                defaults=dict(
                    gmw_bro_id=self.gmw_dict["0_broId"][1],
                    groundwater_monitoring_tube=tube,
                    research_start_date=self.gmw_dict.get("0_researchFirstDate", None),
                    research_last_date=self.gmw_dict.get("0_researchLastDate", None),
                    research_last_correction=self.gmw_dict.get(
                        "0_latestCorrectionTime", None
                    ),
                )
            )
        )
        print(self.groundwater_level_dossier_instance[0], self.groundwater_level_dossier_instance[0].groundwater_monitoring_tube)

    def responsible_party(self) -> None:
        kvk = self.gmw_dict.get("0_deliveryAccountableParty", None)

        # Only make a new party if the KVK is not already in the database.
        # If it is already in the database
        if (
            len(
                ResponsibleParty.objects.filter(
                    identification=kvk,
                )
            )
            != 0
        ):
            self.responsible_party_instance = ResponsibleParty.objects.filter(
                identification=kvk,
            ).first()
            # Return without creating a new instance. Assign the found instance
            return

        # If None is found, update_or_create a new instance.
        self.responsible_party_instance = ResponsibleParty.objects.create(
            identification=kvk,
            organisation_name=None,  # Naam staat niet in XML, achteraf zelf veranderen
        )

    def metadata_observation(self) -> None:
        self.observation_metadate_instance = ObservationMetadata.objects.update_or_create(
            date_stamp=self.gmw_dict.get(f"{self.observation_number}_Date", None),
            observation_type=self.gmw_dict.get(
                f"{self.observation_number}_ObservationType", None
            ),
            status=self.gmw_dict.get(f"{self.observation_number}_status", None),
            responsible_party=self.responsible_party_instance,
        )

    def observation_process(self) -> None:
        self.observation_process_instance = ObservationProcess.objects.update_or_create(
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
        if start != None and end != None:
            interval = datetime.datetime.strptime(
                end, "%Y-%m-%d"
            ) - datetime.datetime.strptime(start, "%Y-%m-%d")

        self.observation_instance = Observation.objects.update_or_create(
            observationperiod=interval,
            observation_starttime=start,
            result_time=self.gmw_dict.get(
                f"{self.observation_number}_timePosition", None
            ),
            observation_endtime=end,
            observation_metadata=self.observation_metadate_instance,
            observation_process=self.observation_process_instance,
            groundwater_level_dossier=self.groundwater_level_dossier_instance,
            status=self.gmw_dict.get(f"{self.observation_number}_status", None),
        )

    def metadata_measurement_tvp(self, measurement_number: int) -> None:
        censor_reason = get_censor_reason(
            self.gmw_dict, self.observation_number, measurement_number
        )
        self.metadata_measurement_tvp_instance = MeasurementPointMetadata.objects.update_or_create(
            qualifier_by_category=self.gmw_dict.get(
                f"{self.observation_number}_point_qualifier_value", [None]
            )[measurement_number],
            interpolation_code="discontinu",  # Standard, only option
            censored_reason=censor_reason,
            # qualifier_by_quantity = self.gmw_dict.get("", None),      # Currently not known how to handle
        )

    def measurement_tvp(self, measurement_number: int) -> None:
        self.measurement_tvp_instance = MeasurementTvp.objects.update_or_create(
            observation=self.observation_instance,
            measurement_time=self.gmw_dict.get(
                f"{self.observation_number}_point_time", [None]
            )[measurement_number],
            field_value=self.gmw_dict.get(
                f"{self.observation_number}_point_value", None
            )[measurement_number],
            field_value_unit=self.gmw_dict.get(f"{self.observation_number}_unit", None)[
                measurement_number
            ],
            measurement_point_metadata=self.metadata_measurement_tvp_instance,
            # calculated_value = self.gmw_dict.get("", None),           # nvt
            # corrected_value = self.gmw_dict.get("", None),            # nvt
            # correction_time = self.gmw_dict.get("", None),            # nvt
            # correction_reason = self.gmw_dict.get("", None),          # nvt
        )

    def reset_values(self) -> None:
        self.observation_number = 0
