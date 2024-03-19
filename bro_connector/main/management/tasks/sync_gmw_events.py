from django.db import models

import bro_exchange as brx
import os
import datetime
import bisect
import reversion

brx.gmw_replace_request
from main.settings.base import gmw_SETTINGS
from gmw import models
from main.management.tasks.django_tools_bro import *

failed_update_strings = ["failed_once", "failed_twice", "failed_thrice"]


def records_in_registrations(bro_id) -> int:
    return len(models.gmw_registration_log.objects.filter(bro_id=bro_id))


def fix_datetime_string(datetime: str):
    new_datetime = datetime.replace(" ", "T", 1)
    return new_datetime


def check_if_object_id_in_database(object_id: str) -> bool:
    return models.gmw_registration_log.objects.filter(
        object_id_accountable_party=object_id
    ).exists()


def get_event_date(event: models.Event) -> str:
    try:
        date = event.event_date
    except:
        date = None

    return date


def generate_object_id(well: models.GroundwaterMonitoringWellStatic) -> dict:
    """
    Format WID = Well ID + primary key of the well in the database
    """

    return {
        "objectIdAccountableParty": f"WID{well.groundwater_monitoring_well_static_id}"
    }


def get_object_id_accountable_party(
    well: models.GroundwaterMonitoringWellStatic,
) -> dict:
    object_id = {"objectIdAccountableParty": well.nitg_code}
    count = 0
    if object_id["objectIdAccountableParty"] == None:
        object_id = generate_object_id(well)

    while check_if_object_id_in_database(object_id):
        object_id = f"{object_id}{count}"
        count += 1

    return object_id


def unpack_point_geometry(point) -> dict:
    """
    Point geometry to dict {
        'X': xcoord,
        'Y': ycoord,
    }
    """

    coords = {
        "X": point.x,
        "Y": point.y,
    }

    return coords


class GetSourceDocData:
    def __init__(self):
        self.datafile = {}
        self.get_data = DjangoTableToDict()

    def create_delivered_vertical_position_dict(
        self,
        well_static: models.GroundwaterMonitoringWellStatic,
        well_dynamic: models.GroundwaterMonitoringWellDynamic,
    ) -> dict:
        """
        dictionary containing the following items:
            'localVerticalReferencePoint':'obligated',
            'offset':'obligated',
            'verticalDatum':'obligated',
            'groundLevelPosition':'obligated',
            'groundLevelPositioningMethod':'obligated'
        """

        delivered_vertical_position_info = {
            "localVerticalReferencePoint": well_static.local_vertical_reference_point,
            "offset": well_static.well_offset,
            "verticalDatum": well_static.vertical_datum,
            "groundLevelPosition": well_dynamic.ground_level_position,
            "groundLevelPositioningMethod": well_dynamic.ground_level_positioning_method,
        }

        delivered_vertical_position = {
            "deliveredVerticalPosition": delivered_vertical_position_info
        }
        return delivered_vertical_position

    def create_delivered_location_dict(
        self, well_static: models.GroundwaterMonitoringWellStatic
    ) -> dict:
        """
        dictionary containing the following items:
        In RD format.
            X: xcoordinate
            Y: ycoordinate
            horizontalPositioningMethod: horizontalPositioningMethod
        """
        delivered_location_info = unpack_point_geometry(well_static.coordinates)

        delivered_location_info.update(
            {"horizontalPositioningMethod": well_static.horizontal_positioning_method}
        )

        delivered_location = {"deliveredLocation": delivered_location_info}
        return delivered_location

    def create_material_used_dict(
        self,
        tube_static: models.GroundwaterMonitoringTubeStatic,
        tube_dynamic: models.GroundwaterMonitoringTubeDynamic,
    ) -> dict:
        material_used = {
            "materialUsed": {
                "tubePackingMaterial": tube_dynamic.tube_packing_material,
                "tubeMaterial": tube_static.tube_material,
                "glue": tube_dynamic.glue,
            }
        }
        return material_used

    def handle_individual_tube(
        self,
        dynamic_tube: models.GroundwaterMonitoringTubeDynamic,
        tube_number: int,
        sourcedoctype: str,
    ) -> None:
        # Static
        static_tube_data = self.get_data.update_static_tube(
            dynamic_tube.groundwater_monitoring_tube_static
        )
        self.datafile["monitoringTubes"][tube_number] = static_tube_data

        # Dynamic
        dynamic_tube_data = self.get_data.update_dynamic_tube(
            dynamic_tube, sourcedoctype
        )
        self.datafile["monitoringTubes"][tube_number].update(dynamic_tube_data)

        # material used
        material_used = self.create_material_used_dict(
            tube_static=dynamic_tube.groundwater_monitoring_tube_static,
            tube_dynamic=dynamic_tube,
        )
        self.datafile["monitoringTubes"][tube_number].update(material_used)

    def handle_individual_geo_ohm_cable(
        self, geo_ohm_cable: models.GeoOhmCable, tube_number, geo_ohm_number
    ) -> None:
        # Static
        static_tube_data = self.get_data.update_static_geo_ohm_cable(geo_ohm_cable)
        self.datafile["monitoringTubes"][tube_number]["geoOhmCables"][
            geo_ohm_number
        ] = static_tube_data

    def handle_individual_electrode(
        self,
        electrode_static: models.ElectrodeStatic,
        electrode_dynamic: models.ElectrodeDynamic,
        tube_number,
        geo_ohm_number,
        electrode_number,
    ):
        # Static
        static_tube_data = self.get_data.update_static_electrode(electrode_static)
        self.datafile["monitoringTubes"][tube_number]["geoOhmCables"][geo_ohm_number][
            "electrodes"
        ][electrode_number] = static_tube_data

        # Dynamic
        dynamic_tube_data = self.get_data.update_dynamic_electrode(electrode_dynamic)
        self.datafile["monitoringTubes"][tube_number]["geoOhmCables"][geo_ohm_number][
            "electrodes"
        ][electrode_number].update(dynamic_tube_data)

    def handle_dynamic_well(
        self, well_dynamic: models.GroundwaterMonitoringWellDynamic
    ):
        dynamic_well_data = self.get_data.update_dynamic_well(well_dynamic)
        self.datafile.update(dynamic_well_data)

    def handle_dynamic_tube(
        self, tube_dynamic: models.GroundwaterMonitoringTubeDynamic, tube_number
    ):
        tubes_dynamic_data = self.get_data.update_dynamic_tube(tube_dynamic)
        self.datafile["monitoringTubes"][tube_number].update(tubes_dynamic_data)

    def handle_dynamic_electrode(self, electrode_dynamic: models.ElectrodeDynamic):
        electrode_static = GetDjangoObjects.get_electrode_static(
            electrode_dynamic.electrode_static
        )

        geo_ohm_cable = GetDjangoObjects.get_geo_ohm_cable(
            electrode_static.geo_ohm_cable
        )

        tube_static = GetDjangoObjects.get_tube_static(
            geo_ohm_cable.groundwater_monitoring_tube_static
        )

        tubes_static_data = self.get_data.update_static_tube(tube_static)
        self.datafile["monitoringTubes"] = tubes_static_data

        dynamic_electrode_data = self.get_data.update_dynamic_electrode(
            electrode_dynamic
        )
        self.datafile["monitoringTubes"][
            geo_ohm_cable.groundwater_monitoring_tube_static
        ]["geoOhmCables"][geo_ohm_cable.geo_ohm_cable_id]["electrodes"][
            electrode_dynamic.electrode_static
        ].update(
            dynamic_electrode_data
        )

    def execute_for_type(self, source_doc_type, event: models.Event) -> None:
        if source_doc_type == "Construction":
            well_construction_date = get_event_date(event)
            self.datafile.update({"wellConstructionDate": well_construction_date})
            self.construction(event)

        if source_doc_type == "Shortening":
            self.shortening(event)

        if source_doc_type == "Lengthening":
            self.lengthening(event)

        if source_doc_type == "PositionsMeasuring":
            self.positions_measuring(event)

        if source_doc_type == "WellHeadProtector":
            self.well_head_protector(event)

        if source_doc_type == "GroundLevelMeasuring":
            self.ground_level_measuring(event)

        if source_doc_type == "Positions":
            self.positions(event)

        if source_doc_type == "GroundLevel":
            self.ground_level(event)

    def construction(self, event: models.Event) -> None:
        """
        Retrieve all the data from the Django database to make it available for construction generation.
        """
        well_construction_date = get_event_date(event)
        self.datafile.update({"wellConstructionDate": well_construction_date})

        well = event.groundwater_monitoring_well_static

        # Get all static well data
        static_well_data = self.get_data.update_static_well(well)
        self.datafile.update(static_well_data)

        # Get delivered vertical position
        delivered_location = self.create_delivered_location_dict(well)
        self.datafile.update(delivered_location)

        tubes = GetDjangoObjects.get_all_tubes(well)

        self.datafile["monitoringTubes"] = {}

        tube_number = 0

        for tube in tubes:
            tube_dynamic = (
                models.GroundwaterMonitoringTubeDynamic.objects.filter(
                    groundwater_monitoring_tube_static=tube
                )
                .order_by("groundwater_monitoring_tube_dynamic_id")
                .first()
            )

            self.handle_individual_tube(
                dynamic_tube=tube_dynamic,
                tube_number=tube_number,
                sourcedoctype="construction",
            )

            geo_ohm_number = 0

            geo_ohm_cables = GetDjangoObjects.get_all_geo_ohm_cables(tube)

            self.datafile["monitoringTubes"][tube_number]["geoOhmCables"] = {}

            for geo_ohm_cable in geo_ohm_cables:
                electrode_number = 0

                electrodes = GetDjangoObjects.get_all_electrodes(geo_ohm_cable)

                self.handle_individual_geo_ohm_cable(
                    geo_ohm_cable=geo_ohm_cable,
                    tube_number=tube_number,
                    geo_ohm_number=geo_ohm_number,
                )

                self.datafile["monitoringTubes"][tube_number]["geoOhmCables"][
                    geo_ohm_number
                ]["electrodes"] = {}

                for electrode in electrodes:
                    try:
                        electrode_dynamic = models.ElectrodeDynamic.objects.get(
                            electrode_static_id=electrode.electrode_static_id
                        )
                    except models.ElectrodeDynamic.DoesNotExist:
                        electrode_dynamic = models.ElectrodeDynamic.objects.create(
                            electrode_static=electrode,
                            electrode_status="onbekend",
                        )

                    self.handle_individual_electrode(
                        electrode_static=electrode,
                        electrode_dynamic=electrode_dynamic,
                        tube_number=tube_number,
                        geo_ohm_number=geo_ohm_number,
                        electrode_number=electrode_number,
                    )

                    electrode_number += 1

                geo_ohm_number += 1

            tube_number += 1

        self.handle_dynamic_well(event.groundwater_monitoring_well_dynamic)

        delivered_vertical_position = self.create_delivered_vertical_position_dict(
            well_static=event.groundwater_monitoring_well_static,
            well_dynamic=event.groundwater_monitoring_well_dynamic,
        )

        self.datafile.update(delivered_vertical_position)

        self.datafile.update(
            {"numberOfMonitoringTubes": len(self.datafile["monitoringTubes"])}
        )

    def shortening(self, event: models.Event) -> None:
        """
        Retrieve all the data from the Django database to make it available for shortening generation.
        """
        well = models.GroundwaterMonitoringWellStatic.objects.get(
            bro_id=str(event.groundwater_monitoring_well_static)
        )

        # Get all static well data
        static_well_data = self.get_data.update_static_well(well)
        self.datafile.update(static_well_data)

        # Get delivered vertical position
        delivered_location = self.create_delivered_location_dict(well)
        self.datafile.update(delivered_location)

        # There is always only change to one tube
        self.datafile.update({"numberOfTubesShortened": 1})
        self.datafile.update({"numberOfTubesLengthened": 0})

        # Get tube information
        self.datafile["monitoringTubes"] = {}
        self.handle_individual_tube(
            event.groundwater_monitoring_well_tube_dynamic, 0, "shortening"
        )

        tube_static = (
            event.groundwater_monitoring_well_tube_dynamic.groundwater_monitoring_tube_static
        )

        material_used = self.create_material_used_dict(
            tube_static=tube_static,
            tube_dynamic=event.groundwater_monitoring_well_tube_dynamic,
        )
        self.datafile["monitoringTubes"][0].update(material_used)

    def lengthening(self, event: models.Event) -> None:
        """
        Retrieve all the data from the Django database to make it available for lengthening generation.
        """
        well = models.GroundwaterMonitoringWellStatic.objects.get(
            bro_id=str(event.groundwater_monitoring_well_static)
        )

        # Get all static well data
        static_well_data = self.get_data.update_static_well(well)
        self.datafile.update(static_well_data)

        # Get delivered vertical position
        delivered_location = self.create_delivered_location_dict(well)
        self.datafile.update(delivered_location)

        self.datafile.update({"numberOfTubesLengthened": 1})
        self.datafile.update({"numberOfTubesShortened": 0})

        # Get tube information
        self.datafile["monitoringTubes"] = {}
        self.handle_individual_tube(
            event.groundwater_monitoring_well_tube_dynamic, 0, "lengthening"
        )

        tube_static = (
            event.groundwater_monitoring_well_tube_dynamic.groundwater_monitoring_tube_static
        )

        material_used = self.create_material_used_dict(
            tube_static=tube_static,
            tube_dynamic=event.groundwater_monitoring_well_tube_dynamic,
        )
        self.datafile["monitoringTubes"][0].update(material_used)

    def positions_measuring_well(self, event: models.Event) -> None:
        self.handle_dynamic_well(event.groundwater_monitoring_well_dynamic)

        delivered_vertical_position = self.create_delivered_vertical_position_dict(
            well_static=event.groundwater_monitoring_well_static,
            well_dynamic=event.groundwater_monitoring_well_dynamic,
        )

        self.datafile.update(delivered_vertical_position)

        # Get tube event at same time
        tube_event = (
            models.Event.objects.filter(
                groundwater_monitoring_well_dynamic=None,
                groundwater_monitoring_well_static=event.groundwater_monitoring_well_static,
            )
            .order_by("event_date")
            .first()
        )

        try:
            self.datafile["monitoringTubes"] = {}
            self.handle_individual_tube(
                dynamic_tube=tube_event.groundwater_monitoring_well_tube_dynamic,
                tube_number=0,
                sourcedoctype="positions_measuring",
            )
        except:
            self.datafile.update({"numberOfMonitoringTubes": 0})

    def positions_measuring_tube(self, event: models.Event) -> None:
        well = models.GroundwaterMonitoringWellStatic.objects.get(
            bro_id=str(event.groundwater_monitoring_well_static)
        )

        self.datafile["monitoringTubes"] = {}
        self.handle_individual_tube(
            event.groundwater_monitoring_well_tube_dynamic, 0, "positions_measuring"
        )

        # Get well event at same time
        well_event = (
            models.Event.objects.filter(
                groundwater_monitoring_well_tube_dynamic=None,
                groundwater_monitoring_well_static=event.groundwater_monitoring_well_static,
            )
            .order_by("-event_date")
            .first()
        )

        try:
            delivered_vertical_position = self.create_delivered_vertical_position_dict(
                well_static=well,
                well_dynamic=well_event.groundwater_monitoring_well_dynamic,
            )

            self.datafile.update(delivered_vertical_position)
        except:
            pass

    def positions_measuring(self, event: models.Event) -> None:
        """
        Retrieve all the data from the Django database to make it available for positionsmeasuring generation.
        """
        self.datafile.update({"numberOfMonitoringTubes": 1})
        well = models.GroundwaterMonitoringWellStatic.objects.get(
            bro_id=str(event.groundwater_monitoring_well_static)
        )

        # Get all static well data
        static_well_data = self.get_data.update_static_well(well)
        self.datafile.update(static_well_data)

        # Get delivered vertical position
        delivered_location = self.create_delivered_location_dict(well)
        self.datafile.update(delivered_location)

        if event.groundwater_monitoring_well_dynamic != None:
            self.positions_measuring_well(event)

        if event.groundwater_monitoring_well_tube_dynamic != None:
            self.positions_measuring_tube(event)

    def well_head_protector(self, event: models.Event) -> None:
        """
        Retrieve all the data from the Django database to make it available for wellheadprotector generation.
        """
        well = models.GroundwaterMonitoringWellStatic.objects.get(
            bro_id=str(event.groundwater_monitoring_well_static)
        )

        # Get all static well data
        static_well_data = self.get_data.update_static_well(well)
        self.datafile.update(static_well_data)

        # Get delivered vertical position
        delivered_location = self.create_delivered_location_dict(well)
        self.datafile.update(delivered_location)

        self.handle_dynamic_well(event.groundwater_monitoring_well_dynamic)

        delivered_vertical_position = self.create_delivered_vertical_position_dict(
            well_static=event.groundwater_monitoring_well_static,
            well_dynamic=event.groundwater_monitoring_well_dynamic,
        )

        self.datafile.update(delivered_vertical_position)

    def positions(self, event: models.Event) -> None:
        # If the id is given get the information directly
        well = models.GroundwaterMonitoringWellStatic.objects.get(
            bro_id=str(event.groundwater_monitoring_well_static)
        )

        # Get all static well data
        static_well_data = self.get_data.update_static_well(well)
        self.datafile.update(static_well_data)

        # Get delivered vertical position
        delivered_location = self.create_delivered_location_dict(well)
        self.datafile.update(delivered_location)

        if event.groundwater_monitoring_well_dynamic != None:
            self.positions_measuring_well

        if event.groundwater_monitoring_well_tube_dynamic != None:
            self.positions_measuring_tube

    def ground_level_measuring(self, event: models.Event) -> None:
        """
        Retrieve all the data from the Django database to make it available for groundlevelmeasuring generation.
        """
        well = models.GroundwaterMonitoringWellStatic.objects.get(
            bro_id=str(event.groundwater_monitoring_well_static)
        )

        # Get all static well data
        static_well_data = self.get_data.update_static_well(well)
        self.datafile.update(static_well_data)

        # Get delivered vertical position
        delivered_location = self.create_delivered_location_dict(well)
        self.datafile.update(delivered_location)

        self.handle_dynamic_well(event.groundwater_monitoring_well_dynamic)

        delivered_vertical_position = self.create_delivered_vertical_position_dict(
            well_static=event.groundwater_monitoring_well_static,
            well_dynamic=event.groundwater_monitoring_well_dynamic,
        )

        self.datafile.update(delivered_vertical_position)

    def ground_level(self, event: models.Event) -> None:
        """
        Retrieve all the data from the Django database to make it available for groundlevel generation.
        """
        well = models.GroundwaterMonitoringWellStatic.objects.get(
            bro_id=str(event.groundwater_monitoring_well_static)
        )

        # Get all static well data
        static_well_data = self.get_data.update_static_well(well)
        self.datafile.update(static_well_data)

        # Get delivered vertical position
        delivered_location = self.create_delivered_location_dict(well)
        self.datafile.update(delivered_location)

        # If the id is given get the information directly
        if event.groundwater_monitoring_well_dynamic != None:
            self.handle_dynamic_well(event.groundwater_monitoring_well_dynamic)

            delivered_vertical_position = self.create_delivered_vertical_position_dict(
                well_static=event.groundwater_monitoring_well_static,
                well_dynamic=event.groundwater_monitoring_well_dynamic,
            )

            self.datafile.update(delivered_vertical_position)


def validate_source_doc_type(source_doc_type):
    full_source_doc_type = f"GMW_{source_doc_type}"

    # From bro-exchange
    allowed_srcdocs = [
        "GMW_Construction",
        "GMW_WellHeadProtector",
        "GMW_Lengthening",
        "GMW_GroundLevel",
        "GMW_Owner",
        "GMW_Shortening",
        "GMW_Positions",
        "GMW_ElectrodeStatus",
        "GMW_Maintainer",
        "GMW_TubeStatus",
        "GMW_Insertion",
        "GMW_Shift",
        "GMW_Removal",
        "GMW_GroundLevelMeasuring",
        "GMW_PositionsMeasuring",
        "GMW_ConstructionWithHistory",
    ]

    if full_source_doc_type not in allowed_srcdocs:
        raise Exception(f"Invalid source document type: {source_doc_type}")


def set_delivery_accountable_party(
    well: models.GroundwaterMonitoringWellStatic, demo: bool
) -> int:
    if demo == True:
        delivery_accountable_party = 27376655
    else:
        delivery_accountable_party = well.delivery_accountable_party

    return delivery_accountable_party


def create_sourcedocs(
    event: models.Event,
    registrations_dir,
    source_doc_type: str
    # Might want to add a variable for with or without history
):
    """
    Try to create registration sourcedocuments for a well/tube/quality regime
    Registration requests are saved to .xml file in registrations folder
    """

    validate_source_doc_type(source_doc_type)

    well = models.GroundwaterMonitoringWellStatic.objects.get(
        bro_id=event.groundwater_monitoring_well_static
    )
    quality_regime = well.quality_regime

    delivery_accountable_party = set_delivery_accountable_party(
        well, gmw_SETTINGS["demo"]
    )

    # Retrieve general static information of the well
    get_srcdoc_data = GetSourceDocData()

    get_srcdoc_data.execute_for_type(source_doc_type=source_doc_type, event=event)
    srcdocdata = get_srcdoc_data.datafile

    objectIdAccountableParty = get_object_id_accountable_party(well)
    srcdocdata.update(objectIdAccountableParty)

    # Add event date
    event_date = get_event_date(event)
    srcdocdata.update({"eventDate": event_date})

    # How many records are already registered -> change the reference
    records_in_register = records_in_registrations(srcdocdata["broId"])

    request_reference = f"{srcdocdata['broId']}_{source_doc_type}_{records_in_register}"
    # Check what kind of request is required and make as followed.
    # Registrate with history
    try:
        gmw_registration_request = brx.gmw_registration_request(
            srcdoc=f"GMW_{source_doc_type}",
            requestReference=request_reference,
            deliveryAccountableParty=str(delivery_accountable_party),
            qualityRegime=quality_regime,
            broId=srcdocdata["broId"],
            underPrivilege=well.under_privilege,
            srcdocdata=srcdocdata,
        )

        filename = request_reference + ".xml"
        gmw_registration_request.generate()
        gmw_registration_request.write_request(
            output_dir=registrations_dir, filename=filename
        )

        process_status = f"succesfully_generated_{source_doc_type}_request"
        record, created = models.gmw_registration_log.objects.update_or_create(
            bro_id=srcdocdata["broId"],
            event_id=event.change_id,
            levering_type=source_doc_type,
            quality_regime=quality_regime,
            defaults=dict(
                comments=f"succesfully generated {source_doc_type} request",
                date_modified=datetime.datetime.now(),
                validation_status=None,
                process_status=process_status,
                file=filename,
            ),
            object_id_accountable_party=srcdocdata["objectIdAccountableParty"],
        )

    except Exception as e:
        process_status = f"failed_to_generate_source_documents"
        record, created = models.gmw_registration_log.objects.update_or_create(
            bro_id=srcdocdata["broId"],
            event_id=event.change_id,
            levering_type=source_doc_type,
            quality_regime=quality_regime,
            defaults=dict(
                comments=f"Failed to create {source_doc_type} source document: {e}",
                date_modified=datetime.datetime.now(),
                process_status=process_status,
            ),
        )


def create_construction_sourcedocs(
    event: models.Event,
    registrations_dir,
):
    """
    Try to create registration sourcedocuments for a well/tube/quality regime
    Registration requests are saved to .xml file in registrations folder
    """

    well = event.groundwater_monitoring_well_static

    delivery_accountable_party = set_delivery_accountable_party(
        well, gmw_SETTINGS["demo"]
    )

    # Retrieve general static information of the well
    get_srcdoc_data = GetSourceDocData()

    get_srcdoc_data.construction(event)
    srcdocdata = get_srcdoc_data.datafile

    objectIdAccountableParty = get_object_id_accountable_party(well)
    srcdocdata.update(objectIdAccountableParty)

    # Add event date
    event_date = get_event_date(event)
    srcdocdata.update({"eventDate": event_date})

    # How many records are already registered -> change the reference
    records_in_register = records_in_registrations(srcdocdata["broId"])

    request_reference = f"{srcdocdata['broId']}_Construction_{records_in_register}"
    # Check what kind of request is required and make as followed.
    # Registrate with history
    try:
        construction_request = brx.gmw_registration_request(
            srcdoc=f"GMW_Construction",
            requestReference=request_reference,
            deliveryAccountableParty=str(delivery_accountable_party),
            qualityRegime=well.quality_regime,
            srcdocdata=srcdocdata,
            underPrivilege=well.under_privilege,
        )

        filename = request_reference + ".xml"
        construction_request.generate()
        construction_request.write_request(
            output_dir=registrations_dir, filename=filename
        )

        process_status = f"succesfully_generated_Construction_request"
        record, created = models.gmw_registration_log.objects.update_or_create(
            bro_id=srcdocdata["broId"],
            event_id=event.change_id,
            levering_type="Construction",
            quality_regime=well.quality_regime,
            defaults=dict(
                comments=f"succesfully generated Construction request",
                date_modified=datetime.datetime.now(),
                validation_status=None,
                process_status=process_status,
                file=filename,
            ),
            object_id_accountable_party=srcdocdata["objectIdAccountableParty"],
        )

    except Exception as e:
        record, created = models.gmw_registration_log.objects.update_or_create(
            bro_id=srcdocdata["broId"],
            event_id=event.change_id,
            levering_type="Construction",
            quality_regime=well.quality_regime,
            defaults=dict(
                comments=f"Failed to create Construction source document: {e}",
                date_modified=datetime.datetime.now(),
                process_status="failed_to_generate_source_documents",
            ),
        )


def handle_not_valid_or_error(registration_id, validation_info):
    defaults = dict(
        validation_status=validation_info["status"],
        process_status="source_document_validation_succesful",
    )

    try:
        validation_errors = validation_info["errors"]
        comments = "Validated registration document, found errors: {}".format(
            validation_errors
        )

        defaults.update({"comments": comments})
        if (
            "Dit registratieobject heeft de registratiestatus voltooid."
            in validation_errors
        ):
            defaults.update({"levering_status": "geleverd", "levering_id": "onbekend"})

        record, created = models.gmw_registration_log.objects.update_or_create(
            id=registration_id, defaults=defaults
        )
    except Exception as e:
        comments = f"No errors found, details: {e}"

        defaults.update({"comments": comments})

        record, created = models.gmw_registration_log.objects.update_or_create(
            id=registration_id, defaults=defaults
        )


def validate_gmw_registration_request(
    registration_id, registrations_dir, bro_info, demo
):
    """
    Validate generated registration sourcedocuments
    """

    gmw_registration = models.gmw_registration_log.objects.get(id=registration_id)
    file = gmw_registration.file
    source_doc_file = os.path.join(registrations_dir, file)
    payload = open(source_doc_file)

    validation_info = brx.validate_sourcedoc(payload, bro_info, demo=demo, api="v2")
    validation_status = validation_info["status"]

    if validation_info["status"] == "VALIDE":
        comments = "Succesfully validated sourcedocument, no errors"
        record, created = models.gmw_registration_log.objects.update_or_create(
            id=registration_id,
            defaults=dict(
                date_modified=datetime.datetime.now(),
                comments=comments,
                validation_status=validation_status,
                process_status="source_document_validation_succesful",
            ),
        )

    else:
        handle_not_valid_or_error(
            registration_id=registration_id, validation_info=validation_info
        )


def deliver_sourcedocuments(registration_id, registrations_dir, bro_info, demo):
    """
    Deliver generated registration sourcedoc to the BRO
    """

    # Get the registration
    gmw_registration = models.gmw_registration_log.objects.get(id=registration_id)

    # If the delivery fails, use the this to indicate how many attempts were made
    delivery_status = gmw_registration.levering_status
    if delivery_status is None:
        delivery_status_update = "failed_once"
    else:
        position = bisect.bisect_left(failed_update_strings, delivery_status)
        delivery_status_update = failed_update_strings[position + 1]

    try:
        file = gmw_registration.file
        source_doc_file = os.path.join(registrations_dir, file)
        payload = open(source_doc_file)
        request = {file: payload}

        upload_info = brx.upload_sourcedocs_from_dict(
            request,
            user=bro_info["token"]["user"],
            password=bro_info["token"]["pass"],
            project_id=bro_info["projectnummer"],
            demo=demo,
            api=gmw_SETTINGS["api_version"],
        )

        if upload_info == "Error":
            comments = "Error occured during delivery of sourcedocument"
            models.gmw_registration_log.objects.update_or_create(
                id=registration_id,
                defaults={
                    "date_modified": datetime.datetime.now(),
                    "comments": comments,
                    "levering_status": delivery_status_update,
                    "process_status": "failed_to_deliver_sourcedocuments",
                },
            )
        else:
            print(upload_info.text)
            levering_id = upload_info.json()["identifier"]
            delivery_status = upload_info.json()["status"]
            lastchanged = upload_info.json()["lastChanged"]
            comments = "Succesfully delivered registration sourcedocument"

            models.gmw_registration_log.objects.update_or_create(
                id=registration_id,
                defaults={
                    "date_modified": datetime.datetime.now(),
                    "comments": comments,
                    "levering_status": delivery_status,
                    "lastchanged": lastchanged,
                    "levering_id": levering_id,
                    "process_status": "succesfully_delivered_sourcedocuments",
                },
            )

    except Exception as e:
        comments = "Exception occured during delivery of registration sourcedocument: {}".format(
            e
        )
        models.gmw_registration_log.objects.update_or_create(
            id=registration_id,
            defaults={
                "date_modified": datetime.datetime.now(),
                "comments": comments,
                "levering_status": delivery_status_update,
                "process_status": "failed_to_deliver_sourcedocuments",
            },
        )


def update_event_based_on_levering(registration: models.gmw_registration_log) -> None:
    event = models.Event.objects.get(
        change_id=registration.event_id,
    )

    event.delivered_to_bro = True
    event.save(update_fields=["delivered_to_bro"])


def check_delivery_status_levering(registration_id, registrations_dir, bro_info, demo):
    """
    Check the status of a registration delivery
    Logs the status of the delivery in the database
    If delivery is approved, a GroundwaterLevelDossier object is created
    This means the registration process is concluded

    Parameters
    ----------
    registration_id : int
        unique id of the gmw registration in the database.
    bro_info : str
        access token for BRO bronhouderportaal: https://demo.bronhouderportaal-bro.nl/ .
    registrations_dir : str
        directory where registration sourcedocument xml's are stored
    demo : bool, optional.

    Returns
    -------
    None.

    """

    registration = models.gmw_registration_log.objects.get(id=registration_id)
    levering_id = registration.levering_id
    try:
        if gmw_SETTINGS["api_version"] == "v2":
            upload_info = brx.check_delivery_status(
                levering_id,
                token=bro_info["token"],
                demo=demo,
                api="v2",
                project_id=bro_info["projectnummer"],
            )

        else:
            upload_info = brx.check_delivery_status(
                levering_id, token=bro_info["token"], demo=demo
            )

        print(upload_info.json())
        if (
            upload_info.json()["status"] == "DOORGELEVERD"
            and upload_info.json()["brondocuments"][0]["status"] == "OPGENOMEN_LVBRO"
        ):
            record, created = models.gmw_registration_log.objects.update_or_create(
                id=registration_id,
                defaults=dict(
                    bro_id=upload_info.json()["brondocuments"][0]["broId"],
                    levering_status=upload_info.json()["brondocuments"][0]["status"],
                    last_changed=upload_info.json()["lastChanged"],
                    comments="registration request approved",
                    process_status="delivery_approved",
                ),
            )

            # Update the event
            update_event_based_on_levering(registration)

            # Remove the sourcedocument file if delivery is approved
            file = registration.file
            source_doc_file = os.path.join(registrations_dir, file)
            os.remove(source_doc_file)

        else:
            record, created = models.gmw_registration_log.objects.update_or_create(
                id=registration_id,
                defaults=dict(
                    levering_status=upload_info.json()["status"],
                    last_changed=upload_info.json()["lastChanged"],
                    comments="registration request not yet approved",
                ),
            )

    except Exception as e:
        record, created = models.gmw_registration_log.objects.update_or_create(
            id=registration_id,
            defaults=dict(
                comments="Error occured during status check of delivery: {}".format(e)
            ),
        )


def get_registration_process_status(registration_id):
    registration = models.gmw_registration_log.objects.get(id=registration_id)
    process_status = registration.process_status
    return process_status


def get_registration_validation_status(registration_id):
    registration = models.gmw_registration_log.objects.get(id=registration_id)
    validation_status = registration.validation_status
    return validation_status


def delete_existing_failed_registrations(event: models.Event, quality_regime: str):
    if (
        models.gmw_registration_log.objects.filter(
            event_id=event.change_id, quality_regime=quality_regime
        ).exists()
        == True
    ):
        reg = models.gmw_registration_log.objects.get(
            event_id=event.change_id, quality_regime=quality_regime
        )

        if reg.process_status == "failed_to_generate_source_documents":
            reg.delete()


class EventsHandler:
    def __init__(self, registrations_dir):
        self.registrations_dir = registrations_dir

    def create_type_sourcedoc(self, event, event_type: str):
        """
        Possible event_types:
        WellHeadProtector, Lengthening,
        GroundLevel, Owner, Shortening, Positions,
        ElectrodeStatus, Maintainer, TubeStatus,
        Insertion, Shift, Removal, GroundLevelMeasuring,
        PositionsMeasuring, ConstructionWithHistory'

        Construction has its own function.

        """

        well = models.GroundwaterMonitoringWellStatic.objects.get(
            bro_id=event.groundwater_monitoring_well_static
        )

        delete_existing_failed_registrations(event, well.quality_regime)

        create_sourcedocs(
            event=event,
            registrations_dir=self.registrations_dir,
            source_doc_type=f"{event_type}",
        )

    def create_construction_sourcedoc(self, event: models.Event):
        well = event.groundwater_monitoring_well_static

        # Check if there is already a registration for this well
        delete_existing_failed_registrations(event, well.quality_regime)

        create_construction_sourcedocs(
            event=event,
            registrations_dir=self.registrations_dir,
        )


def gmw_create_sourcedocs_wells(registrations_dir):
    """
    Run gmw registrations for all monitoring wells in the database
    Registrations has to be run multiple times to get all tubes registered
    This will not interfere with additions, as a check will be done on registration availibility
    """

    # Pak de construction events, filter welke events al in de BRO staan
    construction_events = GetEvents.construction()
    events_handler = EventsHandler(registrations_dir)
    for construction in construction_events:
        events_handler.create_construction_sourcedoc(event=construction)

    electrodeStatus_events = GetEvents.electrodeStatus()
    for electrode_status in electrodeStatus_events:
        events_handler.create_type_sourcedoc(
            event=electrode_status, event_type="ElectrodeStatus"
        )

    groundLevel_events = GetEvents.groundLevel()
    for ground_level in groundLevel_events:
        events_handler.create_type_sourcedoc(
            event=ground_level, event_type="GroundLevel"
        )

    groundLevelMeasuring_events = GetEvents.groundLevelMeasuring()
    for ground_level_measuring in groundLevelMeasuring_events:
        events_handler.create_type_sourcedoc(
            event=ground_level_measuring, event_type="GroundLevelMeasuring"
        )

    insertion_events = GetEvents.insertion()
    for insertion in insertion_events:
        events_handler.create_type_sourcedoc(event=insertion, event_type="Insertion")

    lengthening_events = GetEvents.lengthening()
    for lengthening in lengthening_events:
        events_handler.create_type_sourcedoc(
            event=lengthening, event_type="Lengthening"
        )

    maintainer_events = GetEvents.maintainer()
    for maintainer in maintainer_events:
        events_handler.create_type_sourcedoc(event=maintainer, event_type="Maintainer")

    owner_events = GetEvents.owner()
    for owner in owner_events:
        events_handler.create_type_sourcedoc(events=owner, event_type="Owner")

    positionsMeasuring_events = GetEvents.positionsMeasuring()
    for positions_measuring in positionsMeasuring_events:
        events_handler.create_type_sourcedoc(
            event=positions_measuring, event_type="PositionsMeasuring"
        )

    positions_events = GetEvents.positions()
    for position in positions_events:
        events_handler.create_type_sourcedoc(event=position, event_type="Positions")

    shift_events = GetEvents.shift()
    for shift in shift_events:
        events_handler.create_type_sourcedoc(events=shift, event_type="Shift")

    shortening_events = GetEvents.shortening()
    for shortening in shortening_events:
        events_handler.create_type_sourcedoc(event=shortening, event_type="Shortening")

    tubeStatus_events = GetEvents.tubeStatus()
    for tube_status in tubeStatus_events:
        events_handler.create_type_sourcedoc(event=tube_status, event_type="TubeStatus")

    wellHeadProtector_events = GetEvents.wellHeadProtector()
    for well_head_protector in wellHeadProtector_events:
        events_handler.create_type_sourcedoc(
            event=well_head_protector, event_type="WellHeadProtector"
        )


def delivered_but_not_approved(registration):
    """
    Checks if a registration is delivered but not yet approved.
    """
    if (
        get_registration_process_status(registration.id)
        == "succesfully_delivered_sourcedocuments"
        and registration.levering_status != "OPGENOMEN_LVBRO"
        and registration.levering_id is not None
    ):
        return True

    else:
        return False


def gmw_check_existing_registrations(bro_info, registrations_dir, demo):
    """
    This function loops over all exists registrations in the database
    Depending on the status one of the following actions is carried out:
        - The sourcedocument for the registration is validated
        - The sourcedocument is delivered to the BRO
        - The status of a delivery is checked
        - If a delivery failed, it may be attempted again up to three times

    Parameters
    ----------
    bro_info : str
        access token for BRO bronhouderportaal: https://demo.bronhouderportaal-bro.nl/ .
    registrations_dir : str
        directory where registration sourcedocument xml's are stored
    demo : bool
        True for test environment, False for production

    Returns
    -------
    None.

    """
    # Get all the current registrations, order by event id so construction is handled first.
    gmw_registrations = models.gmw_registration_log.objects.all()

    # Get BRO-IDs
    for registration in gmw_registrations:
        # We check the status of the registration and either validate/deliver/check status/do nothing
        registration_id = registration.id

        event = models.Event.objects.get(change_id=registration.event_id)
        if event.delivered_to_bro:
            # Already delivered, so can skip.
            continue

        source_doc_type = registration.levering_type

        if delivered_but_not_approved(registration):
            # The registration has been delivered, but not yet approved
            status = check_delivery_status_levering(
                registration_id, registrations_dir, bro_info, demo
            )
            continue

        if (
            get_registration_process_status(registration_id)
            == f"succesfully_generated_{source_doc_type}_request"
        ):
            validation_status = validate_gmw_registration_request(
                registration_id,
                registrations_dir,
                bro_info,
                demo,
            )

        # If an error occured during validation, try again
        # Failed to validate sourcedocument doesn't mean the document is valid/invalid
        # It means something went wrong during validation (e.g BRO server error)
        # Even if a document is invalid, the validation process has succeeded and won't be reattempted
        elif (
            get_registration_process_status(registration_id)
            == "failed_to_validate_source_documents"
            or get_registration_validation_status(registration_id) != "VALIDE"
        ):
            # If we failed to validate the sourcedocument, try again
            # TODO maybe limit amount of retries? Do not expect validation to fail multiple times..
            validation_status = validate_gmw_registration_request(
                registration_id,
                registrations_dir,
                bro_info,
                demo,
            )

        # If validation is succesful and the document is valid, try a delivery
        if (
            get_registration_process_status(registration_id)
            == "source_document_validation_succesful"
            and get_registration_validation_status(registration_id) == "VALIDE"
        ):
            delivery_status = deliver_sourcedocuments(
                registration_id,
                registrations_dir,
                bro_info,
                demo,
            )

        # If delivery is succesful, check the status of the delivery
        if (
            get_registration_process_status(registration_id)
            == "succesfully_delivered_sourcedocuments"
            and registration.levering_status != "OPGENOMEN_LVBRO"
            and registration.levering_id is not None
        ):
            # The registration has been delivered, but not yet approved
            status = check_delivery_status_levering(
                registration_id,
                registrations_dir,
                bro_info,
                demo,
            )

        # If the delivery failed previously, we can retry
        if (
            get_registration_process_status(registration_id)
            == "failed_to_deliver_sourcedocuments"
        ):
            # This will not be the case on the first try
            if registration.levering_status == "failed_thrice":
                # TODO report with mail?
                continue
            else:
                delivery_status = deliver_sourcedocuments(
                    registration_id,
                    registrations_dir,
                    bro_info,
                    demo,
                )

        # Make sure the event is adjusted correctly if the information is delivered to the BRO.
        if registration.levering_status == "OPGENOMEN_LVBRO":
            with reversion.create_revision():
                event.delivered_to_bro = True
                event.save(update_fields=["delivered_to_bro"])

                reversion.set_comment("Delivered the information to the BRO.")
