from typing import List, Optional
import json

from gmw import models as gmw_models
from frd import models as frd_models
from gmn import models as gmn_models

maximum_difference_ratio = 0.2

input_field_options = {
    "weerstand": {
        "type": "number",
        "name": "Weerstand"
    },
    "opmerking": {
        "type": "text",
        "name": "Opmerking"
    }
}

# From the FieldForm Github
def write_location_file(data, fname):
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
    with open(fname, "w") as outfile:
        json.dump(data, outfile, indent=2)


def generate_sublocation_fields(tube) -> List[str]:
    try:
        frd = frd_models.FormationResistanceDossier.objects.get(
            groundwater_monitoring_tube = tube
        )
    except frd_models.FormationResistanceDossier.DoesNotExist:
        return []
    
    configs = []
    for config in frd_models.MeasurementConfiguration.objects.filter(
        formation_resistance_dossier = frd
    ):
        configs.append(config.configuration_name)

    return configs

def calculate_minimum_resistance(formationresistance):
    return round(formationresistance * (1-maximum_difference_ratio), 2)

def generate_min_values(tube) -> List[dict]:
    frd = frd_models.FormationResistanceDossier.objects.get(
        groundwater_monitoring_tube = tube
    )
    min_values = {}
    for config in frd_models.MeasurementConfiguration.objects.filter(
        formation_resistance_dossier = frd
    ):
        # Get most recent measurement 
        measurement = frd_models.GeoOhmMeasurementValue.objects.filter(
            measurement_configuration = config
        ).order_by("-datetime").first()

        if measurement is None:
            # Set Max value if no previous measurements are known.
            min_values.update({f"weerstand_{config.configuration_name}": 0})
        else:
            minimum = calculate_minimum_resistance(measurement.formationresistance)
            min_values.update({f"weerstand_{config.configuration_name}": minimum})

    return min_values

def calculate_maximum_resistance(formationresistance):
    return round(formationresistance * (1+maximum_difference_ratio), 2)

def generate_max_values(tube) -> List[dict]:
    frd = frd_models.FormationResistanceDossier.objects.get(
        groundwater_monitoring_tube = tube
    )
    max_values = {}
    for config in frd_models.MeasurementConfiguration.objects.filter(
        formation_resistance_dossier = frd
    ):
        # Get most recent measurement 
        measurement = frd_models.GeoOhmMeasurementValue.objects.filter(
            measurement_configuration = config
        ).order_by("-datetime").first()

        if measurement is None:
            # Set Max value if no previous measurements are known.
            max_values.update({f"weerstand_{config.configuration_name}": 10000})
        else:
            maximum = calculate_maximum_resistance(measurement.formationresistance)
            max_values.update({f"weerstand_{config.configuration_name}": maximum})

    return max_values

def create_sublocation_dict(tube: gmw_models.GroundwaterMonitoringTubeStatic) -> dict:
    filter_name = tube.__str__()

    return {
        f"{filter_name}": {
            "lat": tube.groundwater_monitoring_well_static.coordinates.y,
            "lon": tube.groundwater_monitoring_well_static.coordinates.x,
            "inputfields": generate_sublocation_fields(tube),
            "min_values": generate_min_values(tube),
            "max_values": generate_max_values(tube),
        },
    }

class FieldFormGenerator:
    inputfields: List[dict]

    # QuerySets
    monitoringnetworks: Optional[List[gmn_models.GroundwaterMonitoringNet]]
    wells: Optional[List[gmw_models.GroundwaterMonitoringWellStatic]]


    def update_postfix(self, config: frd_models.MeasurementConfiguration) -> None:
        self.post_fix = config.configuration_name
        self.config = config

    def generate_inputfields(self) -> dict:
        input_field = {}
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
                    f"opmerking_{self.post_fix}"
                ],
                "name": name,
            }
        }

    def create_location_dict(self) -> None:
        locations = {}
        for well in self.wells:  
            tubes = gmw_models.GroundwaterMonitoringTubeStatic.objects.filter(
                groundwater_monitoring_well_static = well
            )
            for tube in tubes:
                if tube.number_of_geo_ohm_cables > 0:
                    sublocation = create_sublocation_dict(tube)

                    if hasattr(self, "group_name"):
                        sublocation.update({"group": self.group_name})

                    locations.update(sublocation)
        
        return locations

    def _set_current_group(self, group_name: str):
        self.group_name = group_name

    def _flush_wells(self):
        self.wells = []

    def write_monitoringnetworks_to_dict(self) -> List[str]:
        groups = []
        for monitoring_network in gmn_models.GroundwaterMonitoringNet.objects.all():
            groups.append(str(monitoring_network.name))
        
        return groups

    def write_measuringpoints_to_wells(self, monitoringnetwork: gmn_models.GroundwaterMonitoringNet) -> None:
        measuringpoints = gmn_models.MeasuringPoint.objects.filter(
            gmn = monitoringnetwork
        )
        for measuringpoint in measuringpoints:
            self.wells.append(measuringpoint.groundwater_monitoring_tube.groundwater_monitoring_well_static)

    def generate(self):
        data = {}
        configs = frd_models.MeasurementConfiguration.objects.all().distinct("configuration_name")
        # For all configurations generate the inputfields.
        inputfields = {}
        inputfield_groups = {}
        for config in configs:
            self.update_postfix(config)
            inputfields.update(self.generate_inputfields())
            inputfield_groups.update(self.generate_inputfield_groups())

        data["inputfield_groups"] = inputfield_groups
        data["inputfields"] = inputfields


        if hasattr(self, "monitoringnetworks"):
            data["groups"] = self.write_monitoringnetworks_to_dict()
            for monitoringnetwork in self.monitoringnetworks:
                self._flush_wells()
                self._set_current_group(str(monitoringnetwork.name))
                self.write_measuringpoints_to_wells(monitoringnetwork)
                data["locations"] = self.create_location_dict()
                print(data)

        elif hasattr(self, "wells"):
            data["locations"] = self.create_location_dict()
            print(data)

        else:
            # If nothing has been deliverd, create for all wells without a grouping.
            self.wells = gmw_models.GroundwaterMonitoringWellStatic.objects.all()
            data["locations"] = self.create_location_dict()
            print(data)

            
                        


