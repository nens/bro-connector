from typing import List, Optional
import json
import pysftp
import datetime
import os
import random
from pyproj import Transformer
from pathlib import Path

from main import localsecret as ls
from gmw import models as gmw_models
from gmn import models as gmn_models

ipfo_w = {
    "opmerking": {
      "type": "text",
      "hint": "Informatie over niet kunnen opnemen bijv. beschadiging"
      },
    "maaiveldhoogte": {
        "type": "number",
        "hint": "Hoogte in meter NAP"
    },
    "methode_positiebepaling_maaiveld": {
        "name": "methode positiebepaling maaiveld",
        "type": "choice",
        "options": [
            "GPS",
            "Waterpas"
        ]
    },
    "beschermconstructie":{
        "type": "text",
        "hint": "Het type beschermconstructie wat is aangebracht"
    },
    "foto 1": {
      "type": "photo",
      "hint": "Foto ter ondersteuning"
      },
    "foto 2": {
      "type": "photo",
      "hint": "Foto ter ondersteuning"
      },
    "foto 3": {
      "type": "photo",
      "hint": "Foto ter ondersteuning"
      },
    "foto 4": {
      "type": "photo",
      "hint": "Foto ter ondersteuning"
      },
    "foto 5": {
      "type": "photo",
      "hint": "Foto ter ondersteuning"
      },
}
ipfo_f = {
    "landgebruik": {
        'name': 'Dominant landgebruik',
        'type': 'choice',
        # 'hint': 'max 2 selecteren',
        'options': ['Grasland',
                    'Akkerbouw',
                    'Glastuinbouw, bomen-&bollenteelt',
                    'Bos, natuur en water',
                    'Bebouwd',
                    'Industrie']
    },
    "beschadiging":  {
        'name': 'Beschadiging put en filter?',
        'type': 'choice',
        'options': ['Ja', 'Nee', 'Onbekend']
    },
    "afdekking": {
        'name': 'Correcte afdekking put?',
        'type': 'choice',
        'options': ['Ja', 'Nee', 'Onbekend']
    },
    # "grondwaterstand": {
    #   "name": "Grondwaterstand tov bovenkant buis",
    #   "type": "number",
    #   "hint": "cm tov bovenkant peilfilter/stijgbuis"
    # },
    "gws_voor_pompen": {
        'name': 'Grondwaterstand voor het voorpompen [cm] *',
        'type': 'number',
        'hint': 'cm tov bovenkant peilfilter/stijgbuis'
    },
    "gws_na_pompen": {
        'name': 'Grondwaterstand na het voorpompen [cm] *',
        'type': 'number',
        'hint': 'cm tov bovenkant peilfilter/stijgbuis'
    },
    "bovenkant_peilfilter": {
        'name': 'Bovenkant peilfilter [cm]',
        'type': 'number',
        'hint': 'cm+mv'
    },
    "onderkant_peilfilter": {
        'name': 'Onderkant peilfilter [cm]',
        'type': 'number',
        'hint': 'cm tov bovenkant peilfilter/stijgbuis'
    },
    "pomptype": {
        'name': 'Pomptype *',
        'type': 'choice',
        'options': ['onderwaterpomp', 'peristaltischePomp',
                    'vacuümpomp', 'anders', 'onbekend']
    },
    "lengte_waterkolom": {
        'name': 'Lengte waterkolom [cm]',
        'type': 'number',
        'hint': 'cm'
    },
    "inwendige_diameter_filter": {
        'name': 'Inwendige diameter filter [mm]',
        'type': 'number',
        'hint': 'mm'
    },
    "voorpompvolume": {
        'name': 'Voorpompvolume',
        'type': 'number',
        'hint': 'l'
    },
    "voorpompdebiet": {
        'name': 'Voorpompdebiet [l/min]',
        'type': 'number',
        'hint': 'l/min; maximaal 8 l/min'
    },
    "bemonsteringsdebiet": {
        'name': 'Bemonsteringsdebiet [l/min]',
        'type': 'number',
        'hint': 'l/min'
    },
    "toestroming_filter": {
        'name': 'Toestroming filter',
        'type': 'choice',
        'options': ['Goed', 'Matig', 'Slecht']
    },
    "zuurgraad_0": {
        'name': 'Zuurgraad na 0 minuten [pH]',
        'type': 'number',
        'hint': 'pH'
    },
    "zuurgraad_3": {
        'name': 'Zuurgraad na 3 minuten [pH]',
        'type': 'number',
        'hint': 'pH'
    },
    "zuurgraad_6": {
        'name': 'Zuurgraad na 6 minuten [pH]',
        'type': 'number',
        'hint': 'pH'
    },
    "geleidbaarheid_0": {
        'name': 'Geleidbaarheid na 0 minuten [µS/cm]',
        'type': 'number',
        'hint': 'µS/cm'
    },
    "geleidbaarheid_3": {
        'name': 'Geleidbaarheid na 3 minuten [µS/cm]',
        'type': 'number',
        'hint': 'µS/cm'
    },
    "geleidbaarheid_6": {
        'name': 'Geleidbaarheid na 6 minuten [µS/cm]',
        'type': 'number',
        'hint': 'µS/cm'
    },
    'zuurstof': {
        'name': 'Zuurstof (O2) [mg/l] *',
        'type': 'number',
        'hint': 'mg/l'
    },
    'temperatuur': {
        'name': 'Temperatuur [ºC] *',
        'type': 'number',
        'hint': 'ºC'
    },
    'temperatuur_moeilijk': {
        'name': 'Temperatuur moeilijk te bepalen *',
        'type': 'choice',
        'options': ['Ja', 'Nee', 'Onbekend']
    },
    'waterstofcarbonaat': {
        'name': 'Waterstofcarbonaat (HCO3) [mg/l] *',
        'type': 'number',
        'hint': 'mg/l'
    },
    'troebelheid': {
        'name': 'Troebelheid [NTU] *',
        'type': 'number',
        'hint': 'NTU'
    },
    'bicarbonaat': {
        'name': 'Bicarbonaat [mg/l] *',
        'type': 'number',
        'hint': 'mg/l'
    },
    'afwijking_meetapparatuur': {
        'name': 'Afwijking meetapparatuur *',
        'type': 'choice',
        'options': ['Ja', 'Nee', 'Onbekend']
    },
    'contaminatie_door_verbrandingsmotor': {
        'name': 'Contaminatie door verbrandingsmotor *',
        'type': 'choice',
        'options': ['Ja', 'Nee', 'Onbekend']
    },
    'bemonsteringsprocedure': {
        'name': 'Bemonsteringsprocedure *',
        'type': 'choice',
        'options': [
            'NEN5744v1991',
            'NEN5744v2011-A1v2013',
            'NEN5745v1997',
            'NTA8017v2008',
            'NTA8017v2016',
            'SIKBProtocol2002vanafV4',
            'onbekend',
        ]
    },
    'inline_filter_afwijkend': {
        'name': 'Inline filter afwijkend *',
        'type': 'choice',
        'options': ['Ja', 'Nee', 'Onbekend']
    },
    'slang_hergebruikt': {
        'name': 'Slang hergebruikt *',
        'type': 'choice',
        'options': ['Ja', 'Nee', 'Onbekend']
    },
    'monster_belucht': {
        'name': 'Monster belucht *',
        'type': 'choice',
        'options': ['Ja', 'Nee', 'Onbekend']
    },
    'afwijkend_gekoeld': {
        'name': 'Afwijkend gekoeld *',
        'type': 'choice',
        'options': ['Ja', 'Nee', 'Onbekend']
    },
    "kleur": {
        'name': 'Kleur *',
        'type': 'choice',
        'options': [
            'kleurloos',
            'wit',
            'grijs',
            'zwart',
            'rood',
            'oranje',
            'geel',
            'groen',
            'blauw',
            'paars',
            'bruin',
            'roestbruin',
            'beige',
            'creme',
        ]
    },
    "bijkleur": {
        'name': 'Bijkleur *',
        'type': 'choice',
        'options': [
            'kleurloos',
            'wit',
            'grijs',
            'zwart',
            'rood',
            'oranje',
            'geel',
            'groen',
            'blauw',
            'paars',
            'bruin',
            'roestbruin',
            'beige',
            'creme',
        ]
    },
    "kleursterkte": {
        'name': 'Kleursterkte *',
        'type': 'choice',
        'options': ['zeer licht', 'licht', 'neutraal', 'donker',
                    'zeer donker']
    },
    "foto": {
      "type": "photo",
      "hint": "Foto ter ondersteuning"
      },
    "bijzonderheden": {
        'name': 'Bijzonderheden',
        'type': 'text',
        'hint': 'Overige informatie'
    }
}

input_fields_well_locations = [
    "opmerking",
    "maaiveldhoogte",
    "methode_positiebepaling_maaiveld",
    "beschermconstructie",
    "foto 1",
    "foto 2",
    "foto 3",
    "foto 4",
    "foto 5",
]

input_fields_filter_locations = [
    "landgebruik",
    "beschadiging",
    "afdekking",
    "gws_voor_pompen"
    "gws_na_pompen",
    "bovenkant_peilfilter",
    "onderkant_peilfilter",
    "pomptype",
    "lengte_waterkolom",
    "inwendige_diameter_filter",
    "voorpompvolume",
    "voorpompdebiet",
    "bemonsteringsdebiet",
    "toestroming_filter",
    "zuurgraad_0",
    "zuurgraad_3",
    "zuurgraad_6",
    "geleidbaarheid_0",
    "geleidbaarheid_3",
    "geleidbaarheid_6",
    'zuurstof',
    'temperatuur',
    'temperatuur_moeilijk',
    'waterstofcarbonaat',
    'troebelheid',
    'bicarbonaat',
    'afwijking_meetapparatuur',
    'contaminatie_door_verbrandingsmotor',
    'bemonsteringsprocedure',
    'inline_filter_afwijkend',
    'slang_hergebruikt',
    'monster_belucht',
    'afwijkend_gekoeld',
    "kleur",
    "bijkleur",
    "kleursterkte",
    "foto",
    "bijzonderheden",
]

input_field_options = ipfo_w.copy() # to avoid modifying the original
input_field_options.update(ipfo_f)


input_fields_filter = ipfo_f

input_fields_well = ipfo_w

def convert_epsg28992_to_epsg4326(x, y):
    # Create a Transformer object for converting from EPSG:28992 to EPSG:4326
    transformer = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
   
    # Perform the transformation
    lon, lat = transformer.transform(x, y)
   
    return lon, lat

def generate_random_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

# From the FieldForm Github
def write_location_file(data, filename):
    """
    Write a FieldForm location file (.json)

    Parameters
    ----------
    data : dict
        The data that needs to be written to the location-file. This dictionary can have
        the keys 'settings', 'inputfields', 'groups' and/or 'locations'.
    fname : str
        The path to the new location-file (.json).

    Returns
    -------
    None.

    """
    with open(filename, "w") as outfile:
        json.dump(data, outfile, indent=2)

def perceel_property(tube: gmw_models.GroundwaterMonitoringTubeStatic, perceel_check: str) -> str:
    measuring_point = gmn_models.MeasuringPoint.objects.filter(groundwater_monitoring_tube=tube).all()
    if measuring_point:
        check = 0
        for measuring_point_i in measuring_point:
            subgroup = measuring_point_i.subgroup.all()
            for subgroup_i in subgroup:
                if perceel_check in subgroup_i.name:
                    check = 1
                else:
                    continue
        if check == 1:
            return "Ja"
        else:
            return "Nee"
    else:
        return "Nee"
    

def create_sublocation_dict(tube: gmw_models.GroundwaterMonitoringTubeStatic) -> dict:
    filter_name = tube.__str__()
    filter_state = tube.state.order_by('date_from').last()
    return {
        f"{filter_name}": {
            "inputfields": input_fields_filter_locations,
            "properties": {
                # TO DO: Add perceel & other fields
                "Bovenkantbuis hoogte ": filter_state.tube_top_position,
                "Bovenkant filter hoogte ": filter_state.screen_top_position,
                "Onderkant filter hoogte ": filter_state.screen_bottom_position,
                "diameter buis [mm]": filter_state.tube_top_diameter,
                "Perceel 1": perceel_property(filter_state.groundwater_monitoring_tube_static, "GAR_2024_Perceel_1"),
                "Perceel 2": perceel_property(filter_state.groundwater_monitoring_tube_static, "GAR_2024_Perceel_2"),
                "Perceel 3": perceel_property(filter_state.groundwater_monitoring_tube_static, "GAR_2024_Perceel_3"),
                "Perceel 4": perceel_property(filter_state.groundwater_monitoring_tube_static, "GAR_2024_Perceel_4"),
                "Perceel 5": perceel_property(filter_state.groundwater_monitoring_tube_static, "GAR_2024_Perceel_5"),
            },
        },
    }

class FieldFormGenerator:
    inputfields: Optional[List[dict]] = input_field_options

    # QuerySets
    monitoringnetworks: Optional[list[gmn_models.GroundwaterMonitoringNet]]
    wells: Optional[List[gmw_models.GroundwaterMonitoringWellStatic]]
    optimal: Optional[bool]
    ftp_path: Optional[Path]

    def __init__(self, *args, **kwargs) -> None:
        self.ftp_path = kwargs.get("path", None)

    def write_file_to_ftp(self, file: str, remote_filename: str):
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None
        with pysftp.Connection(ls.ftp_ip, username=ls.ftp_username, password=ls.ftp_password, port=22, cnopts=cnopts) as sftp:
            with sftp.cd(self.ftp_path):
                sftp.put(localpath=file, remotepath=remote_filename)

    def delete_old_files_from_ftp(self):
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None
        with pysftp.Connection(ls.ftp_ip, username=ls.ftp_username, password=ls.ftp_password, port=22, cnopts=cnopts) as sftp:
            with sftp.cd(self.ftp_path):
                # Get current date and time
                now = datetime.datetime.now()
                
                # list files in the current directory
                files = sftp.listdir()
                for file in files:
                    if not str(file).startswith('locations'):
                        continue

                    file_date = str(file).split('_')[1][0:8]
                    file_time = datetime.datetime.strptime(file_date, "%Y%m%d")
                    
                    # Calculate the age of the file
                    file_age = now - file_time
                    
                    # Check if the file is older than a month
                    if file_age > datetime.timedelta(days=30):
                        # Delete the file
                        sftp.remove(file)
                        print(f"Deleted {file} (age: {file_age.days} days)")

    def create_location_dict(self) -> None:
        locations = {}
        for well in self.wells:  
            tubes = gmw_models.GroundwaterMonitoringTubeStatic.objects.filter(
                groundwater_monitoring_well_static = well
            )

            lon, lat = convert_epsg28992_to_epsg4326(
                x=well.coordinates.x,
                y=well.coordinates.y    
            )

            well_name = well.__str__()
            well_location = {
                f"{well_name}": {
                    "lat": lat,
                    "lon": lon,
                    "sublocations": {
                        f"{well_name}": {
                            "inputfields": input_fields_well_locations,
                        }
                    },
                }
            }
            if hasattr(self, "group_name"):
                well_location[f"{well_name}"].update({"group": self.group_name})

            for tube in tubes:
                sublocation = create_sublocation_dict(tube)
                well_location[f"{well_name}"]["sublocations"].update(sublocation)

            locations.update(well_location)
        
        return locations

    def _set_current_group(self, group_name: str):
        self.group_name = group_name

    def _flush_wells(self):
        self.wells = []

    def write_monitoringnetworks_to_dict(self) -> dict:
        groups = {}
        for monitoring_network in gmn_models.GroundwaterMonitoringNet.objects.all():
            groups[monitoring_network.name] = {
                "name": monitoring_network.name,
                "color": monitoring_network.color
            }
        
        return groups
    
    def write_subgroups_to_dict(self, monitoringnetwork: gmn_models.GroundwaterMonitoringNet) -> dict:
        groups = {}

        for subgroup in monitoringnetwork.subgroups.all():
            groups[subgroup.name] = {
                "name": subgroup.name,
                "color": subgroup.color,
            }

        return groups

    def write_measuringpoints_to_wells(self, monitoringnetwork: gmn_models.GroundwaterMonitoringNet) -> None:
        measuringpoints = gmn_models.MeasuringPoint.objects.filter(
            gmn = monitoringnetwork
        )
        for measuringpoint in measuringpoints:
            self.wells.append(measuringpoint.groundwater_monitoring_tube.groundwater_monitoring_well_static)

    def write_measuringpoints_to_wells_subgroup(self, subgroup: gmn_models.Subgroup) -> None:
        measuringpoints = gmn_models.MeasuringPoint.objects.filter(
            subgroup = subgroup
        )
        for measuringpoint in measuringpoints:
            self.wells.append(measuringpoint.groundwater_monitoring_tube.groundwater_monitoring_well_static)

    def _write_data(self, data: dict):
        cur_date = datetime.datetime.now().date()
        date_string = cur_date.strftime("%Y%m%d")

        # Check if fieldforms folder exists
        if not os.path.exists("../fieldforms"):
            os.mkdir("../fieldforms")

        # Store the file locally
        write_location_file(data=data, filename=f"../fieldforms/gar/locations_{date_string}.json")

        # Write local file to FTP
        self.write_file_to_ftp(file=f"../fieldforms/locations_{date_string}.json", remote_filename=f"locations_{date_string}.json")

    def generate(self):
        data = {
            "inputfields": input_field_options,
            "groups": {},
        }

        if hasattr(self, "optimal"):
            if self.optimal:
                # data["groups"].update(self.write_monitoringnetworks_to_dict())

                # locations = {}
                # wells_in_file = []
                # # Any that are not in a meetroute should be grouped by meetnets
                # for monitoringnetwork in gmn_models.GroundwaterMonitoringNet.objects.all():
                #     self._flush_wells()
                #     self._set_current_group(str(monitoringnetwork.name))
                #     self.write_measuringpoints_to_wells(monitoringnetwork)
                #     locations.update(self.create_location_dict())
                #     wells_pk_list = [obj.pk for obj in self.wells]
                #     wells_in_file += wells_pk_list


                # self._flush_wells()
                # self._set_current_group(None)

                # mps = gmw_models.GroundwaterMonitoringWellStatic.objects.all().exclude(pk__in=wells_in_file)
                # for mp in mps:
                #     self.wells.append(mp)

                # locations.update(self.create_location_dict())

                # # All others should be included without grouping
                # data["locations"] = locations
                # self._write_data(data)
                return


        if hasattr(self, "monitoringnetworks"):
            if len(self.monitoringnetworks) == 1:
                # Use subgroups of network if available.
                monitoringnetwork = self.monitoringnetworks[0]
                data["groups"] = self.write_subgroups_to_dict(monitoringnetwork)
                locations = {}
                for subgroup in monitoringnetwork.subgroups.all():
                    print(subgroup)
                    self._flush_wells()
                    self._set_current_group(subgroup.name)
                    self.write_measuringpoints_to_wells_subgroup(subgroup)
                    locations.update(self.create_location_dict())
                
                data["locations"] = locations
                self._write_data(data)
            else:
                data["groups"] = self.write_monitoringnetworks_to_dict()
                locations = {}
                for monitoringnetwork in self.monitoringnetworks:
                    self._flush_wells()
                    self._set_current_group(str(monitoringnetwork.name))
                    self.write_measuringpoints_to_wells(monitoringnetwork)
                    locations.update(self.create_location_dict())
                
                data["locations"] = locations
                self._write_data(data)

        elif hasattr(self, "wells"):
            data["locations"] = self.create_location_dict()
            self._write_data(data)

        else:
            # If nothing has been deliverd, create for all wells without a grouping.
            self.wells = gmw_models.GroundwaterMonitoringWellStatic.objects.all()
            data["locations"] = self.create_location_dict()
            self._write_data(data)