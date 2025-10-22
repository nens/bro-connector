from typing import List, Optional
import logging
import json
import pysftp
import datetime
import os
import random
from pyproj import Transformer

from main import localsecret as ls
from gmw import models as gmw_models
from frd import models as frd_models
from gmn import models as gmn_models

maximum_difference_ratio = 0.2

input_field_options = {
    "grondwaterstand": {
        "name": "Grondwaterstand [cm tov bkb]",
        "type": "number",
        "hint": "cm tov bovenkant buis",
    },
    "opneembaarheid": {
        "name": "Grondwaterstand niet opneembaar?",
        "type": "choice",
        "options": [
            "Nee, filter staat droog",
            "Nee, beschadiging, reparatie benodigd",
            "Nee, overig (geef infomatie via opmerking)",
        ],
    },
    "positie_bovenkantbuis": {
        "name": "Positie bovenkantbuis",
        "type": "number",
    },
    "methode_positiebepaling_bovenkantbuis": {
        "name": "Buisstatus",
        "type": "choice",
        "options": [
            "afgeleidSbl",
            "AHN1",
            "AHN2",
            "AHN3",
            "AHN4",
            "GPSOnbekend",
            "kaartOnbekend",
            "onbekend",
            "RTKGPS0tot4cm",
            "RTKGPS10tot20cm",
            "RTKGPS20tot100cm",
            "RTKGPS4tot10cm",
            "tachymetrie0tot10cm",
            "tachymetrie10tot50cm",
            "waterpassing0tot2cm",
            "waterpassing2tot4cm",
            "waterpassing4tot10cm",
        ],
    },
    "buisstatus": {
        "name": "Buisstatus",
        "type": "choice",
        "options": [
            "gebruiksklaar",
            "nietGebruiksklaar",
            "onbekend",
            "onbruikbaar",
        ],
    },
    "buisdiameter": {
        "name": "Buisdiameter",
        "type": "number",
    },
    "buismateriaal": {
        "name": "Buismateriaal",
        "type": "choice",
        "options": [
            "asbest",
            "beton",
            "gres",
            "hout",
            "houtStaal",
            "ijzer",
            "koper",
            "koperStaal",
            "messing",
            "onbekend",
            "pe",
            "peHighDensity",
            "peHighDensityPvc",
            "peLowDensity",
            "pePvc",
            "pvc",
            "pvcStaal",
            "staal",
            "staalGegalvaniseerd",
            "staalRoestvrij",
            "teflon",
        ],
    },
    "buislengte": {
        "name": "Maaiveldhoogte",
        "type": "number",
    },
    "maaiveldhoogte": {"name": "Maaiveldhoogte", "type": "number", "hint": "in mNAP"},
    "methode_positiebepaling_maaiveld": {
        "name": "Methode positiebepaling maaiveld",
        "type": "choice",
        "options": [
            "afgeleidBovenkantBuis",
            "AHN1",
            "AHN2",
            "AHN3",
            "AHN4",
            "geen",
            "GPSOnbekend",
            "kaartOnbekend",
            "onbekend",
            "RTKGPS0tot4cm",
            "RTKGPS10tot20cm",
            "RTKGPS20tot100cm",
            "RTKGPS4tot10cm",
            "tachymetrie0tot10cm",
            "tachymetrie10tot50cm",
            "waterpassing0tot2cm",
            "waterpassing2tot4cm",
            "waterpassing4tot10cm",
        ],
    },
    "beschermconstructie": {
        "name": "Beschermconstructie",
        "type": "choice",
        "options": [
            "geen",
            "koker",
            "kokerDeelsMetaal",
            "kokerMetaal",
            "kokerNietMetaal",
            "onbekend",
            "pot",
            "potNietWaterdicht",
            "potWaterdicht",
        ],
    },
    "opmerking_put": {
        "name": "Opmerking",
        "type": "text",
        "hint": "m.b.t. put",
    },
    "opmerking_filter": {
        "name": "Opmerking",
        "type": "text",
        "hint": "m.b.t. filter",
    },
    "foto 1": {"type": "photo", "hint": "Locatie"},
    "foto 2": {"type": "photo", "hint": "Afwerking put"},
    "foto 3": {"type": "photo", "hint": "Filterstelling"},
    "foto 4": {"type": "photo", "hint": "Detail"},
    "foto 5": {"type": "photo", "hint": "Extra"},
    "foto F": {"type": "photo", "hint": "Foto van het filter"},
}

input_fields_filter = [
    "grondwaterstand",
    "opneembaarheid",
    "opmerking_filter",
    "positie_bovenkantbuis",
    "methode_positiebepaling_bovenkantbuis",
    "buisstatus",
    "buisdiameter",
    "buismateriaal",
    "buislengte",
    "foto F",
]

input_fields_well = [
    "opmerking_put",
    "foto 1",
    "foto 2",
    "foto 3",
    "foto 4",
    "foto 5",
]

logger = logging.getLogger(__name__)

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
    with pysftp.Connection(
        ls.ftp_ip,
        username=ls.ftp_username,
        password=ls.ftp_password,
        port=22,
        cnopts=cnopts,
    ) as sftp:
        with sftp.cd(ls.ftp_gmw_path):
            sftp.put(localpath=file, remotepath=remote_filename)


def delete_old_files_from_ftp():
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None
    with pysftp.Connection(
        ls.ftp_ip,
        username=ls.ftp_username,
        password=ls.ftp_password,
        port=22,
        cnopts=cnopts,
    ) as sftp:
        with sftp.cd(ls.ftp_frd_path):
            # Get current date and time
            now = datetime.datetime.now()

            # list files in the current directory
            files = sftp.listdir()
            for file in files:
                if not str(file).startswith("locations"):
                    continue

                file_date = str(file).split("_")[1][0:8]
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
    filter_state = tube.state.order_by("date_from").last()
    well_state = tube.groundwater_monitoring_well_static.state.order_by(
        "date_from"
    ).last()
    return {
        f"{filter_name}": {
            "inputfields": input_fields_filter,
            "properties": {
                "Maaiveldhoogte [mNAP]": well_state.ground_level_position
                if well_state
                else "Onbekend",
                "Bovenkantbuis hoogte[mNAP] ": filter_state.tube_top_position
                if filter_state
                else "Onbekend",
                "Bovenkant filter hoogte [mNAP]": filter_state.screen_top_position
                if filter_state
                else "Onbekend",
                "Onderkant filter hoogte [mNAP]": filter_state.screen_bottom_position
                if filter_state
                else "Onbekend",
                "Zandvang [m]": tube.sediment_sump_length,
                "Diameter [mm]": filter_state.tube_top_diameter
                if filter_state
                else "Onbekend",
                "Buismateriaal": tube.tube_material,
                "Buisstatus": filter_state.tube_status if filter_state else "Onbekend",
            },
        },
    }


class FieldFormGenerator:
    inputfields: Optional[List[dict]] = input_field_options

    # QuerySets
    monitoringnetworks: Optional[List[gmn_models.GroundwaterMonitoringNet]]
    wells: Optional[List[gmw_models.GroundwaterMonitoringWellStatic]]
    optimal: Optional[bool]

    def update_postfix(self, config: frd_models.MeasurementConfiguration) -> None:
        self.post_fix = config.configuration_name
        self.config = config

    def generate_inputfields(self) -> dict:
        input_field = {}
        if self.inputfields:
            for field in self.inputfields:
                if field not in input_field_options.keys():
                    raise ValueError("Unknown input field.")

                input_field[f"{field}_{self.post_fix}"] = input_field_options[field]

        return input_field

    def generate_inputfield_groups(self) -> dict:
        name = f"{self.config.measurement_pair}-{self.config.flowcurrent_pair}"
        return {
            f"{self.post_fix}": {
                "inputfields": [
                    f"weerstand_{self.post_fix}",
                    f"opmerking_{self.post_fix}",
                ],
                "name": name,
            }
        }

    def create_location_dict(self) -> None:
        locations = {}
        for well in self.wells:
            tubes = gmw_models.GroundwaterMonitoringTubeStatic.objects.filter(
                groundwater_monitoring_well_static=well
            )

            lon, lat = convert_epsg28992_to_epsg4326(
                x=well.coordinates.x, y=well.coordinates.y
            )

            well_name = well.__str__()
            well_state = well.state.order_by("date_from").last()
            if well_state is None:
                logger.warning(
                    f"No state found for well {well_name}, skipping this well."
                )
                continue

            well_location = {
                f"{well_name}": {
                    "lat": lat,
                    "lon": lon,
                    "sublocations": {
                        f"{well_name}": {
                            "inputfields": input_fields_well,
                            "properties": {
                                "Eigenaar": well_state.owner,
                                "Waarnemende instantie": well_state.maintenance_responsible_party,
                                "Status put": well.well_status,
                                "X": well.x,
                                "Y": well.y,
                                "Maaiveldhoogte [mNAP]": well_state.ground_level_position
                                if well_state
                                else "Onbekend",
                                "Positiebepaling maaiveld": well_state.ground_level_positioning_method
                                if well_state
                                else "Onbekend",
                                "Beschermconstructie": well_state.well_head_protector
                                if well_state
                                else "Onbekend",
                                "Diameter beschermconstructie [mm]": "?",
                                "Betonvoet": "?",
                                "Type afwerking": well_state.well_head_protector_subtype
                                if well_state
                                else "Onbekend",
                            },
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
                "color": generate_random_color(),
            }

        return groups

    def write_measuringpoints_to_wells(
        self, monitoringnetwork: gmn_models.GroundwaterMonitoringNet
    ) -> None:
        measuringpoints = gmn_models.MeasuringPoint.objects.filter(
            gmn=monitoringnetwork
        )
        for measuringpoint in measuringpoints:
            self.wells.append(
                measuringpoint.groundwater_monitoring_tube.groundwater_monitoring_well_static
            )

    def _write_data(self, data: dict):
        cur_date = datetime.datetime.now().date()
        date_string = cur_date.strftime("%Y%m%d")

        # Check if fieldforms folder exists
        if not os.path.exists("../fieldforms"):
            os.mkdir("../fieldforms")

        # Store the file locally
        write_location_file(
            data=data, filename=f"../fieldforms/gmw/locations_{date_string}.json"
        )

        # Write local file to FTP
        write_file_to_ftp(
            file=f"../fieldforms/gmw/locations_{date_string}.json",
            remote_filename=f"locations_{date_string}.json",
        )

    def write_subgroups_to_dict(
        self, monitoringnetwork: gmn_models.GroundwaterMonitoringNet
    ) -> dict:
        groups = {}
        for subgroup in monitoringnetwork.subgroups.all():
            groups[subgroup.code] = {
                "name": subgroup.code,
                "color": subgroup.color,
            }

        return groups

    def write_measuringpoints_to_wells_subgroup(
        self, subgroup: gmn_models.Subgroup
    ) -> None:
        measuringpoints = gmn_models.MeasuringPoint.objects.filter(subgroup=subgroup)
        for measuringpoint in measuringpoints:
            self.wells.append(
                measuringpoint.groundwater_monitoring_tube.groundwater_monitoring_well_static
            )

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
