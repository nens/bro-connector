import bisect
import datetime
import logging
import os

import bro_exchange as brx
import reversion
from bro.models import Organisation
from gmw import models
from main.management.tasks.django_tools_bro import (
    EVENTNAME2TYPE,
    DjangoTableToDict,
    getAllIntermediateEvents,
    getConstruction,
)
from main.settings.base import BASE_DIR, ENV

logger = logging.getLogger(__name__)

failed_update_strings = ["failed_once", "failed_twice", "failed_thrice"]

REGISTRATIONS_DIR = f"{BASE_DIR}/gmw/registrations/"


def _is_demo():
    if ENV == "production":
        return False
    return True


def _get_token(owner: Organisation):
    return {
        "user": owner.bro_user,
        "pass": owner.bro_token,
    }


def form_bro_info(well: models.GroundwaterMonitoringWellStatic) -> dict:
    return {
        "token": _get_token(well.delivery_accountable_party),
        "projectnummer": well.project_number,
    }


def bro_info_missing(bro_info: dict, gmn_name: str) -> bool:
    skip = False
    if bro_info["projectnummer"] is None:
        skip = True
        logger.info(f"No projectnumber for GMN ({gmn_name})")

    if bro_info["token"]["user"] is None or bro_info["token"]["pass"] is None:
        skip = True
        logger.info(f"No user or pass for GMN ({gmn_name})")

    return skip


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
    if not event or not event.event_date:
        return None

    return event.event_date.strftime("%Y-%m-%d")


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
    object_id = {"objectIdAccountableParty": well.internal_id}
    count = 0
    if object_id["objectIdAccountableParty"] is None:
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
        sourcedoctype: str,
    ) -> dict:
        # Static
        static_tube_data = self.get_data.update_static_tube(
            dynamic_tube.groundwater_monitoring_tube_static
        )

        # Dynamic
        dynamic_tube_data = self.get_data.update_dynamic_tube(
            dynamic_tube, sourcedoctype
        )
        static_tube_data.update(dynamic_tube_data)

        # material used
        material_used = self.create_material_used_dict(
            tube_static=dynamic_tube.groundwater_monitoring_tube_static,
            tube_dynamic=dynamic_tube,
        )
        static_tube_data.update(material_used)
        return static_tube_data

    def handle_individual_geo_ohm_cable(
        self, geo_ohm_cable: models.GeoOhmCable
    ) -> dict:
        # Static
        return self.get_data.update_static_geo_ohm_cable(geo_ohm_cable)

    def handle_individual_electrode(
        self,
        electrode_static: models.Electrode,
    ) -> dict:
        return self.get_data.update_static_electrode(electrode_static)

    def handle_dynamic_well(
        self, well_dynamic: models.GroundwaterMonitoringWellDynamic
    ):
        dynamic_well_data = self.get_data.update_dynamic_well(well_dynamic)
        self.datafile.update(dynamic_well_data)

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

        if source_doc_type == "Removal":
            well = event.groundwater_monitoring_well_static
            self.datafile.update(
                {
                    "requestReference": f"{well.internal_id}_Removal_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                }
            )
            self.datafile.update({"broId": well.bro_id})
            self.datafile.update({"wellRemovalDate": get_event_date(event)})

    def construction(self, event: models.Event) -> None:
        """
        Retrieve all the data from the Django database to make it available for construction generation.
        """
        well_construction_date = get_event_date(event)
        self.datafile.update({"wellConstructionDate": well_construction_date})

        well = event.groundwater_monitoring_well_static
        self.datafile.update({"id": well.groundwater_monitoring_well_static_id})

        # Get all static well data
        static_well_data = self.get_data.update_static_well(well)
        static_well_data.update(
            {
                "requestReference": f"{well.internal_id}_Construction_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            }
        )
        self.datafile.update(static_well_data)

        # Get delivered vertical position
        delivered_location = self.create_delivered_location_dict(well)
        self.datafile.update(delivered_location)

        self.datafile["monitoringTubes"] = []
        for tube in well.tube.all():
            tube_dynamic = tube.state.order_by("date_from").first()
            tube_data = self.handle_individual_tube(
                dynamic_tube=tube_dynamic,
                sourcedoctype="construction",
            )
            geo_ohm_cables = []
            for geo_ohm_cable in tube.geo_ohm_cable.all():
                geo_ohm_cable_data = self.handle_individual_geo_ohm_cable(
                    geo_ohm_cable=geo_ohm_cable,
                )
                electrodes = []
                for electrode in geo_ohm_cable.electrode.all():
                    electrode_data = self.handle_individual_electrode(
                        electrode_static=electrode,
                    )
                    electrodes.append(electrode_data)
                geo_ohm_cable_data["electrodes"] = electrodes
                geo_ohm_cables.append(geo_ohm_cable_data)
            tube_data["geoOhmCables"] = geo_ohm_cables
            self.datafile["monitoringTubes"].append(tube_data)

        initial_well_state = well.state.order_by("date_from").first()
        self.handle_dynamic_well(initial_well_state)
        delivered_vertical_position = self.create_delivered_vertical_position_dict(
            well_static=well,
            well_dynamic=initial_well_state,
        )

        self.datafile.update(delivered_vertical_position)

        self.datafile.update(
            {"numberOfMonitoringTubes": len(self.datafile["monitoringTubes"])}
        )

    def shortening(self, event: models.Event) -> None:
        """
        Retrieve all the data from the Django database to make it available for shortening generation.
        """
        well = event.groundwater_monitoring_well_static
        # Get all static well data
        static_well_data = self.get_data.update_static_well(well)
        static_well_data.update(
            {
                "requestReference": f"{well.internal_id}_Shortening_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            }
        )
        self.datafile.update(static_well_data)

        # Get delivered vertical position
        delivered_location = self.create_delivered_location_dict(well)
        self.datafile.update(delivered_location)

        # There is always only change to one tube
        self.datafile.update(
            {
                "numberOfTubesShortened": event.groundwater_monitoring_tube_dynamic.count()
            }
        )
        self.datafile.update({"numberOfTubesLengthened": 0})

        # Get tube information
        self.datafile["monitoringTubes"] = []
        for tube_state in event.groundwater_monitoring_tube_dynamic.all():
            tube_static: models.GroundwaterMonitoringTubeStatic = (
                tube_state.groundwater_monitoring_tube_static
            )
            tube_data = self.handle_individual_tube(tube_state, "shortening")
            material_used = self.create_material_used_dict(
                tube_static=tube_static,
                tube_dynamic=tube_state,
            )
            tube_data.update(material_used)
            self.datafile["monitoringTubes"].append(tube_data)

    def lengthening(self, event: models.Event) -> None:
        """
        Retrieve all the data from the Django database to make it available for lengthening generation.
        """
        well = event.groundwater_monitoring_well_static

        # Get all static well data
        static_well_data = self.get_data.update_static_well(well)
        static_well_data.update(
            {
                "requestReference": f"{well.internal_id}_Lengthening_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            }
        )
        self.datafile.update(static_well_data)

        # Get delivered vertical position
        delivered_location = self.create_delivered_location_dict(well)
        self.datafile.update(delivered_location)

        self.datafile.update(
            {
                "numberOfTubesLengthened": event.groundwater_monitoring_tube_dynamic.count()
            }
        )
        self.datafile.update({"numberOfTubesShortened": 0})

        # Get tube information
        self.datafile["monitoringTubes"] = {}
        for tube_state in event.groundwater_monitoring_tube_dynamic.all():
            tube_static: models.GroundwaterMonitoringTubeStatic = (
                tube_state.groundwater_monitoring_tube_static
            )
            tube_data = self.handle_individual_tube(tube_state, "lengthening")
            material_used = self.create_material_used_dict(
                tube_static=tube_static,
                tube_dynamic=tube_state,
            )
            tube_data.update(material_used)
            self.datafile["monitoringTubes"].append(tube_data)

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
            self.datafile["monitoringTubes"] = []
            tube_data = self.handle_individual_tube(
                dynamic_tube=tube_event.groundwater_monitoring_well_tube_dynamic,
                sourcedoctype="positions_measuring",
            )
            self.datafile["monitoringTubes"].append(tube_data)
        except Exception as e:
            logger.exception(e)
            self.datafile.update({"numberOfMonitoringTubes": 0})

    def positions_measuring_tube(
        self,
        tube_state: models.GroundwaterMonitoringTubeDynamic,
        well_state: models.GroundwaterMonitoringWellDynamic,
    ) -> None:
        well = tube_state.groundwater_monitoring_tube_static.groundwater_monitoring_well_static

        self.datafile["monitoringTubes"] = []
        tube_data = self.handle_individual_tube(
            tube_state,
            "positions_measuring",
        )

        try:
            delivered_vertical_position = self.create_delivered_vertical_position_dict(
                well_static=well,
                well_dynamic=well_state,
            )
            self.datafile["monitoringTubes"].append(tube_data)
            self.datafile.update(delivered_vertical_position)
        except Exception as e:
            logger.exception(e)
            pass

    def positions_measuring(self, event: models.Event) -> None:
        """
        Retrieve all the data from the Django database to make it available for positionsmeasuring generation.
        """
        well = models.GroundwaterMonitoringWellStatic.objects.get(
            bro_id=str(event.groundwater_monitoring_well_static)
        )

        # Get all static well data
        static_well_data = self.get_data.update_static_well(well)
        static_well_data.update(
            {
                "requestReference": f"{well.internal_id}_Measuring_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            }
        )
        self.datafile.update(static_well_data)

        # Get delivered vertical position
        delivered_location = self.create_delivered_location_dict(well)
        self.datafile.update(delivered_location)

        if event.groundwater_monitoring_well_dynamic is not None:
            self.positions_measuring_well(event)

        monitoring_tubes = []
        for tube in event.groundwater_monitoring_tube_dynamic.all():
            tube_data = self.positions_measuring_tube(
                tube, event.groundwater_monitoring_well_dynamic
            )
            monitoring_tubes.append(tube_data)

        self.datafile.update({"monitoringTubes": monitoring_tubes})

    def well_head_protector(self, event: models.Event) -> None:
        """
        Retrieve all the data from the Django database to make it available for wellheadprotector generation.
        """
        well = event.groundwater_monitoring_well_static

        # Get all static well data
        static_well_data = self.get_data.update_static_well(well)
        static_well_data.update(
            {
                "requestReference": f"{well.internal_id}_WellHeadProtector_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            }
        )
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
        well = event.groundwater_monitoring_well_static

        # Get all static well data
        static_well_data = self.get_data.update_static_well(well)
        static_well_data.update(
            {
                "requestReference": f"{well.internal_id}_Positions_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            }
        )
        self.datafile.update(static_well_data)

        # Get delivered vertical position
        delivered_location = self.create_delivered_location_dict(well)
        self.datafile.update(delivered_location)

        if event.groundwater_monitoring_well_dynamic is not None:
            self.positions_measuring_well(event)

        for tube in event.groundwater_monitoring_tube_dynamic.all():
            self.positions_measuring_tube(tube)

    def ground_level_measuring(self, event: models.Event) -> None:
        """
        Retrieve all the data from the Django database to make it available for groundlevelmeasuring generation.
        """
        well = event.groundwater_monitoring_well_static

        # Get all static well data
        static_well_data = self.get_data.update_static_well(well)
        static_well_data.update(
            {
                "requestReference": f"{well.internal_id}_GroundLevelMeasuring_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            }
        )
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
        well = event.groundwater_monitoring_well_static

        # Get all static well data
        static_well_data = self.get_data.update_static_well(well)
        static_well_data.update(
            {
                "requestReference": f"{well.internal_id}_GroundLevel_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            }
        )
        self.datafile.update(static_well_data)

        # Get delivered vertical position
        delivered_location = self.create_delivered_location_dict(well)
        self.datafile.update(delivered_location)

        # If the id is given get the information directly
        for tube in event.groundwater_monitoring_tube_dynamic.all():
            self.handle_dynamic_well(tube)

            delivered_vertical_position = self.create_delivered_vertical_position_dict(
                well_static=event.groundwater_monitoring_well_static,
                well_dynamic=tube,
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
        "GMW_GroundLevelMeasuring",
        "GMW_PositionsMeasuring",
        "GMW_ConstructionWithHistory",
        "GMW_Removal",
    ]

    if full_source_doc_type not in allowed_srcdocs:
        raise Exception(f"Invalid source document type: {source_doc_type}")


def set_delivery_accountable_party(well: models.GroundwaterMonitoringWellStatic) -> int:
    return 27376655 if _is_demo() else well.delivery_accountable_party.company_number


def create_sourcedocs(
    event: models.Event,
    source_doc_type: str,
    # Might want to add a variable for with or without history
):
    """
    Try to create registration sourcedocuments for a well/tube/quality regime
    Registration requests are saved to .xml file in registrations folder
    """
    validate_source_doc_type(source_doc_type)

    well = event.groundwater_monitoring_well_static
    quality_regime = well.quality_regime
    delivery_accountable_party = set_delivery_accountable_party(well)

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
            srcdocdata=srcdocdata,
        )

        filename = request_reference + ".xml"
        gmw_registration_request.generate()
        gmw_registration_request.write_request(
            output_dir=REGISTRATIONS_DIR, filename=filename
        )

        process_status = f"succesfully_generated_{source_doc_type}_request"
        models.gmw_registration_log.objects.update_or_create(
            bro_id=srcdocdata["broId"],
            event_id=event.change_id,
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
        process_status = "failed_to_generate_source_documents"
        models.gmw_registration_log.objects.update_or_create(
            bro_id=srcdocdata["broId"],
            event_id=event.change_id,
            quality_regime=quality_regime,
            defaults=dict(
                comments=f"Failed to create {source_doc_type} source document: {e}",
                date_modified=datetime.datetime.now(),
                process_status=process_status,
            ),
        )


def create_construction_sourcedocs(
    event: models.Event,
):
    """
    Try to create registration sourcedocuments for a well/tube/quality regime
    Registration requests are saved to .xml file in registrations folder
    """
    well = event.groundwater_monitoring_well_static

    delivery_accountable_party = set_delivery_accountable_party(well)

    # Retrieve general static information of the well
    get_srcdoc_data = GetSourceDocData()

    get_srcdoc_data.construction(event)
    srcdocdata = get_srcdoc_data.datafile

    objectIdAccountableParty = get_object_id_accountable_party(well)
    srcdocdata.update(objectIdAccountableParty)

    # Add event date
    event_date = get_event_date(event)
    srcdocdata.update({"eventDate": event_date})

    logger.info(srcdocdata["requestReference"])
    logger.info(str(delivery_accountable_party))
    logger.info(str(well.quality_regime))
    logger.info(srcdocdata)

    construction_request = brx.gmw_registration_request(
        srcdoc="GMW_Construction",
        requestReference=srcdocdata["requestReference"],
        deliveryAccountableParty=str(delivery_accountable_party),
        qualityRegime=well.quality_regime,
        srcdocdata=srcdocdata,
    )
    logger.info(f"formatted construction sourcedocument for event {event.change_id}")

    filename = srcdocdata["requestReference"] + ".xml"

    construction_request.generate()
    logger.info(f"Generated {filename}")
    logger.info(
        f"Wrote construction sourcedocument {os.path.join(REGISTRATIONS_DIR, filename)}"
    )
    construction_request.write_request(output_dir=REGISTRATIONS_DIR, filename=filename)
    logger.info(
        f"Wrote construction sourcedocument {os.path.join(REGISTRATIONS_DIR, filename)}"
    )
    process_status = "succesfully_generated_Construction_request"
    models.gmw_registration_log.objects.update_or_create(
        event_id=event.change_id,
        defaults=dict(
            quality_regime=well.quality_regime,
            bro_id=srcdocdata.get("broId", None),
            comments="succesfully generated Construction request",
            date_modified=datetime.datetime.now(),
            validation_status=None,
            process_status=process_status,
            file=filename,
            object_id_accountable_party=srcdocdata["objectIdAccountableParty"],
        ),
    )


def handle_not_valid_or_error(
    registration: models.gmw_registration_log, validation_info
):
    defaults = dict(
        validation_status=validation_info["status"],
        process_status="source_document_validation_succesful",
    )
    try:
        validation_errors = validation_info["errors"]
        comments = f"Validated registration document, found errors: {validation_errors}"

        defaults.update({"comments": comments})
        if (
            "Dit registratieobject heeft de registratiestatus voltooid."
            in validation_errors
        ):
            defaults.update({"delivery_status": "geleverd", "delivery_id": "onbekend"})

        models.gmw_registration_log.objects.update_or_create(
            id=registration.id, defaults=defaults
        )
    except Exception as e:
        comments = f"No errors found, details: {e}"
        defaults.update({"comments": comments})
        models.gmw_registration_log.objects.update_or_create(
            id=registration.id, defaults=defaults
        )


def validate_gmw_registration_request(
    registration: models.gmw_registration_log, bro_info
):
    """
    Validate generated registration sourcedocuments
    """
    demo = _is_demo()
    file = registration.file
    source_doc_file = os.path.join(REGISTRATIONS_DIR, file)
    payload = open(source_doc_file)
    print(bro_info, demo)

    def met_projectnummer(bro_info):
        return bro_info.get("projectnummer") not in (None, "")

    proj_str = (
        "" if not met_projectnummer(bro_info) else f"{bro_info['projectnummer']}/"
    )
    url_prefix = "demo" if demo else "www"
    upload_url = (
        f"https://{url_prefix}.bronhouderportaal-bro.nl/api/v2/{proj_str}validatie"
    )
    validation_info = brx.validate_sourcedoc(
        payload,
        bro_info,
        demo=demo,
    )
    validation_status = validation_info["status"]

    if validation_info["status"] == "VALIDE":
        comments = "Succesfully validated sourcedocument, no errors"
        models.gmw_registration_log.objects.update_or_create(
            id=registration,
            defaults=dict(
                date_modified=datetime.datetime.now(),
                comments=comments,
                validation_status=validation_status,
                process_status="source_document_validation_succesful",
            ),
        )
    elif str(validation_status) == "401":
        registration.comments = f"Niet geautoriseerd om te leveren op {bro_info['projectnummer']} - {validation_info}"
        registration.process_status = "source_document_validation_succesful"
        registration.save(update_fields=["comments", "process_status"])
    else:
        handle_not_valid_or_error(
            registration=registration, validation_info=validation_info
        )


def deliver_sourcedocuments(registration: models.gmw_registration_log, bro_info):
    """
    Deliver generated registration sourcedoc to the BRO
    """
    demo = _is_demo()

    # If the delivery fails, use the this to indicate how many attempts were made
    delivery_status = registration.delivery_status
    if delivery_status is None:
        delivery_status_update = "failed_once"
    else:
        position = bisect.bisect_left(failed_update_strings, delivery_status)
        delivery_status_update = failed_update_strings[position + 1]

    try:
        file = registration.file
        source_doc_file = os.path.join(REGISTRATIONS_DIR, file)
        payload = open(source_doc_file)
        request = {file: payload}

        upload_info = brx.upload_sourcedocs_from_dict(
            request,
            user=bro_info["token"]["user"],
            password=bro_info["token"]["pass"],
            project_id=bro_info["projectnummer"],
            demo=demo,
        )

        if upload_info == "Error":
            comments = "Error occured during delivery of sourcedocument"
            models.gmw_registration_log.objects.update_or_create(
                id=registration,
                defaults={
                    "date_modified": datetime.datetime.now(),
                    "comments": comments,
                    "delivery_status": delivery_status_update,
                    "process_status": "failed_to_deliver_sourcedocuments",
                },
            )
        else:
            print(upload_info.text)
            delivery_id = upload_info.json()["identifier"]
            delivery_status = upload_info.json()["status"]
            lastchanged = upload_info.json()["lastChanged"]
            comments = "Succesfully delivered registration sourcedocument"

            models.gmw_registration_log.objects.update_or_create(
                id=registration,
                defaults={
                    "date_modified": datetime.datetime.now(),
                    "comments": comments,
                    "delivery_status": delivery_status,
                    "lastchanged": lastchanged,
                    "delivery_id": delivery_id,
                    "process_status": "succesfully_delivered_sourcedocuments",
                },
            )

    except Exception as e:
        comments = (
            f"Exception occured during delivery of registration sourcedocument: {e}"
        )
        models.gmw_registration_log.objects.update_or_create(
            id=registration,
            defaults={
                "date_modified": datetime.datetime.now(),
                "comments": comments,
                "delivery_status": delivery_status_update,
                "process_status": "failed_to_deliver_sourcedocuments",
            },
        )


def update_event_based_on_levering(registration: models.gmw_registration_log) -> None:
    event = models.Event.objects.get(
        change_id=registration.event_id,
    )

    event.delivered_to_bro = True
    event.save(update_fields=["delivered_to_bro"])


def check_delivery_status_levering(registration: models.gmw_registration_log, bro_info):
    """
    Check the status of a registration delivery
    Logs the status of the delivery in the database
    If delivery is approved, a GroundwaterLevelDossier object is created
    This means the registration process is concluded

    Parameters
    ----------
    registration : int
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
    demo = _is_demo()
    delivery_id = registration.delivery_id
    try:
        upload_info = brx.check_delivery_status(
            delivery_id,
            token=bro_info["token"],
            demo=demo,
            project_id=bro_info["projectnummer"],
        )

        print(upload_info.json())
        if (
            upload_info.json()["status"] == "DOORGELEVERD"
            and upload_info.json()["brondocuments"][0]["status"] == "OPGENOMEN_LVBRO"
        ):
            record, created = models.gmw_registration_log.objects.update_or_create(
                id=registration,
                defaults=dict(
                    bro_id=upload_info.json()["brondocuments"][0]["broId"],
                    delivery_status=upload_info.json()["brondocuments"][0]["status"],
                    last_changed=upload_info.json()["lastChanged"],
                    comments="registration request approved",
                    process_status="delivery_approved",
                ),
            )

            # Update the event
            update_event_based_on_levering(registration)

            # Remove the sourcedocument file if delivery is approved
            file = registration.file
            source_doc_file = os.path.join(REGISTRATIONS_DIR, file)
            os.remove(source_doc_file)

        else:
            record, created = models.gmw_registration_log.objects.update_or_create(
                id=registration,
                defaults=dict(
                    delivery_status=upload_info.json()["status"],
                    last_changed=upload_info.json()["lastChanged"],
                    comments="registration request not yet approved",
                ),
            )

    except Exception as e:
        record, created = models.gmw_registration_log.objects.update_or_create(
            id=registration,
            defaults=dict(
                comments=f"Error occured during status check of delivery: {e}"
            ),
        )


def get_registration_validation_status(registration):
    registration = models.gmw_registration_log.objects.get(id=registration)
    validation_status = registration.validation_status
    return validation_status


def delete_existing_failed_registrations(event: models.Event):
    models.gmw_registration_log.objects.filter(
        event_id=event.change_id, process_status="failed_to_generate_source_documents"
    ).delete()


class EventsHandler:
    def create_type_sourcedoc(self, event: models.Event):
        """
        Possible event_types:
        WellHeadProtector, Lengthening,
        GroundLevel, Owner, Shortening, Positions,
        ElectrodeStatus, Maintainer, TubeStatus,
        Insertion, Shift, Removal, GroundLevelMeasuring,
        PositionsMeasuring, ConstructionWithHistory', Removal

        Construction has its own function.

        """
        delete_existing_failed_registrations(event)
        create_sourcedocs(
            event=event,
            source_doc_type=EVENTNAME2TYPE[event.event_name],
        )

    def create_construction(self, event: models.Event):
        delete_existing_failed_registrations(event)
        create_construction_sourcedocs(
            event=event,
        )


def gmw_create_sourcedocs_wells():
    """
    Run gmw registrations for all monitoring wells in the database
    Registrations has to be run multiple times to get all tubes registered
    This will not interfere with additions, as a check will be done on registration availibility
    """

    # Pak de construction events, filter welke events al in de BRO staan
    events_handler = EventsHandler()
    for construction in getConstruction():
        events_handler.create_construction(event=construction)

    for event in getAllIntermediateEvents():
        events_handler.create_type_sourcedoc(event=event)


def delivered_but_not_approved(registration):
    """
    Checks if a registration is delivered but not yet approved.
    """
    if (
        registration.process_status == "succesfully_delivered_sourcedocuments"
        and registration.delivery_status != "OPGENOMEN_LVBRO"
        and registration.delivery_id is not None
    ):
        return True

    else:
        return False


def gmw_check_existing_registrations():
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
        event = models.Event.objects.get(change_id=registration.event_id)
        if event.delivered_to_bro:
            # Already delivered, so can skip.
            continue

        source_doc_type = registration.event_type
        bro_info = form_bro_info(event.groundwater_monitoring_well_static)
        print(bro_info)
        if bro_info_missing(
            bro_info, event.groundwater_monitoring_well_static.__str__()
        ):
            continue

        if delivered_but_not_approved(registration):
            # The registration has been delivered, but not yet approved
            check_delivery_status_levering(registration, REGISTRATIONS_DIR, bro_info)
            continue

        if (
            registration.process_status
            == f"succesfully_generated_{source_doc_type}_request"
        ):
            validate_gmw_registration_request(
                registration,
                bro_info,
            )

        # If an error occured during validation, try again
        # Failed to validate sourcedocument doesn't mean the document is valid/invalid
        # It means something went wrong during validation (e.g BRO server error)
        # Even if a document is invalid, the validation process has succeeded and won't be reattempted
        elif (
            registration.process_status == "failed_to_validate_source_documents"
            or get_registration_validation_status(registration) != "VALIDE"
        ):
            # If we failed to validate the sourcedocument, try again
            # TODO maybe limit amount of retries? Do not expect validation to fail multiple times..
            validate_gmw_registration_request(
                registration,
                bro_info,
            )

        # If validation is succesful and the document is valid, try a delivery
        if (
            registration.process_status == "source_document_validation_succesful"
            and get_registration_validation_status(registration) == "VALIDE"
        ):
            deliver_sourcedocuments(
                registration,
                bro_info,
            )

        # If delivery is succesful, check the status of the delivery
        if (
            registration.process_status == "succesfully_delivered_sourcedocuments"
            and registration.delivery_status != "OPGENOMEN_LVBRO"
            and registration.delivery_id is not None
        ):
            # The registration has been delivered, but not yet approved
            check_delivery_status_levering(
                registration,
                bro_info,
            )

        # If the delivery failed previously, we can retry
        if registration.process_status == "failed_to_deliver_sourcedocuments":
            # This will not be the case on the first try
            if registration.delivery_status == "failed_thrice":
                # TODO report with mail?
                continue
            else:
                deliver_sourcedocuments(
                    registration,
                    bro_info,
                )

        # Make sure the event is adjusted correctly if the information is delivered to the BRO.
        if registration.delivery_status == "OPGENOMEN_LVBRO":
            with reversion.create_revision():
                event.delivered_to_bro = True
                event.save(update_fields=["delivered_to_bro"])

                reversion.set_comment("Delivered the information to the BRO.")
