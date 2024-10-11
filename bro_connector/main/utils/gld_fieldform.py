from typing import List, Optional
import json
import pysftp
import datetime
import os
import random

from main import localsecret as ls
from gmw import models as gmw_models
from gld import models as gld_models
from gmn import models as gmn_models

input_field_options = {
    "foto1": {
        "type": "photo",
        "name": "foto 1"
    },
    "foto2": {
        "type": "photo",
        "name": "foto 2"
    },
    "waterstand": {
        "type": "number",
        "name": "Waterstand"
    },
    "opmerking": {
        "type": "text",
        "name": "Opmerking"
    }
}

input_fields_filter = [
    "",
    "",
    "",
]

input_fields_well = [
    "",
    "",
    "",
]

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
        with sftp.cd(ls.ftp_path):
            sftp.put(localpath=file, remotepath=remote_filename)

def delete_old_files_from_ftp():
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None
    with pysftp.Connection(ls.ftp_ip, username=ls.ftp_username, password=ls.ftp_password, port=22, cnopts=cnopts) as sftp:
        with sftp.cd(ls.ftp_path):
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
            well_name = well.__str__()
            well_location = {
                f"{well_name}": {
                    "lat": well.coordinates.y,
                    "lon": well.coordinates.x,
                    "inputfields": input_fields_well,
                    "sublocations": {},
                }
            }
            if hasattr(self, "group_name"):
                well_location.update({"group": self.group_name})

            for tube in tubes:
                sublocation = create_sublocation_dict(tube)
                well_location["sublocations"].update(sublocation)
            
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
                "color": generate_random_color()
            }
        
        return groups

    def write_measuringpoints_to_wells(self, monitoringnetwork: gmn_models.GroundwaterMonitoringNet) -> None:
        measuringpoints = gmn_models.MeasuringPoint.objects.filter(
            gmn = monitoringnetwork
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
        write_location_file(data=data, filename=f"../fieldforms/locations_{date_string}.json")

        # Write local file to FTP
        write_file_to_ftp(file=f"../fieldforms/locations_{date_string}.json", remote_filename=f"locations_{date_string}.json")

    def generate(self):
        data = {}
        configs = gld_models.MeasurementConfiguration.objects.all().distinct("configuration_name")
        # For all configurations generate the inputfields.
        inputfields = {}
        inputfield_groups = {}
        for config in configs:
            self.update_postfix(config)
            inputfields.update(self.generate_inputfields())
            inputfield_groups.update(self.generate_inputfield_groups())

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
            # data["groups"] = self.write_monitoringnetworks_to_list()
            # locations = {}
            # for monitoringnetwork in self.monitoringnetworks:
            #     self._flush_wells()
            #     self._set_current_group(str(monitoringnetwork.name))
            #     self.write_measuringpoints_to_wells(monitoringnetwork)
            #     locations.update(self.create_location_dict())
            
            # data["locations"] = locations
            # self._write_data(data)
            return

        elif hasattr(self, "wells"):
            data["locations"] = self.create_location_dict()
            self._write_data(data)

        else:
            # If nothing has been deliverd, create for all wells without a grouping.
            self.wells = gmw_models.GroundwaterMonitoringWellStatic.objects.all()
            data["locations"] = self.create_location_dict()
            self._write_data(data)