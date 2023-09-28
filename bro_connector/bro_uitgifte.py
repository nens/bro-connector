import requests
import requests.auth
import xml.etree.ElementTree as ET
import psycopg2
import psycopg2.sql
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from django.utils import timezone
from psycopg2.extras import execute_values

from gmw_aanlevering.models import (
    GroundwaterMonitoringWellStatic,
    GroundwaterMonitoringWellDynamic,
    GroundwaterMonitoringTubesStatic,
    GroundwaterMonitoringTubesDynamic,
    GeoOhmCable,
    ElectrodeStatic,
    ElectrodeDynamic,
    Event,
)

DB_NAME = "grondwatermeetnet"
DB_USER = "postgres"
DB_PASS = "!StNS!2023"
DB_HOST = "localhost"
DB_PORT = "5432"


# FORMULAS USED IN HISTORIE_OPHALEN COMMAND DJANGO ZEELAND
class Progress:
    start = 0
    end   = 0
    update_interval = 25
    timer = start

    def calibrate(self, ids, update_interval):
        self.end = len(ids)
        self.update_interval = update_interval

    def progress(self):
        if self.timer % self.update_interval == 0:
            print(f"{round((self.timer / self.end)*100, 2)}% completed.")

    def next(self):
        self.timer = self.timer + 1

class DataRetrieverKVK(object):
    def __init__(self, kvk_nummer):
        self.kvk_nummer = kvk_nummer
        self.bro_ids = []

    def request_bro_ids(self):
        basis_url = "https://publiek.broservices.nl"
        kvk_verzoek = requests.get(
            basis_url + "/gm/gmw/v1/bro-ids?bronhouder=" + str(self.kvk_nummer)
        )
        self.bro_ids = json.loads(kvk_verzoek.text)["broIds"]

    def get_ids_kvk(self):
        self.gmw_ids = []
        self.other_ids = []

        self.request_bro_ids()

        for id in self.bro_ids:
            if id.startswith("GMW"):
                self.gmw_ids.append(id)
            else:
                self.other_ids.append(id)

class GMWHandler:
    number_of_events = 0
    number_of_tubes  = 0
    dict = {}

    def __init__(self):
        pass

    def get_data(self, id: str, full_history: bool):
        basis_url = "https://publiek.broservices.nl/gm/gmw/v1/objects/"

        if full_history:
            fh = "ja"
        else:
            fh = "nee"

        gmw_verzoek = requests.get("{}{}?fullHistory={}".format(basis_url, id, fh))

        self.root = ET.fromstring(gmw_verzoek.content)


    def make_dict(self):
        tags = []
        values = []
        prefix = ""

        for element in self.root.iter():
            tag = element.tag
            split = tag.split("}")

            if split[1] == "wellConstructionDate":
                prefix = "construction_"

            elif split[1] == "intermediateEvent":
                self.number_of_events = self.number_of_events + 1
                prefix = "event_" + str(self.number_of_events) + "_"

            elif split[1] == "wellRemovalDate":
                prefix = "removal_"

            elif split[1] == "monitoringTube":
                self.number_of_tubes = self.number_of_tubes + 1
                prefix = "tube_" + str(self.number_of_tubes) + "_"

            tag = str(prefix) + split[1]

            tags.append(tag)
            values.append(element.text)

        self.dict = dict(zip(tags, values))

def slice(sourcedict, string):
    newdict = {}
    for key in sourcedict.keys():
        if key.startswith(string):
            newdict[key.split(string)[1]] = sourcedict[key]
    return newdict

# class Updater:
def well_dynamic(gmwd, updates_dict):
    gmwd.number_of_standpipes = updates_dict.get('numberOfStandpipes', gmwd.number_of_standpipes)
    gmwd.ground_level_stable = updates_dict.get('groundLevelStable',  gmwd.ground_level_stable)
    gmwd.well_stability = updates_dict.get('wellStability', gmwd.well_stability)
    gmwd.owner = updates_dict.get('owner', gmwd.owner)
    gmwd.maintenance_responsible_party = updates_dict.get('maintenanceResponsibleParty', gmwd.maintenance_responsible_party)
    gmwd.well_head_protector = updates_dict.get('wellHeadProtector', gmwd.well_head_protector)
    gmwd.deliver_gld_to_bro = updates_dict.get('deliverGldToBro', gmwd.deliver_gld_to_bro)
    gmwd.ground_level_position = updates_dict.get('groundLevelPosition', gmwd.ground_level_position)
    gmwd.ground_level_positioning_method = updates_dict.get('groundLevelPositioningMethod', gmwd.ground_level_positioning_method)
    return gmwd

def tube_dynamic(gmtd, updates_dict):
    gmtd.tube_top_diameter = updates_dict.get('tubeTopDiameter', gmtd.tube_top_diameter)
    gmtd.variable_diameter = updates_dict.get('variableDiameter',  gmtd.variable_diameter)
    gmtd.tube_status = updates_dict.get('tubeStatus', gmtd.tube_status)
    gmtd.tube_top_position = updates_dict.get('tubeTopPosition', gmtd.tube_top_position)
    gmtd.tube_top_positioning_method = updates_dict.get('tubeTopPositioningMethod', gmtd.tube_top_positioning_method)
    gmtd.tube_packing_material = updates_dict.get('tubePackingMaterial', gmtd.tube_packing_material)
    gmtd.glue = updates_dict.get('glue', gmtd.glue)
    gmtd.plain_tube_part_length = updates_dict.get('plainTubePartLength', gmtd.plain_tube_part_length)
    gmtd.inserted_part_diameter = updates_dict.get('insertedPartDiameter', gmtd.inserted_part_diameter)
    gmtd.inserted_part_length = updates_dict.get('insertedPartLength', gmtd.inserted_part_length)
    gmtd.inserted_part_material = updates_dict.get('insertedPartMaterial', gmtd.inserted_part_material)
    return gmtd

def electrode_dynamic(eled, updates_dict):
    eled.electrode_number = updates_dict.get('electrodeNumber', eled.electrode_number)
    eled.electrode_status = updates_dict.get('electrodeStatus', eled.electrode_status)
    return eled

def get_mytimezone_date(original_datetime):
        try:
            new_datetime = datetime.strptime(original_datetime, '%Y-%m-%d')
            tz = timezone.get_current_timezone()
            timezone_datetime = timezone.make_aware(new_datetime, tz, True)
        except:
            timezone_datetime = None
        return timezone_datetime

class InitializeData:

    tube_number = 0
    prefix = f"tube_{tube_number}_"

    def __init__(self, gmw_dict):
        self.gmw_dict = gmw_dict

    def increment_tube_number(self):
        self.tube_number = self.tube_number + 1
        self.prefix =f"tube_{self.tube_number}_"

    def well_static(self):
        self.gmws = GroundwaterMonitoringWellStatic.objects.create(
                    bro_id=self.gmw_dict.get("broId", None),
                    construction_standard=self.gmw_dict.get("constructionStandard", None),
                    coordinates=(
                        f"POINT({self.gmw_dict.get('pos', None)})"
                    ),  # -> Has a delivered location and a standardized location, which do we want? Used std for now
                    delivery_accountable_party=self.gmw_dict.get(
                        "deliveryAccountableParty", None
                    ),
                    delivery_context=self.gmw_dict.get("deliveryContext", None),
                    delivery_responsible_party=self.gmw_dict.get(
                        "deliveryResponsibleParty", None
                    ),  # Not in XML ??? -> Same as delivery or is it our id or Zeeland ???
                    horizontal_positioning_method=self.gmw_dict.get(
                        "horizontalPositioningMethod", None
                    ),
                    initial_function=self.gmw_dict.get("initialFunction", None),
                    local_vertical_reference_point=self.gmw_dict.get(
                        "localVerticalReferencePoint", None
                    ),
                    monitoring_pdok_id=self.gmw_dict.get(
                        "monitoringPdokId", None
                    ),  # Cannot find in XML
                    nitg_code=self.gmw_dict.get("nitgCode", None),
                    well_offset=self.gmw_dict.get("offset", None),
                    olga_code=self.gmw_dict.get("olgaCode", None),  # -> Cannot find in XML
                    quality_regime=self.gmw_dict.get("qualityRegime", None),
                    reference_system=self.gmw_dict.get(
                        "referenceSystem", None
                    ),  # -> Cannot find in XML, but the reference vertical is NAP?
                    registration_object_type=self.gmw_dict.get(
                        "registrationStatus", None
                    ),  # -> registration status? Otherwise cannot find.
                    request_reference=self.gmw_dict.get("requestReference", None),
                    under_privilege=self.gmw_dict.get(
                        "underReview", None
                    ),  # -> Not in XML, maybe under review?
                    vertical_datum=self.gmw_dict.get("verticalDatum", None),
                    well_code=self.gmw_dict.get("wellCode", None),
                    ## Have to readjust the methodology slightly because if there are multiple events they cannot all have the same names and dates...
                )  # -> Is soms ook niet gedaan, dus nvt? Maar moet datum opgeven...)\
        self.gmws.save()

    def well_dynamic(self):
        self.gmwd = GroundwaterMonitoringWellDynamic.objects.create(
                    groundwater_monitoring_well=self.gmws,
                    deliver_gld_to_bro=self.gmw_dict.get(
                        "deliverGldToBro", False
                    ),  # std True because we are collecting data from BRO
                    ground_level_position=self.gmw_dict.get("groundLevelPosition", None),
                    ground_level_positioning_method=self.gmw_dict.get(
                        "groundLevelPositioningMethod", None
                    ),
                    ground_level_stable=self.gmw_dict.get("groundLevelStable", None),
                    maintenance_responsible_party=self.gmw_dict.get(
                        "maintenanceResponsibleParty", None
                    ),  # not in XML
                    number_of_standpipes=self.gmw_dict.get(
                        "numberOfStandpipes", None
                    ),  # not in XML
                    owner=self.gmw_dict.get("owner", None),
                    well_head_protector=self.gmw_dict.get("wellHeadProtector", None),
                    well_stability=self.gmw_dict.get("wellStability", None),
                )  # not in XML)
        self.gmwd.save()

    def tube_static(self):
        self.gmts = GroundwaterMonitoringTubesStatic.objects.create(
                            groundwater_monitoring_well=self.gmws,
                            artesian_well_cap_present=self.gmw_dict.get(
                                self.prefix + "artesianWellCapPresent", None
                            ),
                            deliver_gld_to_bro=self.gmw_dict.get(
                                self.prefix + "deliverGldToBro", False
                            ),  # std True because we are collecting data from BRO
                            number_of_geo_ohm_cables=self.gmw_dict.get(
                                self.prefix + "numberOfGeoOhmCables", None
                            ),
                            screen_length=self.gmw_dict.get(
                                self.prefix + "screenLength", None
                            ),
                            sediment_sump_length=self.gmw_dict.get(
                                self.prefix + "sedimentSumpLength", None
                            ),  # not in XML --> might be because sediment sump not present, if else statement.
                            sediment_sump_present=self.gmw_dict.get(
                                self.prefix + "sedimentSumpPresent", None
                            ),
                            sock_material=self.gmw_dict.get(
                                self.prefix + "sockMaterial", None
                            ),
                            tube_material=self.gmw_dict.get(
                                self.prefix + "tubeMaterial", None
                            ),
                            tube_number=self.gmw_dict.get(self.prefix + "tubeNumber", None),
                            tube_type=self.gmw_dict.get(self.prefix + "tubeType", None),
                        )
        self.gmts.save()

    def tube_dynamic(self):
        self.gmtd = GroundwaterMonitoringTubesDynamic.objects.create(
                            groundwater_monitoring_tube_static=self.gmts,
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
                            tube_packing_material=self.gmw_dict.get(
                                self.prefix + "tubePackingMaterial", None
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
        self.gmtd.save()

    def geo_ohm(self):
        self.geoc = GeoOhmCable.objects.create(
                                    groundwater_monitoring_tube_static=self.gmts,
                                    cable_number=self.gmw_dict.get(self.prefix + "cableNumber", None),
                                )  # not in XML -> 0 cables)
        self.geoc.save()

    def electrode_static(self):
        geo_ohm_cable = get_geo_ohm_cable(self.gmws)
        self.eles = ElectrodeStatic.objects.create(
                                    geo_ohm_cable=geo_ohm_cable,
                                    electrode_packing_material=self.gmw_dict.get(
                                        self.prefix + "electrodePackingMaterial", None
                                    ),
                                    electrode_position=self.gmw_dict.get(
                                        self.prefix + "electrodePosition", None
                                    ),
                                )
        self.eles.save()

    def electrode_dynamic(self):
        electrode_static = get_electrode_static(self.gmws)
        self.eled = ElectrodeDynamic.objects.create(
                                    electrode_static=electrode_static,
                                    electrode_number=self.gmw_dict.get(
                                        self.prefix + "electrodeNumber", None
                                    ),
                                    electrode_status=self.gmw_dict.get(
                                        self.prefix + "electrodeStatus", None
                                    ),
                                )
        self.eled.save()

def get_geo_ohm_cable(groundwater_monitoring_well_static):
    geoc = GeoOhmCable.objects.get(groundwater_monitoring_well = groundwater_monitoring_well_static)
    return geoc




def get_construction_event(gmw_dict, groundwater_monitoring_well_static):
    event = Event.objects.create(
                event_name = "construction",
                event_date = get_mytimezone_date(gmw_dict.get(
                    "construction_date", None
                )),
                groundwater_monitoring_well_static = groundwater_monitoring_well_static,
                groundwater_monitoring_well_dynamic = GroundwaterMonitoringWellDynamic.objects.filter(
                    groundwater_monitoring_well = groundwater_monitoring_well_static).first(),
            )
    event.save()

def get_electrode_static(groundwater_monitoring_well):
    eles_id = ElectrodeStatic.objects.filter(
        geo_ohm_cable = GeoOhmCable.objects.filter(
            groundwater_monitoring_tube_static = GroundwaterMonitoringTubesStatic.objects.get(
                groundwater_monitoring_well = groundwater_monitoring_well
            )
        )
    )
    return eles_id

def get_tube_static(groundwater_monitoring_well, tube_number):
    gmts_id = GroundwaterMonitoringTubesStatic.objects.get(
        groundwater_monitoring_well = groundwater_monitoring_well,
        tube_number = tube_number
    )
    return gmts_id

def get_tube_dynamic_history(well_static, updates):
    try:
        # Find which filter needs to be adjusted
        new_gmts = GroundwaterMonitoringTubesStatic.objects.get(
                tube_number = updates['tubeNumber'],
                groundwater_monitoring_well = well_static,
                )
        
        # Clone row and make new primary key with save
        new_gmtds = GroundwaterMonitoringTubesDynamic.objects.filter(
            groundwater_monitoring_tube_static = new_gmts)
    except:
        raise Exception("failed to create new tube: ", updates)
    
    return new_gmtds

class Updater:
    event_number = 1
    prefix = f"event_{str(event_number)}_"
    event_updates = []
    event = None

    def __init__(self, gmw_dict, groundwater_monitoring_well):
        self.gmw_dict = gmw_dict
        self.groundwater_monitoring_well = groundwater_monitoring_well
    
    def increment_event(self):
        self.event_number = self.event_number + 1
        self.prefix = f"event_{str(self.event_number)}_"

    def read_updates(self):
        self.event_updates = slice(self.gmw_dict, self.prefix)

    def create_base(self):
        try:
            self.event = Event.objects.create(
                event_name = self.event_updates['eventName'],
                event_date = get_mytimezone_date(self.event_updates['date']),
                groundwater_monitoring_well_static = self.groundwater_monitoring_well,
            )
        except:
            try:
                self.event = Event.objects.create(
                    event_name = self.event_updates['eventName'],
                    event_date = get_mytimezone_date(str(self.event_updates['year']) + "-01-01"),
                    groundwater_monitoring_well_static = self.groundwater_monitoring_well,
                )
            except:
                print(self.event_updates)
                exit()
    
    def intermediate_events(self):
        # Create a base event
        self.read_updates()
        self.create_base()

        # Read the update data
        print("test", self.event_updates)

        # Update tables accordingly
        TableUpdater.fill(self.groundwater_monitoring_well, self.event, self.event_updates)
        self.increment_event()


class TableUpdater(Updater):
    def fill(well_static, event, updates):
        if "wellData" in updates:
            TableUpdater.well_data(well_static, event, updates)
        
        elif "tubeData" in updates:
            TableUpdater.tube_data(well_static, event, updates)

        elif "electrodeData" in updates:
            TableUpdater.electrode_data(well_static, event, updates)

        else:
            raise Exception(f"No correct data found: {updates}")

    def tube_data(well_static, event, updates):
        try:
            gmtd_history = get_tube_dynamic_history(well_static, updates)
            
            # This assumes the gmwds are sorted based on creation date.
            if len(gmtd_history) == 1:
                new_gmtd = gmtd_history.first()
                new_gmtd.groundwater_monitoring_tube_dynamic_id = None
            
            elif len(gmtd_history) > 1:
                new_gmtd = gmtd_history.last()
                new_gmtd.groundwater_monitoring_tube_dynamic_id = None
            
            else:
                raise Exception("No Groundwater Monitoring Tube Dynamic Tables found for this GMT: ", get_tube_static(well_static, updates['tubeNumber']))

            # Check what has to be changed
            print("works so far: ", new_gmtd, "\n", updates)
            new_gmtd = tube_dynamic(new_gmtd, updates)

            # Save and add new key to event
            new_gmtd.save()
            
            #  Add to the event
            event.groundwater_monitoring_well_tube_dynamic = new_gmtd
            event.save()

        except:
            raise Exception(f"Failed to update tube data: {updates}")


    def electrode_data(well_static, event, updates):
        try:
            # Clone row and make new primary key with save
            new_eleds = ElectrodeDynamic.objects.filter(
                electrode_static = get_electrode_static(well_static))
            
            # This assumes the gmwds are sorted based on creation date.
            if len(new_eleds) == 1:
                new_eled = new_eleds.first()
                new_eled.electrode_dynamic_id = None
            
            elif len(new_eleds) > 1:
                new_eled = new_eleds.last()
                new_eled.electrode_dynamic_id = None
            
            else:
                raise Exception("No Groundwater Monitoring Tube Dynamic Tables found for this GMT: ", get_tube_static(well_static, updates['tubeNumber']))

            # Check what has to be changed
            new_eled = electrode_dynamic(new_eled, updates)

            # Save and add new key to event
            new_eled.save()

            # Add to the event.
            event.electrode_dynamic = new_eled
            event.groundwater_monitoring_well_static = well_static
            event.save()

        except:
            raise Exception(f"Failed to update tube data: {updates}")

    def well_data(well_static, event, updates):
        try:
            # Clone row and make new primary key with save
            new_gmwds = GroundwaterMonitoringWellDynamic.objects.filter(
                groundwater_monitoring_well = well_static)
            
            # This assumes the gmwds are sorted based on creation date.
            if len(new_gmwds) == 1:
                new_gmwd = new_gmwds.first()
                new_gmwd.groundwater_monitoring_well_dynamic_id = None
            
            elif len(new_gmwds) > 1:
                new_gmwd = new_gmwds.last()
                new_gmwd.groundwater_monitoring_well_dynamic_id = None
            
            else:
                raise Exception("No Groundwater Monitoring Well Dynamic Tables found for this GMW: ", well_static)

            
            # Check what has to be changed
            new_gmwd = well_dynamic(new_gmwd, updates)


            # Save and add new key to event
            new_gmwd.save()
            
            # Add to the event.
            event.groundwater_monitoring_well_static = well_static
            event.groundwater_monitoring_well_dynamic = new_gmwd
            event.save()

        except:
            raise Exception(f"Failed to update tube data: {updates}")

def get_removal_event(gmw_dict, groundwater_monitoring_well_static):
    event = Event.objects.create(event_name = "removal",
                    event_date = get_mytimezone_date(
                        gmw_dict.get(
                            "removal_date", None
                        ),
                    ),
                    groundwater_monitoring_well_static = groundwater_monitoring_well_static,
                    groundwater_monitoring_well_dynamic = GroundwaterMonitoringWellDynamic.objects.filter(
                        groundwater_monitoring_well = groundwater_monitoring_well_static).first(),
            )
    event.save()

def check_filetype(csv_file: str):
    if ".xlsx" in csv_file:
        filetype = "Excel"

    elif ".csv" in csv_file:
        filetype = "CSV"

    else:
        raise Exception("Given file is not a CSV or Excel file.")

    return filetype

def read_datafile(file: str, type: str):
    if type == 'Excel':
        df = pd.read_excel(file)
    
    elif type == 'CSV':
        df = pd.read_csv(file)

    else:
        raise Exception("Current filetype not yet implemented.")

    return df