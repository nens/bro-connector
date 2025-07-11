from ..tasks.bro_handlers import GMWHandler
from ..tasks.kvk_handler import DataRetrieverKVK
from .bbox_handler import DataRetrieverBBOX
from ..tasks.progressor import Progress
from ..tasks import events_handler
import reversion
import datetime
from django.conf import settings

from gmw.models import (
    GroundwaterMonitoringWellStatic,
    GroundwaterMonitoringWellDynamic,
    GroundwaterMonitoringTubeDynamic,
    GroundwaterMonitoringTubeStatic,
    GeoOhmCable,
    Electrode,
)
from bro.models import Organisation

import logging

logger = logging.getLogger(__name__)

# def within_bbox(coordinates) -> bool:
#     print(f"x: {coordinates.x}, y: {coordinates.y}")
#     if (
#         coordinates.x > settings.BBOX_SETTINGS["xmin"]
#         and coordinates.x < settings.BBOX_SETTINGS["xmax"]
#         and coordinates.y > settings.BBOX_SETTINGS["ymin"]
#         and coordinates.y < settings.BBOX_SETTINGS["ymax"]
#     ):
#         return True
#     return False


def run(kvk_number=None, csv_file=None, bro_type: str = "gmw", handler: str = "ogc"):
    progressor = Progress()
    gmw = GMWHandler()

    if kvk_number and handler == "kvk":
        DR = DataRetrieverKVK(kvk_number)
        DR.request_bro_ids(bro_type)
        DR.get_ids_kvk()
        gmw_ids = DR.gmw_ids
        gmw_ids_ini_count = len(gmw_ids)

    bbox_settings = settings.BBOX_SETTINGS
    bbox = settings.BBOX
    shp = settings.POLYGON_SHAPEFILE
    if bbox_settings["use_bbox"] and handler == "ogc":
        print("bbox settings: ", bbox_settings)
        DR = DataRetrieverBBOX(bbox)
        DR.request_bro_ids(bro_type)
        DR.filter_ids_kvk(kvk_number)
        DR.enforce_shapefile(shp, delete=False)
        DR.get_ids_ogc()
        gmw_ids = DR.gmw_ids
        gmw_ids_ini_count = len(gmw_ids)

    if gmw_ids_ini_count == 0:
        print(f"No IDs found for kvk: {kvk_number}.")
        return {"ids_found": gmw_ids_ini_count, "imported": gmw_ids_ini_count}

    print(f"{gmw_ids_ini_count} bro ids found for kvk {kvk_number}.")

    imported = 0
    gmw_ids_count = len(gmw_ids)
    progressor.calibrate(gmw_ids, 25)

    # Import the well data
    for id in range(gmw_ids_count):
        print("BRO id: ", gmw_ids[id])

        gmw.get_data(gmw_ids[id], True)
        if gmw.root is None:
            continue
        gmw.root_data_to_dictionary()
        gmw_dict = gmw.dict

        # For now don't handle deregistered GMWs
        if gmw_dict.get("deregistered", None) == "ja":
            continue

        # Invullen initiële waarden.
        ini = InitializeData(gmw_dict)
        ini.well_static()
        gmws = ini.gmws
        ini.well_dynamic()

        for tube_number in range(gmw.number_of_tubes):
            ini.increment_tube_number()
            ini.tube_static()
            ini.tube_dynamic()

            for geo_ohm_cable in range(int(ini.gmts.number_of_geo_ohm_cables)):
                ini.increment_geo_ohm_number()
                ini.geo_ohm()

                for electrode in range(int(gmw.number_of_electrodes)):
                    ini.increment_electrode_number()
                    ini.electrode()

                ini.reset_electrode_number()
            ini.reset_geo_ohm_number()

        events_handler.create_construction_event(gmw_dict, gmws)
        imported += 1
        # Update based on the events
        updater = events_handler.Updater(gmw.dict, gmws)
        for nr in range(int(gmw.number_of_events)):
            updater.intermediate_events()

        gmw.reset_values()
        ini.reset_tube_number()
        progressor.next()
        progressor.progress()

    info = {
        "ids_found": gmw_ids_count,
        "imported": imported,
    }
    print("run finished")
    return info


def get_or_create_instantie(instantie: str):
    if instantie is None:
        return (None, False)
    if instantie.isdigit():
        return Organisation.objects.get_or_create(company_number=instantie)
    else:
        return Organisation.objects.get_or_create(name=instantie)


def convert_event_date_str_to_datetime(event_date: str) -> datetime:
    try:
        date = datetime.datetime.strptime(event_date, "%Y-%m-%d")
    except ValueError:
        date = datetime.datetime.strptime(event_date, "%Y")
    except TypeError:
        date = datetime.datetime.strptime("1900-01-01", "%Y-%m-%d")

    return date


class InitializeData:
    """
    Function that allow you to create initial data when reading data from the BRO.
    The xml converted to dictionary is read into the database.
    """

    tube_number = 0
    geo_ohm_number = 0
    electrode_number = 0

    prefix = f"tube_{tube_number}_"

    def __init__(self, gmw_dict):
        self.gmw_dict = gmw_dict

    def reset_tube_number(self):
        self.tube_number = 0

    def reset_geo_ohm_number(self):
        self.geo_ohm_number = 0

    def reset_electrode_number(self):
        self.electrode_number = 0

    def increment_tube_number(self):
        self.tube_number = self.tube_number + 1
        self.prefix = f"tube_{self.tube_number}_"

    def increment_geo_ohm_number(self):
        self.geo_ohm_number = self.geo_ohm_number + 1
        self.prefix = f"tube_{self.tube_number}_geo_ohm_{str(self.geo_ohm_number)}_"

    def increment_electrode_number(self):
        self.electrode_number = self.electrode_number + 1
        self.prefix = f"tube_{self.tube_number}_geo_ohm_{str(self.geo_ohm_number)}_electrode_{str(self.electrode_number)}_"

    def well_static(self):
        if "construction_date" in self.gmw_dict:
            construction_date = self.gmw_dict["construction_date"]
            construction_date = datetime.datetime.strptime(
                construction_date, "%Y-%m-%d"
            )

        elif "construction_year" in self.gmw_dict:
            construction_date = self.gmw_dict["construction_year"]
            construction_date = datetime.datetime.strptime(construction_date, "%Y")

        else:
            construction_date = None

        with reversion.create_revision():
            (
                self.gmws,
                created,
            ) = GroundwaterMonitoringWellStatic.objects.update_or_create(
                bro_id=self.gmw_dict.get("broId", None),
                defaults={
                    "construction_standard": self.gmw_dict.get(
                        "constructionStandard", None
                    ),
                    "coordinates": f"POINT({self.gmw_dict.get('pos_1', None)})",
                    "delivery_accountable_party": get_or_create_instantie(
                        self.gmw_dict.get("deliveryAccountableParty", None)
                    )[0],
                    "delivery_context": self.gmw_dict.get("deliveryContext", None),
                    "delivery_responsible_party": get_or_create_instantie(
                        self.gmw_dict.get("deliveryResponsibleParty", None)
                    )[0],
                    "horizontal_positioning_method": self.gmw_dict.get(
                        "horizontalPositioningMethod", None
                    ),
                    "initial_function": self.gmw_dict.get("initialFunction", None),
                    "local_vertical_reference_point": self.gmw_dict.get(
                        "localVerticalReferencePoint", None
                    ),
                    "monitoring_pdok_id": self.gmw_dict.get("monitoringPdokId", None),
                    "nitg_code": self.gmw_dict.get("nitgCode", None),
                    "well_offset": self.gmw_dict.get("offset", None),
                    "olga_code": self.gmw_dict.get("olgaCode", None),
                    "quality_regime": self.gmw_dict.get("qualityRegime", None),
                    "reference_system": self.gmw_dict.get("referenceSystem", None),
                    "vertical_datum": self.gmw_dict.get("verticalDatum", None),
                    "construction_date": construction_date,
                    "well_code": self.gmw_dict.get("wellCode", None),
                    "deliver_gmw_to_bro": True,
                    "complete_bro": True,
                },
            )  # -> Is soms ook niet gedaan, dus nvt? Maar moet datum opgeven...)

            reversion.set_comment(
                f"Updated from BRO-database({datetime.datetime.now().astimezone()})"
            )

        if (
            str(self.gmws.delivery_accountable_party.company_number)
            == settings.KVK_USER
        ):
            self.gmws.in_management = True
        else:
            self.gmws.in_management = False

        self.gmws.save()

    def well_dynamic(self):
        if "construction_date" in self.gmw_dict:
            date = self.gmw_dict["construction_date"]

        elif "construction_year" in self.gmw_dict:
            date = self.gmw_dict["construction_year"]

        else:
            date = None

        date = convert_event_date_str_to_datetime(date)

        self.gmwd, created = GroundwaterMonitoringWellDynamic.objects.update_or_create(
            groundwater_monitoring_well_static=self.gmws,
            date_from=date,
            defaults={
                "ground_level_position": self.gmw_dict.get("groundLevelPosition", None),
                "ground_level_positioning_method": self.gmw_dict.get(
                    "groundLevelPositioningMethod", None
                ),
                "ground_level_stable": self.gmw_dict.get("groundLevelStable", None),
                "maintenance_responsible_party": get_or_create_instantie(
                    self.gmw_dict.get("maintenanceResponsibleParty", None)
                )[0],
                "owner": self.gmw_dict.get("owner", None),
                "well_head_protector": self.gmw_dict.get("wellHeadProtector", None),
                "well_stability": self.gmw_dict.get("wellStability", None),
            },
        )

    def tube_static(self):
        self.gmts, created = GroundwaterMonitoringTubeStatic.objects.update_or_create(
            groundwater_monitoring_well_static=self.gmws,
            tube_number=self.gmw_dict.get(self.prefix + "tubeNumber", None),
            defaults={
                "artesian_well_cap_present": self.gmw_dict.get(
                    self.prefix + "artesianWellCapPresent", None
                ),
                "deliver_gld_to_bro": self.gmw_dict.get(
                    self.prefix + "deliverGldToBro", False
                ),
                "screen_length": self.gmw_dict.get(self.prefix + "screenLength", None),
                "sediment_sump_length": self.gmw_dict.get(
                    self.prefix + "sedimentSumpLength", None
                ),
                "sediment_sump_present": self.gmw_dict.get(
                    self.prefix + "sedimentSumpPresent", None
                ),
                "sock_material": self.gmw_dict.get(self.prefix + "sockMaterial", None),
                "tube_material": self.gmw_dict.get(self.prefix + "tubeMaterial", None),
                "tube_type": self.gmw_dict.get(self.prefix + "tubeType", None),
            },
        )

    def tube_dynamic(self):
        try:
            self.gmtd, created = (
                GroundwaterMonitoringTubeDynamic.objects.update_or_create(
                    groundwater_monitoring_tube_static=self.gmts,
                    date_from=self.gmwd.date_from,
                    defaults={
                        "glue": self.gmw_dict.get(self.prefix + "glue", None),
                        "inserted_part_diameter": self.gmw_dict.get(
                            self.prefix + "insertedPartDiameter", None
                        ),
                        "inserted_part_length": self.gmw_dict.get(
                            self.prefix + "insertedPartLength", None
                        ),
                        "inserted_part_material": self.gmw_dict.get(
                            self.prefix + "insertedPartMaterial", None
                        ),
                        "plain_tube_part_length": self.gmw_dict.get(
                            self.prefix + "plainTubePartLength", None
                        ),
                        "tube_packing_material": self.gmw_dict.get(
                            self.prefix + "tubePackingMaterial", None
                        ),
                        "tube_status": self.gmw_dict.get(
                            self.prefix + "tubeStatus", None
                        ),
                        "tube_top_diameter": self.gmw_dict.get(
                            self.prefix + "tubeTopDiameter", None
                        ),
                        "tube_top_position": self.gmw_dict.get(
                            self.prefix + "tubeTopPosition", None
                        ),
                        "tube_top_positioning_method": self.gmw_dict.get(
                            self.prefix + "tubeTopPositioningMethod", None
                        ),
                        "variable_diameter": self.gmw_dict.get(
                            self.prefix + "variableDiameter", None
                        ),
                    },
                )
            )
        except:
            print(
                "Raised a MultipleObjectsReturned exception. Now taking the dynamic tube with the highest primary key."
            )
            self.gmtd = (
                GroundwaterMonitoringTubeDynamic.objects.filter(
                    groundwater_monitoring_tube_static=self.gmts,
                    date_from=self.gmwd.date_from,
                )
                .order_by("-pk")
                .last()
            )

    def geo_ohm(self):
        self.geoc, created = GeoOhmCable.objects.update_or_create(
            groundwater_monitoring_tube_static=self.gmts,
            cable_number=self.gmw_dict.get(self.prefix + "cableNumber", None),
        )

    def electrode(self):
        Electrode.objects.update_or_create(
            geo_ohm_cable=self.geoc,
            electrode_number=self.gmw_dict.get(self.prefix + "electrodeNumber", None),
            defaults={
                "electrode_packing_material": self.gmw_dict.get(
                    self.prefix + "electrodePackingMaterial", None
                ),
                "electrode_position": self.gmw_dict.get(
                    self.prefix + "electrodePosition", None
                ),
                "electrode_status": self.gmw_dict.get(
                    self.prefix + "electrodeStatus", None
                ),
            },
        )
