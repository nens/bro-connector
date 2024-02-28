from ..tasks.bro_handlers import GMWHandler
from ..tasks.kvk_handler import DataRetrieverKVK
from ..tasks.progressor import Progress
from ..tasks import events_handler
import reversion
import datetime

from gmw.models import (
    GroundwaterMonitoringWellStatic,
    GroundwaterMonitoringWellDynamic,
    GroundwaterMonitoringTubeDynamic,
    GroundwaterMonitoringTubeStatic,
    GeoOhmCable,
    ElectrodeDynamic,
    ElectrodeStatic,
    Instantie,
)

# BBOX VALUES ZEELAND
XMIN = 10000
XMAX = 80000
YMIN = 355000
YMAX = 420000


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


def run(kvk_number=None, csv_file=None, bro_type: str = "gmw"):
    progressor = Progress()
    gmw = GMWHandler()

    if kvk_number != None:
        DR = DataRetrieverKVK(kvk_number)
        DR.request_bro_ids(bro_type)
        DR.get_ids_kvk()
        gmw_ids = DR.gmw_ids
        gmw_ids_ini_count = len(gmw_ids)

    print(f"{gmw_ids_ini_count} bro ids found for organisation.")

    gmw_ids_count = len(gmw_ids)
    progressor.calibrate(gmw_ids, 25)

    # Import the well data
    for id in range(gmw_ids_count):
        gmw.get_data(gmw_ids[id], True)
        gmw.root_data_to_dictionary()
        gmw_dict = gmw.dict

        # For now don't handle deregistered GMWs
        if gmw_dict.get("deregistered", None) == "ja":
            continue

        # Invullen initiële waarden.
        ini = InitializeData(gmw_dict)
        ini.well_static()
        gmws = ini.gmws

        if not within_bbox(gmws.coordinates):
            gmws.delete()
            gmw.reset_values()
            ini.reset_tube_number()
            progressor.next()
            progressor.progress()
            continue

        ini.well_dynamic()

        try:
            for tube_number in range(gmw.number_of_tubes):
                ini.increment_tube_number()
                ini.tube_static()
                ini.tube_dynamic()

                try:
                    for geo_ohm_cable in range(int(ini.gmts.number_of_geo_ohm_cables)):
                        ini.increment_geo_ohm_number()
                        ini.geo_ohm()

                        for electrode in range(int(gmw.number_of_electrodes)):
                            ini.increment_electrode_number()
                            ini.electrode_static()
                            ini.electrode_dynamic()

                        ini.reset_electrode_number()
                    ini.reset_geo_ohm_number()
                except:
                    raise Exception(f"Failed, {gmw_dict}")
        except:
            raise Exception(f"Failed, {gmw_dict}")

        construction_event = events_handler.create_construction_event(gmw_dict, gmws)

        # Update based on the events
        for nr in range(int(gmw.number_of_events)):
            print(gmw.dict)
            updater = events_handler.Updater(gmw.dict, gmws)
            updater.intermediate_events()

        gmw.reset_values()
        ini.reset_tube_number()
        progressor.next()
        progressor.progress()


def get_or_create_instantie(instantie: str):
    if instantie is None:
        return (None, False)
    if instantie.isdigit():
        return Instantie.objects.get_or_create(company_number=instantie)
    else:
        return Instantie.objects.get_or_create(name=instantie)


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
        with reversion.create_revision():
            self.gmws, created = (
                GroundwaterMonitoringWellStatic.objects.update_or_create(
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
                        "monitoring_pdok_id": self.gmw_dict.get(
                            "monitoringPdokId", None
                        ),
                        "nitg_code": self.gmw_dict.get("nitgCode", None),
                        "well_offset": self.gmw_dict.get("offset", None),
                        "olga_code": self.gmw_dict.get("olgaCode", None),
                        "quality_regime": self.gmw_dict.get("qualityRegime", None),
                        "reference_system": self.gmw_dict.get("referenceSystem", None),
                        "registration_object_type": self.gmw_dict.get(
                            "registrationStatus", None
                        ),
                        "request_reference": self.gmw_dict.get(
                            "requestReference", None
                        ),
                        "under_privilege": self.gmw_dict.get("underReview", None),
                        "vertical_datum": self.gmw_dict.get("verticalDatum", None),
                        "well_code": self.gmw_dict.get("wellCode", None),
                        "deliver_gmw_to_bro": True,
                    },
                )
            )  # -> Is soms ook niet gedaan, dus nvt? Maar moet datum opgeven...)

            reversion.set_comment(
                f"Updated from BRO-database({datetime.datetime.now().astimezone()})"
            )

        if str(self.gmws.delivery_accountable_party.company_number) == "20168636":
            self.gmws.in_management = True
        else:
            self.gmws.in_management = False

        self.gmws.save()

    def well_dynamic(self):
        dynamic = GroundwaterMonitoringWellDynamic.objects.filter(
            groundwater_monitoring_well_static=self.gmws
        ).first()

        if dynamic:
            with reversion.create_revision():
                dynamic.ground_level_position = self.gmw_dict.get(
                    "groundLevelPosition", None
                )
                dynamic.ground_level_positioning_method = self.gmw_dict.get(
                    "groundLevelPositioningMethod", None
                )
                dynamic.ground_level_stable = self.gmw_dict.get(
                    "groundLevelStable", None
                )
                dynamic.maintenance_responsible_party = get_or_create_instantie(
                    self.gmw_dict.get("maintenanceResponsibleParty", None)
                )[0]
                dynamic.owner = self.gmw_dict.get("owner", None)
                dynamic.well_head_protector = self.gmw_dict.get(
                    "wellHeadProtector", None
                )
                dynamic.well_stability = self.gmw_dict.get("wellStability", None)
                dynamic.save()
                reversion.set_comment(
                    f"Updated from BRO-database({datetime.datetime.now().astimezone()})"
                )
        else:
            self.gmwd = GroundwaterMonitoringWellDynamic.objects.create(
                groundwater_monitoring_well_static=self.gmws,
                defaults={
                    "deliver_gld_to_bro": self.gmw_dict.get("deliverGldToBro", False),
                    "ground_level_position": self.gmw_dict.get(
                        "groundLevelPosition", None
                    ),
                    "ground_level_positioning_method": self.gmw_dict.get(
                        "groundLevelPositioningMethod", None
                    ),
                    "ground_level_stable": self.gmw_dict.get("groundLevelStable", None),
                    "maintenance_responsible_party": get_or_create_instantie(
                        self.gmw_dict.get("maintenanceResponsibleParty", None)
                    )[0],
                    "number_of_standpipes": self.gmw_dict.get(
                        "numberOfStandpipes", None
                    ),
                    "owner": self.gmw_dict.get("owner", None),
                    "well_head_protector": self.gmw_dict.get("wellHeadProtector", None),
                    "well_stability": self.gmw_dict.get("wellStability", None),
                },
            )

    def tube_static(self):
        self.gmts, created = GroundwaterMonitoringTubeStatic.objects.update_or_create(
            groundwater_monitoring_well_static=self.gmws,
            defaults={
                "artesian_well_cap_present": self.gmw_dict.get(
                    self.prefix + "artesianWellCapPresent", None
                ),
                "deliver_gld_to_bro": self.gmw_dict.get(
                    self.prefix + "deliverGldToBro", False
                ),
                "number_of_geo_ohm_cables": self.gmw_dict.get(
                    self.prefix + "numberOfGeoOhmCables", None
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
                "tube_number": self.gmw_dict.get(self.prefix + "tubeNumber", None),
                "tube_type": self.gmw_dict.get(self.prefix + "tubeType", None),
            },
        )

    def tube_dynamic(self):
        dynamic = GroundwaterMonitoringTubeDynamic.objects.filter(
            groundwater_monitoring_tube_static=self.gmts
        ).first()

        if dynamic:
            with reversion.create_revision():
                dynamic.glue = self.gmw_dict.get(self.prefix + "glue", None)
                dynamic.inserted_part_diameter = self.gmw_dict.get(
                    self.prefix + "insertedPartDiameter", None
                )
                dynamic.inserted_part_length = self.gmw_dict.get(
                    self.prefix + "insertedPartLength", None
                )
                dynamic.inserted_part_material = self.gmw_dict.get(
                    self.prefix + "insertedPartMaterial", None
                )
                dynamic.plain_tube_part_length = self.gmw_dict.get(
                    self.prefix + "plainTubePartLength", None
                )
                dynamic.tube_packing_material = self.gmw_dict.get(
                    self.prefix + "tubePackingMaterial", None
                )
                dynamic.tube_status = self.gmw_dict.get(
                    self.prefix + "tubeStatus", None
                )
                dynamic.tube_top_diameter = self.gmw_dict.get(
                    self.prefix + "tubeTopDiameter", None
                )
                dynamic.tube_top_position = self.gmw_dict.get(
                    self.prefix + "tubeTopPosition", None
                )
                dynamic.tube_top_positioning_method = self.gmw_dict.get(
                    self.prefix + "tubeTopPositioningMethod", None
                )
                dynamic.variable_diameter = self.gmw_dict.get(
                    self.prefix + "variableDiameter", None
                )
                dynamic.save()
                reversion.set_comment(
                    f"Updated from BRO-database({datetime.datetime.now().astimezone()})"
                )

        else:
            self.gmtd, created = GroundwaterMonitoringTubeDynamic.objects.create(
                groundwater_monitoring_tube_static=self.gmts,
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
                    "tube_status": self.gmw_dict.get(self.prefix + "tubeStatus", None),
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

    def geo_ohm(self):
        self.geoc, created = GeoOhmCable.objects.update_or_create(
            groundwater_monitoring_tube_static=self.gmts,
            cable_number=self.gmw_dict.get(self.prefix + "cableNumber", None),
        )

    def electrode_static(self):
        self.eles, created = ElectrodeStatic.objects.update_or_create(
            geo_ohm_cable=self.geoc,
            defaults={
                "electrode_packing_material": self.gmw_dict.get(
                    self.prefix + "electrodePackingMaterial", None
                ),
                "electrode_position": self.gmw_dict.get(
                    self.prefix + "electrodePosition", None
                ),
            },
        )

    def electrode_dynamic(self):
        self.eled, created = ElectrodeDynamic.objects.update_or_create(
            electrode_static=self.eles,
            defaults={
                "electrode_number": self.gmw_dict.get(
                    self.prefix + "electrodeNumber", None
                ),
                "electrode_status": self.gmw_dict.get(
                    self.prefix + "electrodeStatus", None
                ),
            },
        )
