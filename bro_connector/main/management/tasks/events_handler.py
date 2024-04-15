import datetime
from django.utils import timezone
from gmw.models import (
    GroundwaterMonitoringWellStatic,
    GroundwaterMonitoringWellDynamic,
    GroundwaterMonitoringTubeDynamic,
    GroundwaterMonitoringTubeStatic,
    GeoOhmCable,
    ElectrodeDynamic,
    ElectrodeStatic,
    Event,
)


# FORMULAS USED IN HISTORIE_OPHALEN COMMAND DJANGO ZEELAND
def slice(sourcedict, string):
    newdict = {}
    for key in sourcedict.keys():
        if key.startswith(string):
            newdict[key.split(string)[1]] = sourcedict[key]
    return newdict


def well_dynamic(gmwd, updates_dict):
    gmwd.ground_level_stable = updates_dict.get(
        "groundLevelStable", gmwd.ground_level_stable
    )
    gmwd.well_stability = updates_dict.get("wellStability", gmwd.well_stability)
    gmwd.owner = updates_dict.get("owner", gmwd.owner)
    gmwd.maintenance_responsible_party = updates_dict.get(
        "maintenanceResponsibleParty", gmwd.maintenance_responsible_party
    )
    gmwd.well_head_protector = updates_dict.get(
        "wellHeadProtector", gmwd.well_head_protector
    )
    gmwd.ground_level_position = updates_dict.get(
        "groundLevelPosition", gmwd.ground_level_position
    )
    gmwd.ground_level_positioning_method = updates_dict.get(
        "groundLevelPositioningMethod", gmwd.ground_level_positioning_method
    )
    return gmwd

def remove_prefix_from_keys(dictionary, prefix):
    """
    Remove a specified prefix from keys in a dictionary.

    Parameters:
        dictionary (dict): The dictionary to process.
        prefix (str): The prefix to remove from keys.

    Returns:
        dict: A new dictionary with the specified prefix removed from keys.
    """
    new_dict = {}
    for key, value in dictionary.items():
        if key.startswith(prefix):
            new_key = key[len(prefix):]
            new_dict[new_key] = value
        else:
            new_dict[key] = value
    return new_dict

def tube_dynamic(gmtd, updates_dict):
    gmtd.tube_top_diameter = updates_dict.get("tubeTopDiameter", gmtd.tube_top_diameter)
    gmtd.variable_diameter = updates_dict.get(
        "variableDiameter", gmtd.variable_diameter
    )
    gmtd.tube_status = updates_dict.get("tubeStatus", gmtd.tube_status)
    gmtd.tube_top_position = updates_dict.get("tubeTopPosition", gmtd.tube_top_position)
    gmtd.tube_top_positioning_method = updates_dict.get(
        "tubeTopPositioningMethod", gmtd.tube_top_positioning_method
    )
    gmtd.tube_packing_material = updates_dict.get(
        "tubePackingMaterial", gmtd.tube_packing_material
    )
    gmtd.glue = updates_dict.get("glue", gmtd.glue)
    gmtd.plain_tube_part_length = updates_dict.get(
        "plainTubePartLength", gmtd.plain_tube_part_length
    )
    gmtd.inserted_part_diameter = updates_dict.get(
        "insertedPartDiameter", gmtd.inserted_part_diameter
    )
    gmtd.inserted_part_length = updates_dict.get(
        "insertedPartLength", gmtd.inserted_part_length
    )
    gmtd.inserted_part_material = updates_dict.get(
        "insertedPartMaterial", gmtd.inserted_part_material
    )
    return gmtd


def electrode_dynamic(eled, updates_dict):
    eled.electrode_number = updates_dict.get("electrodeNumber", eled.electrode_number)
    eled.electrode_status = updates_dict.get("electrodeStatus", eled.electrode_status)
    return eled


def get_mytimezone_date(original_datetime):
    try:
        new_datetime = datetime.strptime(original_datetime, "%Y-%m-%d")
        tz = timezone.get_current_timezone()
        timezone_datetime = timezone.make_aware(new_datetime, tz, True)
    except:
        timezone_datetime = None
    return timezone_datetime


def create_construction_event(gmw_dict, groundwater_monitoring_well_static) -> Event:
    if "construction_date" in gmw_dict:
        date = gmw_dict["construction_date"]

    elif "construction_year" in gmw_dict:
        date = gmw_dict["construction_year"]

    else:
        date = None

    event = Event.objects.update_or_create(
        event_name="constructie",
        groundwater_monitoring_well_static=groundwater_monitoring_well_static,
        defaults={
            "event_date": date,
            "groundwater_monitoring_well_dynamic": GroundwaterMonitoringWellDynamic.objects.filter(
                groundwater_monitoring_well_static=groundwater_monitoring_well_static
            ).first(),
            "delivered_to_bro": True,
        },
    )
    return event


def get_electrode_static(groundwater_monitoring_well, tube_number):
    try:
        eles_id = ElectrodeStatic.objects.filter(
            geo_ohm_cable=GeoOhmCable.objects.filter(
                groundwater_monitoring_tube_static=GroundwaterMonitoringTubeStatic.objects.get(
                    groundwater_monitoring_well_static=groundwater_monitoring_well,
                    tube_number=tube_number,
                )
            )
        )
    except:
        print(groundwater_monitoring_well, tube_number)

    return eles_id

def get_tube_static(groundwater_monitoring_well, tube_number):
    gmts_id = GroundwaterMonitoringTubeStatic.objects.get(
        groundwater_monitoring_well_static=groundwater_monitoring_well,
        tube_number=tube_number,
    )
    return gmts_id

def convert_event_date_str_to_datetime(event: Event) -> datetime:
    try:
        date = datetime.datetime.strptime(event.event_date,'%Y-%m-%d')
    except ValueError:
        date = datetime.datetime.strptime(event.event_date,'%Y')
    except TypeError:
        date = datetime.datetime.strptime("1900-01-01",'%Y-%m-%d')

    return date

class Updater:
    def __init__(self, gmw_dict, groundwater_monitoring_well):
        self.gmw_dict = gmw_dict
        self.groundwater_monitoring_well_static = groundwater_monitoring_well
        self.event_number = 1
        self.prefix = f"event_{str(self.event_number)}_"
        self.event_updates = []
        self.event = None

    def reset_event(self):
        self.event_number = 1

    def increment_event(self):
        self.event_number = self.event_number + 1
        self.prefix = f"event_{str(self.event_number)}_"

    def read_updates(self):
        self.event_updates = slice(self.gmw_dict, self.prefix)

    def create_base(self):
        if "date" in self.event_updates:
            date = self.event_updates["date"]

        elif "year" in self.event_updates:
            date = self.event_updates["year"]

        else:
            raise Exception(f"date/year not found in dict: {self.event_updates}")

        event = Event.objects.filter(
            event_name=self.event_updates["eventName"],
            event_date=date,
            groundwater_monitoring_well_static=self.groundwater_monitoring_well_static,
            delivered_to_bro=True,
        ).first()
        if event:
            self.event = event
        else:
            self.event = Event.objects.create(
                event_name=self.event_updates["eventName"],
                event_date=date,
                groundwater_monitoring_well_static=self.groundwater_monitoring_well_static,
                delivered_to_bro=True,
            )

    def intermediate_events(self):
        # Create a base event
        self.read_updates()
        self.create_base()

        # Update tables accordingly
        TableUpdater.fill(
            self.groundwater_monitoring_well_static, self.event, self.event_updates
        )
        self.increment_event()


class TableUpdater(Updater):
    def fill(well_static, event, updates):
        if "wellData" in updates:
            TableUpdater.well_data(well_static, event, updates)

        if "1_tubeData" in updates:
            TableUpdater.tube_data(well_static, event, updates)

        if "electrodeData" in updates:
            TableUpdater.electrode_data(well_static, event, updates)

    def tube_data(well_static: GroundwaterMonitoringWellStatic, event: Event, updates):
        data_num = 1
        while True:
            prefix = f"{data_num}_"
            if f"{prefix}tubeData" not in updates:
                break

            # Find which filter needs to be adjusted
            new_gmts = GroundwaterMonitoringTubeStatic.objects.get(
                tube_number=updates[f"{prefix}tubeNumber"],
                groundwater_monitoring_well_static=well_static,
            )
            date = convert_event_date_str_to_datetime(event)
            
            try:
                # Clone row and make new primary key with save
                new_gmtd = GroundwaterMonitoringTubeDynamic.objects.get(
                    groundwater_monitoring_tube_static=new_gmts,
                    date_from = date,
                )
            except GroundwaterMonitoringTubeDynamic.DoesNotExist:
                # Clone row and make new primary key with save
                new_gmtds = GroundwaterMonitoringTubeDynamic.objects.filter(
                    groundwater_monitoring_tube_static=new_gmts
                )
                    # This assumes the gmwds are sorted based on creation date.
                if len(new_gmtds) == 1:
                    new_gmtd = new_gmtds.first()
                    new_gmtd.groundwater_monitoring_tube_dynamic_id = None

                elif len(new_gmtds) > 1:
                    new_gmtd = new_gmtds.last()
                    new_gmtd.groundwater_monitoring_tube_dynamic_id = None

            # Check what has to be changed
            updates = remove_prefix_from_keys(updates, prefix)
            new_gmtd = tube_dynamic(new_gmtd, updates)
            new_gmtd.date_from = date
            # Save and add new key to event
            new_gmtd.save()

            #  Add to the event
            event.groundwater_monitoring_tube_dynamic = new_gmtd
            event.save()

            data_num += 1

    def electrode_data(well_static: GroundwaterMonitoringWellStatic, event: Event, updates):
        date =convert_event_date_str_to_datetime(event)
        print(updates)
        exit()
        try:
            # Clone row and make new primary key with save
            new_eled = ElectrodeDynamic.objects.get(
                electrode_static=get_electrode_static(
                    well_static, updates["tubeNumber"]
                ),
                date_from = date,
            )
        except ElectrodeDynamic.DoesNotExist:
            # Clone row and make new primary key with save
            new_eleds = ElectrodeDynamic.objects.filter(
                electrode_static=get_electrode_static(
                    well_static, updates["tubeNumber"]
                )
            )

            # This assumes the gmwds are sorted based on creation date.
            if len(new_eleds) == 1:
                new_eled = new_eleds.first()
                new_eled.electrode_dynamic_id = None

            elif len(new_eleds) > 1:
                new_eled = new_eleds.last()
                new_eled.electrode_dynamic_id = None

            else:
                raise Exception(
                    "No Groundwater Monitoring Tube Dynamic Tables found for this GMT: ",
                    get_tube_static(well_static, updates["tubeNumber"]),
                )

        # Check what has to be changed
        new_eled = electrode_dynamic(new_eled, updates)
        new_eled.date_from = date
        # Save and add new key to event
        new_eled.save()

        # Add to the event.
        event.electrode_dynamic = new_eleds
        event.save()

    def well_data(well_static: GroundwaterMonitoringWellStatic, event: Event, updates):
        # Clone row and make new primary key with save
        date =convert_event_date_str_to_datetime(event)

        try:
            new_gmwd = GroundwaterMonitoringWellDynamic.objects.get(
                groundwater_monitoring_well_static=well_static,
                date_from = date,
            )
        except GroundwaterMonitoringWellDynamic.DoesNotExist:
            new_gmwds = GroundwaterMonitoringWellDynamic.objects.filter(
                groundwater_monitoring_well_static=well_static
            )
            if len(new_gmwds) == 1:
                new_gmwd = new_gmwds.first()
                new_gmwd.groundwater_monitoring_well_dynamic_id = None

            elif len(new_gmwds) > 1:
                new_gmwd = new_gmwds.last()
                new_gmwd.groundwater_monitoring_well_dynamic_id = None

            else:
                raise Exception(
                    "No Groundwater Monitoring Well Dynamic Tables found for this GMW: ",
                    well_static,
                )

        # Check what has to be changed
        new_gmwd = well_dynamic(new_gmwd, updates)
        new_gmwd.date_from = date
        # Save and add new key to event
        new_gmwd.save()

        # Add to the event.
        event.groundwater_monitoring_well_dynamic = new_gmwd
        event.save()


def get_removal_event(gmw_dict, groundwater_monitoring_well_static):
    event = Event.objects.create(
        event_name="removal",
        event_date=get_mytimezone_date(
            gmw_dict.get("removal_date", None),
        ),
        groundwater_monitoring_well_static=groundwater_monitoring_well_static,
        groundwater_monitoring_well_dynamic=GroundwaterMonitoringWellDynamic.objects.filter(
            groundwater_monitoring_well=groundwater_monitoring_well_static
        ).first(),
        delivered_to_bro=True,
    )
    event.save()
