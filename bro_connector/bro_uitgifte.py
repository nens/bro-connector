import requests
import requests.auth
import xml.etree.ElementTree as ET
import psycopg2
import psycopg2.sql
import json
import os
from datetime import datetime, timedelta
from django.utils import timezone
from psycopg2.extras import execute_values

DB_NAME = "grondwatermeetnet"
DB_USER = "postgres"
DB_PASS = "!StNS!2023"
DB_HOST = "localhost"
DB_PORT = "5432"


# FORMULAS USED IN HISTORIE_OPHALEN COMMAND DJANGO ZEELAND


def get_bro_ids(kvk_nummer):
    basis_url = "https://publiek.broservices.nl"
    kvk_verzoek = requests.get(
        basis_url + "/gm/gmw/v1/bro-ids?bronhouder=" + str(kvk_nummer)
    )

    bro_ids = json.loads(kvk_verzoek.text)
    return bro_ids["broIds"]


def get_gmw_ids(IDs):
    gmw_ids = []
    other_ids = []

    for id in IDs:
        if id.startswith("GMW"):
            gmw_ids.append(id)
        else:
            other_ids.append(id)

    return gmw_ids


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