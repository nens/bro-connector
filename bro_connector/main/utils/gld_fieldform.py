from typing import List, Optional
import json
import pysftp
import datetime
import os
import random
from pyproj import Transformer

from main import localsecret as ls
from gmw import models as gmw_models
from gld import models as gld_models
from gmn import models as gmn_models

input_field_options = {
    "opneembaarheid": {
      "name": "Grondwaterstand niet opneembaar?",
        "type": "choice",
        "options": [
          "Nee, filter staat droog",
          "Nee, beschadiging, reparatie benodigd",
          "Nee, overig (geef infomatie via opmerking)"
        ]
    },
    "grondwaterstand": {
      "name": "Grondwaterstand tov bovenkant buis",
      "type": "number",
      "hint": "cm tov bovenkant peilfilter/stijgbuis"
    },
    "opmerking": {
      "type": "text",
      "hint": "Informatie over niet kunnen opnemen bijv. beschadiging"
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
      }
  }

input_fields_filter = [
    "opneembaarheid",
    "opmerking",
    "grondwaterstand",
]

input_fields_well = [
    "opmerking",
    "foto 1",
    "foto 2",
    "foto 3",
    "foto 4",
    "foto 5",
]

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

def write_file_to_ftp(file: str, remote_filename: str):
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None
    with pysftp.Connection(ls.ftp_ip, username=ls.ftp_username, password=ls.ftp_password, port=22, cnopts=cnopts) as sftp:
        with sftp.cd(ls.ftp_gld_path):
            sftp.put(localpath=file, remotepath=remote_filename)

def delete_old_files_from_ftp():
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None
    with pysftp.Connection(ls.ftp_ip, username=ls.ftp_username, password=ls.ftp_password, port=22, cnopts=cnopts) as sftp:
        with sftp.cd(ls.ftp_gld_path):
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

def create_sublocation_dict(tube: gmw_models.GroundwaterMonitoringTubeStatic) -> dict:
    filter_name = tube.__str__()
    return {
        f"{filter_name}": {
            "inputfields": input_fields_filter,
        },
    }

class FieldFormGenerator:
    inputfields: List[dict]

    # QuerySets
    monitoringnetworks: Optional[List[gmn_models.GroundwaterMonitoringNet]]
    wells: Optional[List[gmw_models.GroundwaterMonitoringWellStatic]]
    optimal: Optional[bool]

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
                            "inputfields": input_fields_well,
                        }
                    },
                }
            }
            if hasattr(self, "group_name"):
                well_location.update({"group": self.group_name})

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
        for subgroup in monitoringnetwork.subgroup_set.all():
            groups[subgroup.code] = {
                "name": subgroup.code,
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

        print(data)
        # Store the file locally
        write_location_file(data=data, filename=f"../fieldforms/gld/locations_{date_string}.json")

        # Write local file to FTP
        write_file_to_ftp(file=f"../fieldforms/locations_{date_string}.json", remote_filename=f"locations_{date_string}.json")

    def generate(self):
        data = {}

        data["inputfields"] = input_field_options
        data["groups"] = {}

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
                for subgroup in monitoringnetwork.subgroup_set.all():
                    self._flush_wells()
                    self._set_current_group(str(subgroup.name))
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