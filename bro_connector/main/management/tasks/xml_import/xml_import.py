import datetime
import os
import xml.etree.ElementTree as ET
from string import punctuation, whitespace

import bro.models as bro_models
import gmw.models as gmw_models
from django.conf import settings
from django.contrib.gis.geos import Point
from django.db.models.signals import post_save
from gmw.signals import (
    on_save_groundwater_monitoring_tube_static,
    on_save_groundwater_monitoring_well_static,
)

from ..bro_handlers import GMWHandler as broGMWHandler
from .bro_handlers import GMWHandler as xmlGMWHandler

os.environ["PROJ_LIB"] = r"C:\OSGeo4W\share\proj"


def import_xml(file: str, path: str) -> tuple:
    file_path = os.path.join(path, file)

    # Read XML to detect type
    try:
        with open(file_path) as f:
            xml_data = f.read()
            root = ET.fromstring(xml_data)
    except Exception as e:
        return False, f"Failed to parse XML: {e}"

    # Detect type by looking for key elements
    if root.find(".//{*}GMW_Construction") is not None:
        gmw = xmlGMWHandler()
        id_key = "objectIdAccountableParty"
        gmw.get_data(file_path)
    elif (
        root.find(".//{*}GMW_PPO") is not None or root.find(".//{*}GMW_PO") is not None
    ):
        gmw = broGMWHandler()
        id_key = "deliveryAccountableParty"
        # For broGMWHandler, full_history is required; set False for file import
        gmw.get_data(id=None, full_history=False, file=file_path)
    else:
        return False, f"\n{file} is not a recognized GMW XML file."

    # Build dictionary
    gmw.root_data_to_dictionary()
    gmw_dict = gmw.dict

    # Select the correct ID field
    internal_id = gmw_dict.get(id_key, None)
    bro_id = gmw_dict.get("broId", None)

    # Check if already in DB
    try:
        exists = (
            gmw_models.GroundwaterMonitoringWellStatic.objects.filter(
                internal_id=internal_id
            ).exists()
            or gmw_models.GroundwaterMonitoringWellStatic.objects.filter(
                bro_id=bro_id
            ).exists()
            if bro_id is not None
            else False
        )

        if exists:
            message = f"\ninternal_id: {internal_id} or bro_id: {bro_id} is already in database."
            print(message)
            return False, message

    except gmw_models.GroundwaterMonitoringWellStatic.DoesNotExist:
        pass

    try:
        post_save.disconnect(
            on_save_groundwater_monitoring_well_static,
            sender=gmw_models.GroundwaterMonitoringWellStatic,
        )
        post_save.disconnect(
            on_save_groundwater_monitoring_tube_static,
            sender=gmw_models.GroundwaterMonitoringTubeStatic,
        )
        # Initialize and create objects
        ini = InitializeData(gmw_dict)
        ini.well()
        ini.well_dynamic()
        ini.event()

        for _ in range(gmw.number_of_tubes):
            ini.increment_tube_number()
            ini.filter()
            ini.filter_dynamic()
            for _ in range(int(gmw.number_of_geo_ohm_cables)):
                ini.increment_geo_ohm_number()
                ini.geo_ohm()
                for _ in range(int(gmw.number_of_electrodes)):
                    ini.increment_electrode_number()
                    ini.electrode()
                ini.reset_electrode_number()
            ini.reset_geo_ohm_number()

        gmw.reset_values()
        ini.reset_tube_number()

    finally:
        post_save.connect(
            on_save_groundwater_monitoring_well_static,
            sender=gmw_models.GroundwaterMonitoringWellStatic,
        )
        post_save.connect(
            on_save_groundwater_monitoring_tube_static,
            sender=gmw_models.GroundwaterMonitoringTubeStatic,
        )

    completed = True
    message = f"\nPut {ini.gmw_dict.get('broId', None)} en bijbehorende filters gemaakt aan de hand van XML."
    return completed, message


def get_sediment_sump_present(dict: dict, prefix: str) -> bool | None:
    aanwezig = dict.get(prefix + "sedimentSumpPresent", None)

    if aanwezig is not None:
        # Remove all unnecessary chars
        ignore = punctuation + whitespace
        aanwezig = aanwezig.translate(str.maketrans("", "", ignore))

    if aanwezig == "ja":
        return "ja"

    elif aanwezig == "nee":
        return "nee"

    else:
        return "onbekend"


def get_artesian_well_cap_present(dict: dict, prefix: str) -> bool | None:
    artesian = str(
        dict.get(prefix + "artesianWellCapPresent", None),
    )

    if artesian is not None:
        # Remove all unnecessary chars
        ignore = punctuation + whitespace
        artesian = artesian.translate(str.maketrans("", "", ignore))

    if artesian == "ja":
        return True

    elif artesian == "nee":
        return False

    else:
        return None


def get_float_item_or_none(item):
    if item is not None:
        return float(item)
    return item


class InitializeData:
    """
    Function that allow you to create initial data when reading data from the BRO.
    The xml converted to dictionary is read into the database.

    Should redesign this with XML.Etree
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

    def get_accountable_party(self) -> bro_models.Organisation | None:
        kvk_nummer = self.gmw_dict.get("deliveryAccountableParty", None)
        if kvk_nummer is None:
            return None
        if kvk_nummer.isdigit():
            organisation = bro_models.Organisation.objects.get_or_create(
                company_number=kvk_nummer
            )[0]
            organisation.save()
            return organisation
        else:
            organisation = bro_models.Organisation.objects.get_or_create(
                name=kvk_nummer
            )[0]
            organisation.save()
            return organisation

    def get_coordinates(self) -> Point:
        position = self.gmw_dict.get("pos_1", None)
        if position is not None:
            positions = position.split(" ")
            coords_field = Point(float(positions[0]), float(positions[1]))

        else:
            coords_field = Point()

        return coords_field

    def well(self):
        kwaliteits = self.gmw_dict.get("qualityRegime", None)

        construction_date = self.gmw_dict.get("construction_date", None)
        if construction_date is not None:
            construction_date = datetime.datetime.strptime(
                construction_date, "%Y-%m-%d"
            )

        self.meetpunt_instance = (
            gmw_models.GroundwaterMonitoringWellStatic.objects.create(
                bro_id=self.gmw_dict.get("broId", None),
                internal_id=self.gmw_dict.get("objectIdAccountableParty", None),
                delivery_accountable_party=self.get_accountable_party(),
                construction_standard=self.gmw_dict.get("constructionStandard", None),
                coordinates=self.get_coordinates(),
                delivery_context=self.gmw_dict.get("deliveryContext", None),
                horizontal_positioning_method=self.gmw_dict.get(
                    "horizontalPositioningMethod", None
                ),
                initial_function=self.gmw_dict.get("initialFunction", None),
                nitg_code=self.gmw_dict.get("nitgCode", None),
                olga_code=self.gmw_dict.get("olgaCode", None),
                quality_regime=kwaliteits,
                reference_system=self.gmw_dict.get("CRS", "rd"),
                well_offset=self.gmw_dict.get("offset", None),
                local_vertical_reference_point=self.gmw_dict.get(
                    "localVerticalReferencePoint", None
                ),
                well_code=self.gmw_dict.get("wellCode", None),
                vertical_datum=self.gmw_dict.get("verticalDatum", None),
                last_horizontal_positioning_date=construction_date,
                construction_coordinates=self.get_coordinates(),
                deliver_gmw_to_bro=True,
                complete_bro=True,
                in_management=True
                if self.gmw_dict.get("deliveryAccountableParty", None)
                == settings.KVK_USER
                else False,
            )
        )

        self.meetpunt_instance.save()

    def event(self):
        self.onderhoudsmoment_instance = gmw_models.Event.objects.create(
            event_name="constructie",
            groundwater_monitoring_well_static=self.meetpunt_instance,
            groundwater_monitoring_well_dynamic=self.meetpuntgeschiedenis_instance,
            event_date=self.meetpunt_instance.last_horizontal_positioning_date,
            delivered_to_bro=False,
        )

    def well_dynamic(self):
        self.meetpuntgeschiedenis_instance = (
            gmw_models.GroundwaterMonitoringWellDynamic.objects.create(
                groundwater_monitoring_well_static=self.meetpunt_instance,
                date_from=self.meetpunt_instance.last_horizontal_positioning_date,
                owner=self.gmw_dict.get("owner", None),
                ground_level_stable=self.gmw_dict.get("groundLevelStable", None),
                well_stability=self.gmw_dict.get("wellStability", None),
                ground_level_position=self.gmw_dict.get("groundLevelPosition", None),
                ground_level_positioning_method=self.gmw_dict.get(
                    "groundLevelPositioningMethod", None
                ),
                well_head_protector=self.gmw_dict.get("wellHeadProtector", None),
            )
        )

        print(self.meetpuntgeschiedenis_instance)
        self.meetpuntgeschiedenis_instance.save()

    def filter(self):
        zandvang_aanwezig = get_sediment_sump_present(self.gmw_dict, self.prefix)
        arthesisch_water_aanwezig = get_artesian_well_cap_present(
            self.gmw_dict, self.prefix
        )

        self.filter_instance = gmw_models.GroundwaterMonitoringTubeStatic.objects.create(
            groundwater_monitoring_well_static=self.meetpunt_instance,
            artesian_well_cap_present=arthesisch_water_aanwezig,
            screen_length=float(self.gmw_dict.get(self.prefix + "screenLength", None)),
            sediment_sump_length=self.gmw_dict.get(
                self.prefix + "sedimentSumpLength", None
            ),  # not in XML --> might be because sediment sump not present, if else statement.
            sediment_sump_present=zandvang_aanwezig,
            sock_material=self.gmw_dict.get(self.prefix + "sockMaterial", None),
            tube_material=self.gmw_dict.get(self.prefix + "tubeMaterial", None),
            tube_number=int(self.gmw_dict.get(self.prefix + "tubeNumber", None)),
            tube_type=self.gmw_dict.get(self.prefix + "tubeType", None),
        )
        self.filter_instance.save()

    def filter_dynamic(self):
        self.filtergeschiedenis_instance = (
            gmw_models.GroundwaterMonitoringTubeDynamic.objects.create(
                groundwater_monitoring_tube_static=self.filter_instance,
                date_from=self.meetpunt_instance.last_horizontal_positioning_date,
                tube_packing_material=self.gmw_dict.get(
                    self.prefix + "tubePackingMaterial", None
                ),
                glue=self.gmw_dict.get(self.prefix + "glue", None),
                inserted_part_diameter=self.gmw_dict.get(
                    self.prefix + "insertedPartDiameter", None
                ),
                inserted_part_length=self.gmw_dict.get(
                    self.prefix + "insertedPartLength", None
                ),
                inserted_part_material=self.gmw_dict.get(
                    self.prefix + "insertedPartMaterial", None
                ),
                plain_tube_part_length=self.gmw_dict.get(
                    self.prefix + "plainTubePartLength", None
                ),
                tube_status=self.gmw_dict.get(self.prefix + "tubeStatus", None),
                tube_top_diameter=get_float_item_or_none(
                    self.gmw_dict.get(self.prefix + "tubeTopDiameter", None)
                ),
                tube_top_position=self.gmw_dict.get(
                    self.prefix + "tubeTopPosition", None
                ),
                tube_top_positioning_method=self.gmw_dict.get(
                    self.prefix + "tubeTopPositioningMethod", None
                ),
                variable_diameter=self.gmw_dict.get(
                    self.prefix + "variableDiameter", None
                ),
            )
        )
        self.filtergeschiedenis_instance.save()

        self.onderhoudsmoment_instance.groundwater_monitoring_tube_dynamic.add(
            self.filtergeschiedenis_instance
        )

    def geo_ohm(self):
        """
        Maak een geo ohm kabel vanuit de xml waardes.
        """
        self.geoc = gmw_models.GeoOhmCable.objects.create(
            groundwater_monitoring_tube_static=self.filter_instance,
            cable_number=(self.gmw_dict.get(self.prefix + "cableNumber", None)),
        )
        self.geoc.save()

    def electrode(self):
        """
        Maak een elektrode gebaseerd op de waardes uit de xml.
        """
        electrode = gmw_models.Electrode.objects.create(
            geo_ohmkabel=self.geoc,
            electrode_number=self.gmw_dict.get(self.prefix + "electrodeNumber", None),
            electrode_status=self.gmw_dict.get(self.prefix + "electrodeStatus", None),
            electrode_packing_material=self.gmw_dict.get(
                self.prefix + "electrodePackingMaterial", None
            ),
            elektrodepositie=self.gmw_dict.get(self.prefix + "electrodePosition", None),
        )
        electrode.save()

        self.onderhoudsmoment_instance.electrodes.add(electrode)
