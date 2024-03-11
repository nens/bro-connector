from . import sync_gmw_events as gmw_sync
from gmw.models import (
    GroundwaterMonitoringWellStatic,
    Event,
    gmw_registration_log,
)
import os
import reversion

from main.settings.base import gmw_SETTINGS

demo = gmw_SETTINGS["demo"]
if demo:
    bro_info = gmw_SETTINGS["bro_info_demo"]
else:
    bro_info = gmw_SETTINGS["bro_info_bro_connector"]

folder_name = "./registrations/"


def create_registrations_folder():
    # Check if the folder already exists
    if not os.path.exists(folder_name):
        try:
            # Create the folder if it doesn't exist
            os.mkdir(folder_name)
            print(f"Folder '{folder_name}' created successfully.")
        except OSError:
            print(f"Creation of the folder '{folder_name}' failed.")
    else:
        print(f"Folder '{folder_name}' already exists.")


class GetEvents:
    """
    A Class that helps retrieving different types of events.
    The events will have information linking to the data that changed.
    """

    def construction(well):
        return Event.objects.filter(
            groundwater_monitoring_well_static=well,
            event_name="constructie",
            delivered_to_bro=False,
        )

    def wellHeadProtector(well):
        return Event.objects.filter(
            groundwater_monitoring_well_static=well,
            event_name="beschermconstructieVeranderd",
            delivered_to_bro=False,
        )

    def lengthening(well):
        return Event.objects.filter(
            groundwater_monitoring_well_static=well,
            event_name="buisOpgelengd",
            delivered_to_bro=False,
        )

    def shortening(well):
        return Event.objects.filter(
            groundwater_monitoring_well_static=well,
            event_name="buisIngekort",
            delivered_to_bro=False,
        )

    def groundLevelMeasuring(well):
        return Event.objects.filter(
            groundwater_monitoring_well_static=well,
            event_name="nieuweInmetingMaaiveld",
            delivered_to_bro=False,
        )

    def positionsMeasuring(well):
        return Event.objects.filter(
            groundwater_monitoring_well_static=well,
            event_name="nieuweInmetingPosities",
            delivered_to_bro=False,
        )

    def groundLevel(well):
        return Event.objects.filter(
            groundwater_monitoring_well_static=well,
            event_name="nieuweBepalingMaaiveld",
            delivered_to_bro=False,
        )

    def owner(well):
        return Event.objects.filter(
            groundwater_monitoring_well_static=well,
            event_name="eigenaarVeranderd",
            delivered_to_bro=False,
        )

    def positions(well):
        return Event.objects.filter(
            groundwater_monitoring_well_static=well,
            event_name="inmeting",
            delivered_to_bro=False,
        )

    def electrodeStatus(well):
        return Event.objects.filter(
            groundwater_monitoring_well_static=well,
            event_name="electrodeStatus",
            delivered_to_bro=False,
        )

    def maintainer(well):
        return Event.objects.filter(
            groundwater_monitoring_well_static=well,
            event_name="onderhouderVeranderd",
            delivered_to_bro=False,
        )

    def tubeStatus(well):
        return Event.objects.filter(
            groundwater_monitoring_well_static=well,
            event_name="buisstatusVeranderd",
            delivered_to_bro=False,
        )

    def insertion(well):
        return Event.objects.filter(
            groundwater_monitoring_well_static=well,
            event_name="buisdeelIngeplaatst",
            delivered_to_bro=False,
        )

    def shift(well):
        return Event.objects.filter(
            groundwater_monitoring_well_static=well,
            event_name="maaiveldVerlegd",
            delivered_to_bro=False,
        )


def check_and_deliver(well: GroundwaterMonitoringWellStatic) -> None:
    """
    Run gmw registrations for all monitoring wells in the database
    Registrations has to be run multiple times to get all tubes registered
    This will not interfere with additions, as a check will be done on registration availibility
    """

    # Pak de construction events, filter welke events al in de BRO staan
    construction_events = GetEvents.construction(well)

    # Check if a registrations directory has been made.
    create_registrations_folder()

    events_handler = gmw_sync.EventsHandler("./registrations/")
    for construction in construction_events:
        events_handler.create_construction_sourcedoc(event=construction)

    electrodeStatus_events = GetEvents.electrodeStatus(well)
    for electrode_status in electrodeStatus_events:
        events_handler.create_type_sourcedoc(
            event=electrode_status, event_type="ElectrodeStatus"
        )

    groundLevel_events = GetEvents.groundLevel(well)
    for ground_level in groundLevel_events:
        events_handler.create_type_sourcedoc(
            event=ground_level, event_type="GroundLevel"
        )

    groundLevelMeasuring_events = GetEvents.groundLevelMeasuring(well)
    for ground_level_measuring in groundLevelMeasuring_events:
        events_handler.create_type_sourcedoc(
            event=ground_level_measuring, event_type="GroundLevelMeasuring"
        )

    insertion_events = GetEvents.insertion(well)
    for insertion in insertion_events:
        events_handler.create_type_sourcedoc(event=insertion, event_type="Insertion")

    lengthening_events = GetEvents.lengthening(well)
    for lengthening in lengthening_events:
        events_handler.create_type_sourcedoc(
            event=lengthening, event_type="Lengthening"
        )

    maintainer_events = GetEvents.maintainer(well)
    for maintainer in maintainer_events:
        events_handler.create_type_sourcedoc(event=maintainer, event_type="Maintainer")

    owner_events = GetEvents.owner(well)
    for owner in owner_events:
        events_handler.create_type_sourcedoc(events=owner, event_type="Owner")

    positionsMeasuring_events = GetEvents.positionsMeasuring(well)
    for positions_measuring in positionsMeasuring_events:
        events_handler.create_type_sourcedoc(
            event=positions_measuring, event_type="PositionsMeasuring"
        )

    positions_events = GetEvents.positions(well)
    for position in positions_events:
        events_handler.create_type_sourcedoc(event=position, event_type="Positions")

    shift_events = GetEvents.shift(well)
    for shift in shift_events:
        events_handler.create_type_sourcedoc(events=shift, event_type="Shift")

    shortening_events = GetEvents.shortening(well)
    for shortening in shortening_events:
        events_handler.create_type_sourcedoc(event=shortening, event_type="Shortening")

    tubeStatus_events = GetEvents.tubeStatus(well)
    for tube_status in tubeStatus_events:
        events_handler.create_type_sourcedoc(event=tube_status, event_type="TubeStatus")

    wellHeadProtector_events = GetEvents.wellHeadProtector(well)
    for well_head_protector in wellHeadProtector_events:
        events_handler.create_type_sourcedoc(
            event=well_head_protector, event_type="WellHeadProtector"
        )

    events = (
        construction_events
        | electrodeStatus_events
        | groundLevelMeasuring_events
        | groundLevel_events
        | insertion_events
        | lengthening_events
        | maintainer_events
        | owner_events
        | positionsMeasuring_events
        | positions_events
        | shift_events
        | shortening_events
        | tubeStatus_events
        | wellHeadProtector_events
    )
    print(events)
    for event in events:
        registration = gmw_registration_log.objects.get(
            event_id=event.change_id,
        )
        print(registration)
        gmw_check_registrations(registration)


def check_status(well: GroundwaterMonitoringWellStatic) -> None:
    events = Event.objects.filter(
        groundwater_monitoring_well_static=well,
        delivered_to_bro=False,
    )

    for event in events:
        registration = gmw_registration_log.objects.get(
            event_id=event.change_id,
        )
        gmw_check_registrations(registration)


def gmw_check_registrations(registration):
    """
    This function loops over all exists registrations in the database
    Depending on the status one of the following actions is carried out:
        - The sourcedocument for the registration is validated
        - The sourcedocument is delivered to the BRO
        - The status of a delivery is checked
        - If a delivery failed, it may be attempted again up to three times

    Parameters
    ----------
    events: QuerySet
    All the events in one queryset gathered from the well.

    Returns
    -------
    None.

    """
    # We check the status of the registration and either validate/deliver/check status/do nothing
    registration_id = registration.id
    source_doc_type = registration.levering_type

    if gmw_sync.delivered_but_not_approved(registration):
        print("1")
        # The registration has been delivered, but not yet approved
        status = gmw_sync.check_delivery_status_levering(
            registration_id, folder_name, bro_info, demo
        )

    if (
        gmw_sync.get_registration_process_status(registration_id)
        == f"succesfully_generated_{source_doc_type}_request"
    ):
        print("2")
        validation_status = gmw_sync.validate_gmw_registration_request(
            registration_id,
            folder_name,
            bro_info,
            demo,
        )

    # If an error occured during validation, try again
    # Failed to validate sourcedocument doesn't mean the document is valid/invalid
    # It means something went wrong during validation (e.g BRO server error)
    # Even if a document is invalid, the validation process has succeeded and won't be reattempted
    elif (
        gmw_sync.get_registration_process_status(registration_id)
        == "failed_to_validate_source_documents"
        or gmw_sync.get_registration_validation_status(registration_id) != "VALIDE"
    ):
        print("3")
        # If we failed to validate the sourcedocument, try again
        # TODO maybe limit amount of retries? Do not expect validation to fail multiple times..
        validation_status = gmw_sync.validate_gmw_registration_request(
            registration_id,
            folder_name,
            bro_info,
            demo,
        )

    # If validation is succesful and the document is valid, try a delivery
    if (
        gmw_sync.get_registration_process_status(registration_id)
        == "source_document_validation_succesful"
        and gmw_sync.get_registration_validation_status(registration_id) == "VALIDE"
    ):
        print("4")
        delivery_status = gmw_sync.deliver_sourcedocuments(
            registration_id,
            folder_name,
            bro_info,
            demo,
        )

    # If delivery is succesful, check the status of the delivery
    if (
        gmw_sync.get_registration_process_status(registration_id)
        == "succesfully_delivered_sourcedocuments"
        and registration.levering_status != "OPGENOMEN_LVBRO"
        and registration.levering_id is not None
    ):
        print("5")
        # The registration has been delivered, but not yet approved
        status = gmw_sync.check_delivery_status_levering(
            registration_id,
            folder_name,
            bro_info,
            demo,
        )

    # If the delivery failed previously, we can retry
    if (
        gmw_sync.get_registration_process_status(registration_id)
        == "failed_to_deliver_sourcedocuments"
    ):
        print("6")
        # This will not be the case on the first try
        if registration.levering_status == "failed_thrice":
            # TODO report with mail?
            pass
        else:
            delivery_status = gmw_sync.deliver_sourcedocuments(
                registration_id,
                folder_name,
                bro_info,
                demo,
            )

    # Make sure the event is adjusted correctly if the information is delivered to the BRO.
    if registration.levering_status == "OPGENOMEN_LVBRO":
        event = Event.objects.get(change_id=registration.event_id)

        with reversion.create_revision():
            event.delivered_to_bro = True
            event.save(update_fields=["delivered_to_bro"])

            reversion.set_comment("Delivered the information to the BRO.")
