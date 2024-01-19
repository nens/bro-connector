from .bro_handlers import GMWHandler
from .progressor import Progress
import gmw.models as bro
import datetime
from string import punctuation, whitespace
import reversion


def import_xml(file: str, path: str) -> tuple:
    gmw = GMWHandler()
    progressor = Progress()
    file_path = f"{path}/{file}"
    gmw.get_data(file_path)
    gmw.root_data_to_dictionary()
    gmw_dict = gmw.dict

    if "GMW_Construction" not in gmw_dict:
        completed = False
        message = f"{file} is not a GMW xml file."
        return (completed, message)

    try:
        bro.GroundwaterMonitoringWellStatic.objects.get(
            request_reference=gmw_dict.get("requestReference", None),
        )
        message = f"request_reference: {gmw_dict.get('requestReference', None)} is already in database."
        completed = True
        print(message)
        return (completed, message)

    except bro.GroundwaterMonitoringWellStatic.DoesNotExist:
        pass

    # Invullen initiële waarden.
    ini = InitializeData(gmw_dict)

    # Eerst de put maken, want die zit in het onderhoudsmoment.
    ini.well()

    # Dan de putgeschiedenis.
    ini.well_dynamic()

    for tube_number in range(gmw.number_of_tubes):
        try:
            ini.increment_tube_number()
            ini.filter()
            ini.filter_dynamic()
        except:
            raise Exception(f"Failed while trying to create filter objects, {gmw_dict}")

        try:
            for geo_ohm_cable in range(int(gmw.number_of_geo_ohm_cables)):
                ini.increment_geo_ohm_number()
                ini.geo_ohm()

                for electrode in range(int(gmw.number_of_electrodes)):
                    ini.increment_electrode_number()
                    ini.electrode_static()
                    ini.electrode_dynamic()

                ini.reset_electrode_number()
            ini.reset_geo_ohm_number()
        except:
            raise Exception(
                f"Failed while trying to create geo_ohm_cable or electrode objects, {gmw_dict}"
            )

    # Dan het onderhoudsmoment, want die zit in de geschiedenissen.
    ini.event()

    gmw.reset_values()
    ini.reset_tube_number()
    progressor.next()
    progressor.progress()

    completed = True
    message = f"Put {ini.meetpunt_instance.request_reference} en bijbehorende filters gemaakt aan de hand van XML."
    return (completed, message)


def get_quality_regime(dict: dict) -> str:
    qr = dict.get("qualityRegime", None)

    if qr == "IMBRO":
        return "imbro"

    elif qr == "IMBRO/A":
        return "imbro_a"

    else:
        return None


def get_sediment_sump_present(dict: dict, prefix: str) -> bool | None:
    aanwezig = dict.get(prefix + "sedimentSumpPresent", None)

    if aanwezig is not None:
        # Remove all unnecessary chars
        ignore = punctuation + whitespace
        aanwezig = aanwezig.translate(str.maketrans("", "", ignore))

    if aanwezig == "ja":
        return True

    elif aanwezig == "nee":
        return False

    else:
        return None


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

    def well(self):
        kwaliteits = get_quality_regime(self.gmw_dict)

        construction_date = self.gmw_dict.get("construction_date", None)
        if construction_date is not None:
            construction_date = datetime.datetime.strptime(
                construction_date, "%Y-%m-%d"
            )

        self.meetpunt_instance = bro.GroundwaterMonitoringWellStatic.objects.create(
            bro_id=self.gmw_dict.get("broId", None),
            request_reference=self.gmw_dict.get("requestReference", None),
            delivery_accountable_party=self.gmw_dict.get(
                "deliveryAccountableParty", None
            ),
            construction_standard=self.gmw_dict.get("constructionStandard", None),
            coordinates=self.gmw_dict.get("pos_1", None),
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
            construction_coordinates=self.gmw_dict.get("pos_1", None),
        )

        self.meetpunt_instance.save()

    def event(self):
        self.onderhoudsmoment_instance = bro.Event.objects.create(
            event_name="constructie",
            groundwater_monitoring_well_static=self.meetpunt_instance,
            groundwater_monitoring_well_dynamic=self.meetpuntgeschiedenis_instance,
            groundwater_monitoring_well_tube_dynamic=self.filtergeschiedenis_instance,
            event_date=self.meetpunt_instance.last_horizontal_positioning_date,
            delivered_to_bro=False,
        )
        self.onderhoudsmoment_instance.save()

    def well_dynamic(self):
        print("dynamic")
        print(self.meetpunt_instance)
        self.meetpuntgeschiedenis_instance = (
            bro.GroundwaterMonitoringWellDynamic.objects.create(
                groundwater_monitoring_well=self.meetpunt_instance,
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

        self.filter_instance = bro.GroundwaterMonitoringTubeStatic.objects.create(
            groundwater_monitoring_well=self.meetpunt_instance,
            artesian_well_cap_present=arthesisch_water_aanwezig,
            screen_length=self.gmw_dict.get(self.prefix + "screenLength", None),
            sediment_sump_length=self.gmw_dict.get(
                self.prefix + "sedimentSumpLength", None
            ),  # not in XML --> might be because sediment sump not present, if else statement.
            sediment_sump_present=zandvang_aanwezig,
            sock_material=self.gmw_dict.get(self.prefix + "sockMaterial", None),
            tube_material=self.gmw_dict.get(self.prefix + "tubeMaterial", None),
            tube_number=self.gmw_dict.get(self.prefix + "tubeNumber", None),
            tube_type=self.gmw_dict.get(self.prefix + "tubeType", None),
            number_of_geo_ohm_cables=self.gmw_dict.get(
                self.prefix + "numberOfGeoOhmCables", None
            ),
        )
        self.filter_instance.save()

    def filter_dynamic(self):
        self.filtergeschiedenis_instance = (
            bro.GroundwaterMonitoringTubeDynamic.objects.create(
                groundwater_monitoring_tube_static=self.filter_instance,
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
                tube_top_diameter=self.gmw_dict.get(
                    self.prefix + "tubeTopDiameter", None
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

    def geo_ohm(self):
        """
        Maak een geo ohm kabel vanuit de xml waardes.
        """
        self.geoc = bro.GeoOhmCable.objects.create(
            groundwater_monitoring_tube_static=self.filter_instance,
            cable_number=(self.gmw_dict.get(self.prefix + "cableNumber", None)),
        )
        self.geoc.save()

    def electrode_static(self):
        """
        Maak een elektrode gebaseerd op de waardes uit de xml.
        """
        self.eles = bro.ElectrodeStatic.objects.create(
            geo_ohmkabel=self.geoc,
            electrode_packing_material=self.gmw_dict.get(
                self.prefix + "electrodePackingMaterial", None
            ),
            elektrodepositie=self.gmw_dict.get(self.prefix + "electrodePosition", None),
        )
        self.eles.save()

    def electrode_dynamic(self):
        """
        Maak een elektrode gebaseerd op de waardes uit de xml.
        """
        self.eled = bro.ElectrodeDynamic.objects.create(
            electrode_static=self.eles,
            electrode_number=self.gmw_dict.get(self.prefix + "electrodeNumber", None),
            electrode_status=self.gmw_dict.get(self.prefix + "electrodeStatus", None),
        )
        self.eled.save()
