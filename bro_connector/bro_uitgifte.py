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

class DataRetriever(object):
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


def get_gmw_data(id: str, full_history: bool):
    basis_url = "https://publiek.broservices.nl/gm/gmw/v1/objects/"

    if full_history:
        fh = "ja"
    else:
        fh = "nee"

    gmw_verzoek = requests.get("{}{}?fullHistory={}".format(basis_url, id, fh))

    root = ET.fromstring(gmw_verzoek.content)

    return root


def make_dict(gmw_element):
    tags = []
    values = []
    i = ""
    j = 0
    k = 0

    for element in gmw_element.iter():
        tag = element.tag
        split = tag.split("}")

        if split[1] == "wellConstructionDate":
            i = "construction_"

        elif split[1] == "intermediateEvent":
            j = j + 1
            i = "event_" + str(j) + "_"

        elif split[1] == "wellRemovalDate":
            i = "removal_"

        elif split[1] == "monitoringTube":
            k = k + 1
            i = "tube_" + str(k) + "_"

        tag = str(i) + split[1]

        tags.append(tag)
        values.append(element.text)

    gmw_dict = dict(zip(tags, values))

    return gmw_dict, j, k

def slice(sourcedict, string):
    newdict = {}
    for key in sourcedict.keys():
        if key.startswith(string):
            newdict[key.split(string)[1]] = sourcedict[key]
    return newdict

def update_well_dynamic(gmwd, updates_dict):
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

def update_tube_dynamic(gmtd, updates_dict):
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

def update_electrode_dynamic(eled, updates_dict):
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

def get_initial_well_static_data(gmw_dict):
    gmws = GroundwaterMonitoringWellStatic.objects.create(
                bro_id=gmw_dict.get("broId", None),
                construction_standard=gmw_dict.get("constructionStandard", None),
                coordinates=(
                    f"POINT({gmw_dict.get('pos', None)})"
                ),  # -> Has a delivered location and a standardized location, which do we want? Used std for now
                delivery_accountable_party=gmw_dict.get(
                    "deliveryAccountableParty", None
                ),
                delivery_context=gmw_dict.get("deliveryContext", None),
                delivery_responsible_party=gmw_dict.get(
                    "deliveryResponsibleParty", None
                ),  # Not in XML ??? -> Same as delivery or is it our id or Zeeland ???
                horizontal_positioning_method=gmw_dict.get(
                    "horizontalPositioningMethod", None
                ),
                initial_function=gmw_dict.get("initialFunction", None),
                local_vertical_reference_point=gmw_dict.get(
                    "localVerticalReferencePoint", None
                ),
                monitoring_pdok_id=gmw_dict.get(
                    "monitoringPdokId", None
                ),  # Cannot find in XML
                nitg_code=gmw_dict.get("nitgCode", None),
                well_offset=gmw_dict.get("offset", None),
                olga_code=gmw_dict.get("olgaCode", None),  # -> Cannot find in XML
                quality_regime=gmw_dict.get("qualityRegime", None),
                reference_system=gmw_dict.get(
                    "referenceSystem", None
                ),  # -> Cannot find in XML, but the reference vertical is NAP?
                registration_object_type=gmw_dict.get(
                    "registrationStatus", None
                ),  # -> registration status? Otherwise cannot find.
                request_reference=gmw_dict.get("requestReference", None),
                under_privilege=gmw_dict.get(
                    "underReview", None
                ),  # -> Not in XML, maybe under review?
                vertical_datum=gmw_dict.get("verticalDatum", None),
                well_code=gmw_dict.get("wellCode", None),
                ## Have to readjust the methodology slightly because if there are multiple events they cannot all have the same names and dates...
            )  # -> Is soms ook niet gedaan, dus nvt? Maar moet datum opgeven...)\
    gmws.save()
    return gmws

def get_initial_well_dynamic_data(gmw_dict, groundwater_monitoring_well_static):
    gmwd = GroundwaterMonitoringWellDynamic.objects.create(
                groundwater_monitoring_well=groundwater_monitoring_well_static,
                deliver_gld_to_bro=gmw_dict.get(
                    "deliverGldToBro", False
                ),  # std True because we are collecting data from BRO
                ground_level_position=gmw_dict.get("groundLevelPosition", None),
                ground_level_positioning_method=gmw_dict.get(
                    "groundLevelPositioningMethod", None
                ),
                ground_level_stable=gmw_dict.get("groundLevelStable", None),
                maintenance_responsible_party=gmw_dict.get(
                    "maintenanceResponsibleParty", None
                ),  # not in XML
                number_of_standpipes=gmw_dict.get(
                    "numberOfStandpipes", None
                ),  # not in XML
                owner=gmw_dict.get("owner", None),
                well_head_protector=gmw_dict.get("wellHeadProtector", None),
                well_stability=gmw_dict.get("wellStability", None),
            )  # not in XML)
    gmwd.save()

def get_initial_tube_static_data(gmw_dict, groundwater_monitoring_well_static, tube_number):
    prefix = "tube_" + str(tube_number) + "_"
    gmts = GroundwaterMonitoringTubesStatic.objects.create(
                        groundwater_monitoring_well=groundwater_monitoring_well_static,
                        artesian_well_cap_present=gmw_dict.get(
                            prefix + "artesianWellCapPresent", None
                        ),
                        deliver_gld_to_bro=gmw_dict.get(
                            prefix + "deliverGldToBro", False
                        ),  # std True because we are collecting data from BRO
                        number_of_geo_ohm_cables=gmw_dict.get(
                            prefix + "numberOfGeoOhmCables", None
                        ),
                        screen_length=gmw_dict.get(
                            prefix + "screenLength", None
                        ),
                        sediment_sump_length=gmw_dict.get(
                            prefix + "sedimentSumpLength", None
                        ),  # not in XML --> might be because sediment sump not present, if else statement.
                        sediment_sump_present=gmw_dict.get(
                            prefix + "sedimentSumpPresent", None
                        ),
                        sock_material=gmw_dict.get(
                            prefix + "sockMaterial", None
                        ),
                        tube_material=gmw_dict.get(
                            prefix + "tubeMaterial", None
                        ),
                        tube_number=gmw_dict.get(prefix + "tubeNumber", None),
                        tube_type=gmw_dict.get(prefix + "tubeType", None),
                    )
    gmts.save()
    return gmts

def get_initial_tube_dynamic_data(gmw_dict, groundwater_monitoring_tube_static, tube_number):
    prefix = "tube_" + str(tube_number) + "_"
    gmtd = GroundwaterMonitoringTubesDynamic.objects.create(
                        groundwater_monitoring_tube_static=groundwater_monitoring_tube_static,
                        glue=gmw_dict.get(prefix + "glue", None),
                        inserted_part_diameter=gmw_dict.get(
                            prefix + "insertedPartDiameter", None
                        ),
                        inserted_part_length=gmw_dict.get(
                            prefix + "insertedPartLength", None
                        ),
                        inserted_part_material=gmw_dict.get(
                            prefix + "insertedPartMaterial", None
                        ),
                        plain_tube_part_length=gmw_dict.get(
                            prefix + "plainTubePartLength", None
                        ),
                        tube_packing_material=gmw_dict.get(
                            prefix + "tubePackingMaterial", None
                        ),
                        tube_status=gmw_dict.get(prefix + "tubeStatus", None),
                        tube_top_diameter=gmw_dict.get(
                            prefix + "tubeTopDiameter", None
                        ),
                        tube_top_position=gmw_dict.get(
                            prefix + "tubeTopPosition", None
                        ),
                        tube_top_positioning_method=gmw_dict.get(
                            prefix + "tubeTopPositioningMethod", None
                        ),
                        variable_diameter=gmw_dict.get(
                            prefix + "variableDiameter", None
                        ),
                    )
    gmtd.save()

def get_initial_geo_ohm_data(gmw_dict, groundwater_monitoring_tube_static, tube_number):
    prefix = "tube_" + str(tube_number) + "_"
    geoc = GeoOhmCable.objects.create(
                                groundwater_monitoring_tube_static=groundwater_monitoring_tube_static,
                                cable_number=gmw_dict.get(prefix + "cableNumber", None),
                            )  # not in XML -> 0 cables)
    print(geoc)
    geoc.save()

def get_geo_ohm_cable(groundwater_monitoring_well_static):
    geoc = GeoOhmCable.objects.get(groundwater_monitoring_well = groundwater_monitoring_well_static)
    return geoc

def get_initial_electrode_static_data(gmw_dict, groundwater_monitoring_well_static, tube_number):
    geo_ohm_cable = get_geo_ohm_cable(groundwater_monitoring_well_static)
    prefix = "tube_" + str(tube_number) + "_"
    eles = ElectrodeStatic.objects.create(
                                geo_ohm_cable=geo_ohm_cable,
                                electrode_packing_material=gmw_dict.get(
                                    prefix + "electrodePackingMaterial", None
                                ),
                                electrode_position=gmw_dict.get(
                                    prefix + "electrodePosition", None
                                ),
                            )
    eles.save()

def get_initial_electrode_dynamic_data(gmw_dict, groundwater_monitoring_well_static, tube_number):
    electrode_static = get_electrode_static(groundwater_monitoring_well_static)
    prefix = "tube_" + str(tube_number) + "_"
    eled = ElectrodeDynamic.objects.create(
                                electrode_static=electrode_static,
                                electrode_number=gmw_dict.get(
                                    prefix + "electrodeNumber", None
                                ),
                                electrode_status=gmw_dict.get(
                                    prefix + "electrodeStatus", None
                                ),
                            )
    eled.save()

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

def create_intermediate_event(event_updates, gmws):
    try:
        event = Event.objects.create(
            event_name = event_updates['eventName'],
            event_date = get_mytimezone_date(event_updates['date']),
            groundwater_monitoring_well_static = gmws,
        )
    except:
        try:
            event = Event.objects.create(
                event_name = event_updates['eventName'],
                event_date = get_mytimezone_date(str(event_updates['year']) + "-01-01"),
                groundwater_monitoring_well_static = gmws,
            )
        except:
            print(event_updates)
            exit()
    
    return event

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

def fill_event_data(event_updates, event, groundwater_monitoring_well):
    try:
        if event_updates.get('wellData', True):
            # Check for tube data
            if event_updates.get('tubeData', True):
                # Check for electrode data
                if event_updates.get('electrodeData', True):
                    print("Unknown data")
                    print(event_updates)
                else:
                    # Clone row and make new primary key with save
                    new_eleds = ElectrodeDynamic.objects.get(
                        electrode_static = get_electrode_static(groundwater_monitoring_well))
                    
                    # This assumes the gmwds are sorted based on creation date.
                    if len(new_eleds) == 1:
                        new_eled = new_eleds.first()
                        new_eled.electrode_dynamic_id = None
                    
                    elif len(new_gmtds) > 1:
                        new_eled = new_gmtds.last()
                        new_eled.electrode_dynamic_id = None
                    
                    else:
                        raise Exception("No Groundwater Monitoring Tube Dynamic Tables found for this GMT: ", get_tube_static(groundwater_monitoring_well, event_updates['tubeNumber']))

                    # Check what has to be changed
                    new_eled = update_electrode_dynamic(new_eled, event_updates)

                    # Save and add new key to event
                    new_eled.save()

                    # Add to the event.
                    event.electrode_dynamic = new_eled
                    event.groundwater_monitoring_well_static = groundwater_monitoring_well
                    event.save()

            else:
                # Find which filter needs to be adjusted
                new_gmts = GroundwaterMonitoringTubesStatic.objects.get(
                    tube_number = event_updates['tubeNumber'],
                    groundwater_monitoring_well = groundwater_monitoring_well,
                    )

                # Clone row and make new primary key with save
                new_gmtds = GroundwaterMonitoringTubesDynamic.objects.filter(
                    groundwater_monitoring_tube_static = new_gmts)
                
                # This assumes the gmwds are sorted based on creation date.
                if len(new_gmtds) == 1:
                    new_gmtd = new_gmtds.first()
                    new_gmtd.groundwater_monitoring_tube_dynamic_id = None
                
                elif len(new_gmtds) > 1:
                    new_gmtd = new_gmtds.last()
                    new_gmtd.groundwater_monitoring_tube_dynamic_id = None
                
                else:
                    raise Exception("No Groundwater Monitoring Tube Dynamic Tables found for this GMT: ", get_tube_static(groundwater_monitoring_well, event_updates['tubeNumber']))

                # Check what has to be changed
                new_gmtd = update_tube_dynamic(new_gmtd, event_updates)


                # Save and add new key to event
                new_gmtd.save()
                
                #  Add to the event
                event.groundwater_monitoring_well_tube_dynamic = new_gmtd
                event.save()
        else:
            # Clone row and make new primary key with save
            new_gmwds = GroundwaterMonitoringWellDynamic.objects.filter(
                groundwater_monitoring_well = groundwater_monitoring_well)
            
            # This assumes the gmwds are sorted based on creation date.
            if len(new_gmwds) == 1:
                new_gmwd = new_gmwds.first()
                new_gmwd.groundwater_monitoring_well_dynamic_id = None
            
            elif len(new_gmwds) > 1:
                new_gmwd = new_gmwds.last()
                new_gmwd.groundwater_monitoring_well_dynamic_id = None
            
            else:
                raise Exception("No Groundwater Monitoring Well Dynamic Tables found for this GMW: ", groundwater_monitoring_well)

            
            # Check what has to be changed
            new_gmwd = update_well_dynamic(new_gmwd, event_updates)


            # Save and add new key to event
            new_gmwd.save()
            
            # Add to the event.
            event.groundwater_monitoring_well_static = groundwater_monitoring_well
            event.groundwater_monitoring_well_dynamic = new_gmwd
            event.save()
    except:
        print(f"dict: {str(event_updates)} \ngmws: {str(groundwater_monitoring_well)}")


def get_intermediate_events(gmw_dict, gmws, event_number):
    prefix = "event_" + str(event_number) + "_"
    event_updates = slice(gmw_dict, prefix)

    event = create_intermediate_event(event_updates, gmws)
    fill_event_data(event_updates, event, gmws)


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