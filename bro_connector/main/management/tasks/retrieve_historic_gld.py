from ..tasks.bro_handlers import GLDHandler
from ..tasks.kvk_handler import DataRetrieverKVK
from .bbox_handler import DataRetrieverBBOX
from ..tasks.progressor import Progress
import reversion
import datetime
from zoneinfo import ZoneInfo
from gmw.models import GroundwaterMonitoringTubeStatic, GroundwaterMonitoringWellStatic
import logging
from django.conf import settings
from main.utils.bbox_extractor import BBOX_EXTRACTOR
import time
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


def run(kvk_number: str = None, bro_type: str = "gld", handler: str = "shape", shp_file: str = None, delete: bool = False) -> dict:
    if shp_file == None:
        shp_file = settings.POLYGON_SHAPEFILE
    shp = shp_file
    bbox_settings = BBOX_EXTRACTOR(shp=shp, use_bbox=True).bbox_settings
    bbox = BBOX_EXTRACTOR(shp=shp, use_bbox=True).bbox
    progressor = Progress()
    gld = GLDHandler()

    if kvk_number and handler.lower() == "kvk":
        DR = DataRetrieverKVK(kvk_number)
        DR.request_bro_ids(bro_type)
        DR.get_ids_kvk()
        gld_ids = DR.gld_ids
        gld_ids_ini_count = len(gld_ids)

    if bbox_settings["use_bbox"] and handler.lower() == "shape":
        print("bbox settings: ", bbox_settings)
        DR = DataRetrieverBBOX(bbox)
        DR.request_bro_ids(bro_type)
        DR.filter_ids_kvk(kvk_number)
        DR.enforce_shapefile(shp, delete=delete)
        DR.get_ids_ogc()
        gld_ids = DR.gld_ids
        gld_ids_ini_count = len(gld_ids)

    if gld_ids_ini_count == 0:
        print(f"No IDs found for kvk: {kvk_number}.")
        return {"ids_found": gld_ids_ini_count, "imported": gld_ids_ini_count}

    print(f"{gld_ids_ini_count} bro ids found for organisation.")

    imported = 0
    gld_ids_count = len(gld_ids)
    progressor.calibrate(gld_ids, 25)

    # Import the well data
    for id in range(1):#gld_ids_count):
        start = time.time()
        print("BRO id: ",gld_ids[id])

        gld.get_data(gld_ids[id], False)
        if gld.root is None:
            continue
        gld.root_data_to_dictionary()
        gld_dict = gld.dict

        # For now don't handle deregistered GMWs
        if gld_dict.get("0_deregistered", None) == "ja":
            continue

        # Start at observation 1
        ini = InitializeData(gld_dict)
        ini.well_static()
        ini.tube_static()
        ini.groundwater_level_dossier()

        if ini.gld is None:
            continue

        print("total points: ", gld.number_of_points)

        step = max(1, gld.number_of_points // 4)
        for observation_number in range(gld.number_of_observations):
            ini.increment_observation_number()
            ini.observation_metadata()
            ini.observation_process()
            ini.observation()

            # print(f"Total number of measurements for observation {observation_number}: {gld.count_dictionary[observation_number]}")
            for measurement_number in range(gld.number_of_measurements[ini.observation_number]):
                if ini.measurement_count % step == 0 or ini.measurement_count == gld.number_of_points:
                    print(f"{(ini.measurement_count / gld.number_of_points) * 100:.0f}% done ({ini.measurement_count}/{gld.number_of_points})")

                ini.measurement_metadata()
                ini.measurement_tvp()
                ini.increment_measurement_number()
            
            ini.reset_measurement_number()

        imported += 1
        ini.reset_values()
        progressor.next()
        progressor.progress()

        end = time.time()
        print(f"Time for one GLD: {end-start}s")

    info = {
        "ids_found": gld_ids_count,
        "imported": imported,
    }

    return info

def get_delivery_accountable_party(self) -> None:
        company_id = self.gld_dict.get("0_deliveryAccountableParty", None)
        if company_id is None:
            return (None, False)
        if company_id.isdigit():
            return Organisation.objects.get_or_create(company_number=company_id)
        else:
            return Organisation.objects.get_or_create(name=company_id)

def get_censor_reason(
    dict: dict, prefix: str, measurement_number: int
) -> str:
    censor_reasons = dict.get(
        prefix + "point_censoring_censoredReason", None
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
    
def get_bro_id_by_type(bro_ids: list[str], bro_type: str):
    try:
        bro_id = None
        for id in bro_ids:
            if id.lower().startswith(bro_type.lower().strip()):
                bro_id = id
                break
        return bro_id
    except:
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
            return datetime.datetime.strptime(string, "%Y-%m-%d").replace(tzinfo=ZoneInfo("Europe/Amsterdam"))


class InitializeData:
    """
    Function that allow you to create initial data when reading data from the BRO.
    The xml converted to dictionary is read into the database.
    """

    observation_number = 0
    measurement_number = 0
    measurement_count = 0
    prefix = f"{observation_number}_"

    def __init__(self, gld_dict: dict) -> None:
        self.gld_dict = gld_dict
        self.gld_bro_id = get_bro_id_by_type(self.gld_dict.get(self.prefix + "broId"), "gld")
        self.gmw_bro_id = get_bro_id_by_type(self.gld_dict.get(self.prefix + "broId"), "gmw")
        self.gmn_bro_id =get_bro_id_by_type(self.gld_dict.get(self.prefix + "broId"), "gmn")
        
    def reset_measurement_number(self):
        self.measurement_number = 0

    def increment_observation_number(self) -> None:
        self.observation_number += 1
        self.prefix = f"{self.observation_number}_"

    def increment_measurement_number(self) -> None:
        self.measurement_number += 1
        self.measurement_count += 1

    def well_static(self) -> None:
        try:
            self.gmws = GroundwaterMonitoringWellStatic.objects.get(
                bro_id=self.gmw_bro_id
            )
        except (
            GroundwaterMonitoringWellStatic.DoesNotExist
            or GroundwaterMonitoringTubeStatic.MultipleObjectsReturned
        ):
            self.gmws = None

    def tube_static(self) -> None:
        try:
            self.gmts = GroundwaterMonitoringTubeStatic.objects.get(
            groundwater_monitoring_well_static=self.gmws,
            tube_number = self.gld_dict.get(self.prefix + "tubeNumber", None),
        )
        except (
            GroundwaterMonitoringTubeStatic.DoesNotExist
            or GroundwaterMonitoringTubeStatic.MultipleObjectsReturned
        ):
            self.gmts = None

    def groundwater_level_dossier(self) -> None:
        with reversion.create_revision():
            self.gld, created = GroundwaterLevelDossier.objects.update_or_create(
                gld_bro_id=self.gld_bro_id,
                groundwater_monitoring_tube=self.gmts,
                defaults={
                    "quality_regime": self.gld_dict.get(self.prefix + "qualityRegime", "onbekend"),
                    "research_start_date": str_to_date(
                        self.gld_dict.get(self.prefix + "researchFirstDate", None)
                    ),
                    "research_last_date": str_to_date(
                        self.gld_dict.get(self.prefix + "researchLastDate", None)
                    ),
                    "research_last_correction": str_to_datetime(
                        self.gld_dict.get(self.prefix + "latestCorrectionTime", None)
                    ),
                }
            )

            reversion.set_comment(
                f"Updated from BRO-database({datetime.datetime.now().astimezone()})"
            )

            self.gld.save()

            print(
                self.gld,
                self.gld.groundwater_monitoring_tube,
                " - created: ", created
            )

    def observation_metadata(self) -> None:
        try:
            self.obsm, created = (
                ObservationMetadata.objects.get_or_create(
                    observation_type=self.gld_dict.get(
                        self.prefix + "ObservationType", None
                    ),
                    status=self.gld_dict.get(
                        self.prefix + "status", None
                    ),
                    responsible_party=get_delivery_accountable_party(self)[0],
                )
            )
        except ObservationMetadata.MultipleObjectsReturned:
            self.obsm = None        

    def observation_process(self) -> None:
        try:
            self.obsp, created = (
                ObservationProcess.objects.get_or_create(
                    process_reference=self.gld_dict.get(
                        self.prefix + "processReference", None
                    ),
                    measurement_instrument_type=self.gld_dict.get(
                        self.prefix + "MeasurementInstrumentType", None
                    ),
                    process_type="algoritme",  # Standard, only option
                    evaluation_procedure=self.gld_dict.get(
                        self.prefix + "EvaluationProcedure", None
                    ),
                    air_pressure_compensation_type=self.gld_dict.get(
                        self.prefix + "AirPressureCompensationType", None
                    ),
                )
            )
        except ObservationProcess.MultipleObjectsReturned:
            self.obsp = None

    def observation(self) -> None:
        start_time = str_to_datetime(
            self.gld_dict.get(self.prefix + "beginPosition", None)
        )
        end_time = str_to_datetime(
            self.gld_dict.get(self.prefix + "endPosition", None)
        )
        result_time = str_to_datetime(
            self.gld_dict.get(self.prefix + "timePosition", None)
        )

        self.obs, created = Observation.objects.update_or_create(
            groundwater_level_dossier=self.gld,
            observation_starttime=start_time,
            observation_endtime=end_time,
            defaults={                    
                "observation_metadata": self.obsm,
                "observation_process": self.obsp,
                "result_time": result_time,
                "up_to_date_in_bro": True,
            }
        )

    def measurement_metadata(self) -> None:
        self.mm = (
            MeasurementPointMetadata.objects.create(
                status_quality_control=self.gld_dict.get(
                    self.prefix + "point_qualifier_value", "onbekend"
                )[self.measurement_number],
                censor_reason=get_censor_reason(
                    self.gld_dict, self.prefix, self.measurement_number
                ),
            )
        )

    def measurement_tvp(self) -> None:
        calculated_value = _calculate_value(
            self.gld_dict.get(self.prefix + "point_value", None)[
                self.measurement_number
            ],
            self.gld_dict.get(self.prefix + "unit", None)[
                self.measurement_number
            ],
        )

        self.mtvp = MeasurementTvp.objects.update_or_create(
            observation=self.obs,
            measurement_time=str_to_datetime(
                self.gld_dict.get(
                    self.prefix + "point_time", [None]
                )[self.measurement_number]
            ),
            defaults={
                "field_value": self.gld_dict.get(
                    self.prefix + "point_value", None
                )[self.measurement_number],
                "field_value_unit": self.gld_dict.get(
                    self.prefix + "unit", None
                    )[self.measurement_number],
                "calculated_value": calculated_value,
                "measurement_point_metadata": self.mm,
            }
        )

    def reset_values(self):
        self.observation_number = 0
        self.measurement_count = 0
