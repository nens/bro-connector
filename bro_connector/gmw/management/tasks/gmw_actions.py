import logging
import os

import reversion
from bro.models import Organisation
from django.apps import apps
from gmw.models import (
    Event,
    GroundwaterMonitoringWellStatic,
    gmw_registration_log,
)

from . import sync_gmw_events as gmw_sync

logger = logging.getLogger(__name__)


def _get_token(owner: Organisation):
    return {
        "user": owner.bro_user,
        "pass": owner.bro_token,
    }


def form_bro_info(well: GroundwaterMonitoringWellStatic) -> dict:
    return {
        "token": _get_token(well.delivery_accountable_party),
        "projectnummer": well.project_number,
    }


def _get_registrations_dir(app: str):
    app_config = apps.get_app_config(app)
    base_dir = app_config.path
    return f"{base_dir}\\registrations"


def create_registrations_folder():
    folder_name = _get_registrations_dir("gmw")
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


def check_and_deliver(well: GroundwaterMonitoringWellStatic) -> None:
    """
    Run gmw registrations for all monitoring wells in the database
    Registrations has to be run multiple times to get all tubes registered
    This will not interfere with additions, as a check will be done on registration availibility
    """

    # Pak de construction events, filter welke events al in de BRO staan
    construction_events = well.event.filter(
        groundwater_monitoring_well_static=well,
        event_name="constructie",
        delivered_to_bro=False,
    )

    # Check if a registrations directory has been made.
    create_registrations_folder()

    events_handler = gmw_sync.EventsHandler()
    logger.debug(
        f"Processing well: {well} with {construction_events.count()} construction events."
    )
    for construction in construction_events:
        logger.debug(f"Processing {construction}")
        delivery_type = (
            "register" if construction.correction_reason is None else "replace"
        )
        if gmw_registration_log.objects.filter(
            event_id=construction.change_id,
            delivery_type=delivery_type,
            validation_status="VALIDE",
        ).exists():
            logger.info(
                f"Registration for construction event {construction} already exists. Skipping creation.",
            )
            continue

        events_handler.create_construction(event=construction)

    for event in well.event.exclude(event_name="constructie").filter(
        delivered_to_bro=False
    ):
        events_handler.create_type_sourcedoc(event=event)

    for event in well.event.filter(delivered_to_bro=False):
        logger.info(f"Checking registration for event: {event}")
        delivery_type = "register" if event.correction_reason is None else "replace"
        registration = gmw_registration_log.objects.get(
            event_id=event.change_id,
            delivery_type=delivery_type,
        )
        gmw_check_registrations(registration)


def check_status(well: GroundwaterMonitoringWellStatic) -> None:
    events = Event.objects.filter(
        groundwater_monitoring_well_static=well,
        delivered_to_bro=False,
    )

    for event in events:
        delivery_type = "register" if event.correction_reason is None else "replace"
        registration = gmw_registration_log.objects.get(
            event_id=event.change_id,
            delivery_type=delivery_type,
        )
        gmw_check_registrations(registration)


def get_well_from_event_id(event_id: int):
    event = Event.objects.get(change_id=event_id)
    return event.groundwater_monitoring_well_static


def gmw_check_registrations(registration: gmw_registration_log):
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
    well = get_well_from_event_id(registration.event_id)
    bro_info = form_bro_info(well)
    logger.info(f"Processing registration: {registration} with {bro_info}")
    logger.info(f"Current status: {registration.process_status}")
    # We check the status of the registration and either validate/deliver/check status/do nothing
    source_doc_type = registration.event_type

    if gmw_sync.delivered_but_not_approved(registration):
        # The registration has been delivered, but not yet approved
        gmw_sync.check_delivery_status_levering(registration, bro_info)
    if (
        registration.process_status
        == f"succesfully_generated_{source_doc_type}_request"
    ):
        gmw_sync.validate_gmw_registration_request(
            registration,
            bro_info,
        )

    # If an error occured during validation, try again
    # Failed to validate sourcedocument doesn't mean the document is valid/invalid
    # It means something went wrong during validation (e.g BRO server error)
    # Even if a document is invalid, the validation process has succeeded and won't be reattempted
    elif (
        registration.process_status == "failed_to_validate_source_documents"
        or registration.validation_status != "VALIDE"
    ):
        # If we failed to validate the sourcedocument, try again
        # TODO maybe limit amount of retries? Do not expect validation to fail multiple times..
        gmw_sync.validate_gmw_registration_request(
            registration,
            bro_info,
        )

    # If validation is succesful and the document is valid, try a delivery
    if (
        registration.process_status == "source_document_validation_succesful"
        and registration.validation_status == "VALIDE"
    ):
        gmw_sync.deliver_sourcedocuments(registration, bro_info)

    # If delivery is succesful, check the status of the delivery
    if (
        registration.process_status == "succesfully_delivered_sourcedocuments"
        and registration.delivery_status != "OPGENOMEN_LVBRO"
        and registration.delivery_id is not None
    ):
        # The registration has been delivered, but not yet approved
        gmw_sync.check_delivery_status_levering(
            registration,
            bro_info,
        )

    # If the delivery failed previously, we can retry
    if registration.process_status == "failed_to_deliver_sourcedocuments":
        # This will not be the case on the first try
        if registration.delivery_status == "failed_thrice":
            # TODO report with mail?
            pass
        else:
            gmw_sync.deliver_sourcedocuments(
                registration,
                bro_info,
            )

    # Make sure the event is adjusted correctly if the information is delivered to the BRO.
    if registration.delivery_status == "OPGENOMEN_LVBRO":
        event = Event.objects.get(change_id=registration.event_id)

        with reversion.create_revision():
            event.delivered_to_bro = True
            event.save(update_fields=["delivered_to_bro"])

            reversion.set_comment("Delivered the information to the BRO.")
