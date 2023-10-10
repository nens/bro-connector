from django.core.management.base import BaseCommand
from django.db import transaction

import pandas as pd
import requests
import bro_exchange as brx
import json
import os
import sys
import traceback
import datetime
import logging
import bisect

from bro_connector_gld.settings.base import GMW_AANLEVERING_SETTINGS
from gmw_aanlevering import models

failed_update_strings = ["failed_once", "failed_twice", "failed_thrice"]

<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
def records_in_registrations(bro_id) -> int:
    return len(models.gmw_registration_log.objects.filter(bro_id = bro_id))

def create_registration_sourcedocs(
    quality_regime,
    delivery_accountable_party,
    bro_id,
    locationcode,
=======

def create_start_registration_sourcedocs(
    quality_regime,
    deliveryaccountableparty,
    broidgmw,
    filtrnr,
    locationcode,  # nitg code
>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py
    registrations_dir,
    monitoringnetworks,
):

    """
<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
    Try to create registration sourcedocuments for a well/tube/quality regime
    Registration requests are saved to .xml file in registrations folder
    """

    try:
        monitoringpoints = [{"broId": bro_id}]
=======
    Try to create startregistration sourcedocuments for a well/tube/quality regime
    Startregistration requests are saved to .xml file in startregistrations folder
    """

    try:
        monitoringpoints = [{"broId": broidgmw, "tubeNumber": filtrnr}]
>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py

        if monitoringnetworks == None:

            srcdocdata = {
<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
                "objectIdAccountableParty": locationcode,
=======
                "objectIdAccountableParty": locationcode + str(filtrnr),
>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py
                "monitoringPoints": monitoringpoints,
            }
        else:
            srcdocdata = {
<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
                "objectIdAccountableParty": locationcode,
=======
                "objectIdAccountableParty": locationcode + str(filtrnr),
>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py
                "groundwaterMonitoringNets": monitoringnetworks,  #
                "monitoringPoints": monitoringpoints,
            }

<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
        records_in_register = records_in_registrations(bro_id)

        request_reference = f"{bro_id}_Registration_{records_in_register}"

        gmw_registration_request = brx.gmw_registration_request(
            srcdoc="GMW_registration",
            requestReference=request_reference,
            deliveryAccountableParty=delivery_accountable_party,
=======
        request_reference = "gmw_StartRegistration_{}_tube_{}".format(
            broidgmw, str(filtrnr)
        )
        gmw_startregistration_request = brx.gmw_registration_request(
            srcdoc="GMW_StartRegistration",
            requestReference=request_reference,
            deliveryAccountableParty=deliveryaccountableparty,
>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py
            qualityRegime=quality_regime,
            srcdocdata=srcdocdata,
        )

        filename = request_reference + ".xml"
<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
        gmw_registration_request.generate()
        gmw_registration_request.write_request(
            output_dir=registrations_dir, filename=filename
        )

        process_status = "succesfully_generated_registration_request"
        record, created = models.gmw_registration_log.objects.update_or_create(
            gwm_bro_id=bro_id,
            quality_regime=quality_regime,
            defaults=dict(
                comments="Succesfully generated registration request",
=======
        gmw_startregistration_request.generate()
        gmw_startregistration_request.write_request(
            output_dir=registrations_dir, filename=filename
        )

        process_status = "succesfully_generated_startregistration_request"
        record, created = models.gmw_registration_log.objects.update_or_create(
            gwm_bro_id=broidgmw,
            filter_id=filtrnr,
            quality_regime=quality_regime,
            defaults=dict(
                comments="Succesfully generated startregistration request",
>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py
                date_modified=datetime.datetime.now(),
                validation_status=None,
                process_status=process_status,
                file=filename,
            ),
        )

    except Exception as e:

        process_status = "failed_to_generate_source_documents"
        record, created = models.gmw_registration_log.objects.update_or_create(
<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
            gwm_bro_id=bro_id,
            quality_regime=quality_regime,
            defaults=dict(
                comments="Failed to create registration source document: {}".format(
=======
            gwm_bro_id=broidgmw,
            filter_id=filtrnr,
            quality_regime=quality_regime,
            defaults=dict(
                comments="Failed to create startregistration source document: {}".format(
>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py
                    e
                ),
                date_modified=datetime.datetime.now(),
                process_status=process_status,
            ),
        )


<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
def validate_gmw_registration_request(
=======
def validate_gmw_startregistration_request(
>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py
    registration_id, registrations_dir, acces_token_bro_portal, demo
):

    """
<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
    Validate generated registration sourcedocuments
=======
    Validate generated startregistration sourcedocuments
>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py
    """

    try:
        gmw_registration = models.gmw_registration_log.objects.get(
            id=registration_id
        )
        file = gmw_registration.file
        source_doc_file = os.path.join(registrations_dir, file)
        payload = open(source_doc_file)

        validation_info = brx.validate_sourcedoc(payload, acces_token_bro_portal, demo = demo)
<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
=======
        #print(validation_info)
>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py
        validation_status = validation_info["status"]

        if "errors" in validation_info:
            validation_errors = validation_info["errors"]
<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
            comments = "Validated registration document, found errors: {}".format(
=======
            comments = "Validated startregistration document, found errors: {}".format(
>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py
                validation_errors
            )

            record, created = models.gmw_registration_log.objects.update_or_create(
                id=registration_id,
                defaults=dict(
<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
                    comments="Registration document is invalid, {}".format(
=======
                    comments="Startregistration document is invalid, {}".format(
>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py
                        validation_errors
                    ),
                    validation_status=validation_status,
                    process_status="source_document_validation_succesful",
                ),
            )

        else:
            comments = "Succesfully validated sourcedocument, no errors"
            record, created = models.gmw_registration_log.objects.update_or_create(
                id=registration_id,
                defaults=dict(
                    # date_modified = datetime.datetime.now(),
                    comments=comments,
                    validation_status=validation_status,
                    process_status="source_document_validation_succesful",
                ),
            )

    except Exception as e:
        process_status = "failed_to_validate_sourcedocument"
        comments = "Exception occured during validation of sourcedocuments: {}".format(
            e
        )
        record, created = models.gmw_registration_log.objects.update_or_create(
            id=registration_id,
            defaults=dict(comments=comments, process_status=process_status),
        )


def deliver_sourcedocuments(
    registration_id, registrations_dir, acces_token_bro_portal, demo
):

    """
<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
    Deliver generated registration sourcedoc to the BRO
=======
    Deliver generated startregistration sourcedoc to the BRO
>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py
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
            request, acces_token_bro_portal, demo = demo
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
            levering_id = upload_info.json()["identifier"]
            delivery_status = upload_info.json()["status"]
            lastchanged = upload_info.json()["lastChanged"]
<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
            comments = "Succesfully delivered registration sourcedocument"
=======
            comments = "Succesfully delivered startregistration sourcedocument"
>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py

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
<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
        comments = "Exception occured during delivery of registration sourcedocument: {}".format(
=======
        comments = "Exception occured during delivery of startregistration sourcedocument: {}".format(
>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py
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


def check_delivery_status_levering(
    registration_id, registrations_dir, acces_token_bro_portal, demo
):

    """
<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
    Check the status of a registration delivery
    Logs the status of the delivery in the database
    If delivery is approved, a GroundwaterLevelDossier object is created
    This means the registration process is concluded
=======
    Check the status of a startregistration delivery
    Logs the status of the delivery in the database
    If delivery is approved, a GroundwaterLevelDossier object is created
    This means the startregistration process is concluded
>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py

    Parameters
    ----------
    registration_id : int
        unique id of the gmw registration in the database.
    acces_token_bro_portal : str
        access token for BRO bronhouderportaal: https://demo.bronhouderportaal-bro.nl/ .
    registrations_dir : str
<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
        directory where registration sourcedocument xml's are stored
=======
        directory where startregistration sourcedocument xml's are stored
>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py
    demo : bool, optional.

    Returns
    -------
    None.

    """

    registration = models.gmw_registration_log.objects.get(id=registration_id)
    levering_id = registration.levering_id

    try:
        upload_info = brx.check_delivery_status(
            levering_id, acces_token_bro_portal, demo = demo
        )
        if (
            upload_info.json()["status"] == "DOORGELEVERD"
            and upload_info.json()["brondocuments"][0]["status"] == "OPGENOMEN_LVBRO"
        ):

            record, created = models.gmw_registration_log.objects.update_or_create(
                id=registration_id,
                defaults=dict(
<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
                    bro_id=upload_info.json()["brondocuments"][0]["broId"],
                    levering_status=upload_info.json()["brondocuments"][0]["status"],
                    last_changed=upload_info.json()["lastChanged"],
                    comments="registration request approved",
=======
                    gmw_bro_id=upload_info.json()["brondocuments"][0]["broId"],
                    levering_status=upload_info.json()["brondocuments"][0]["status"],
                    last_changed=upload_info.json()["lastChanged"],
                    comments="Startregistration request approved",
>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py
                    process_status="delivery_approved",
                ),
            )

<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
=======
            # Create new GroundWaterLevelDossier
            start_date_research = datetime.datetime.now().date().isoformat()
            record, created = models.GroundwaterLevelDossier.objects.update_or_create(
                groundwater_monitoring_tube_id=registration.filter_id,
                gmw_bro_id=registration.gwm_bro_id,
                research_start_date=start_date_research,
                gmw_bro_id=upload_info.json()["brondocuments"][0]["broId"],
            )

>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py
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
<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
                    comments="registration request not yet approved",
=======
                    comments="Startregistration request not yet approved",
>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py
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


<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
def gmw_registration_wells(
=======
def gmw_start_registration_wells(
>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py
    acces_token_bro_portal, monitoringnetworks, registrations_dir, demo
):

    """
<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
    Run gmw registrations for all monitoring wells in the database
    Registrations has to be run multiple times to get all tubes registered
    This will not interfere with additions, as a check will be done on registration availibility
    """

    gwm_wells = models.GroundwaterMonitoringWellStatic.objects.all()
    # Loop over all GMW objects in the database
    for well in gwm_wells:

        # Ignore wells that are  delivered to BRO
        if well.current_in_bro == True:
=======
    Run gmw start registrations for all monitoring wells in the database
    Start registrations has to be run multiple times to get all tubes registered
    This will not interfere with additions, as a check will be done on registration availibility
    """

    gwm_wells = models.GroundwaterMonitoringWells.objects.all()
    # Loop over all GMW objects in the database
    for well in gwm_wells:

        # Ignore wells that are not (yet) delivered to BRO
        if well.delivered_to_bro == False:
            # ignore wells that are not registrated on purpose
>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py
            continue
        
        if demo == True:
            #print(well.bro_id)
            if well.bro_id != 'GMW000000042583':
                continue

        # Get some well properties
<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
        registration_object_id_well = well.groundwater_monitoring_well_static_id
        quality_regime = well.quality_regime
        gwm_bro_id = well.bro_id

        # Check if there is already a registration for this well
        if not models.gmw_registration_log.objects.filter(
            gwm_bro_id=gwm_bro_id, quality_regime=quality_regime
        ).exists():

            # There is not a gmw registration object with this configuration
            # Create a new configuration by creating registration sourcedocs
            # By creating the sourcedocs (or failng to do so), a registration is made in the database
            # This registration is used to track the progress of the delivery in further steps

            delivery_accountable_party = str(well.delivery_accountable_party)
            well_bro_id = well.bro_id
            location_code_internal = well.nitg_code
            registration = create_registration_sourcedocs(
                quality_regime,
                delivery_accountable_party,
                well_bro_id,
                location_code_internal,
                registrations_dir,
                monitoringnetworks,
            )


def gmw_check_existing_registrations(
    acces_token_bro_portal, registrations_dir, demo
):
    """
    This function loops over all exists registrations in the database
    Depending on the status one of the following actions is carried out:
        - The sourcedocument for the registration is validated
=======
        registration_object_id_well = well.groundwater_monitoring_well_id
        quality_regime = 'IMBRO'
        gwm_bro_id = well.bro_id

        # Get all filters that are installed in this well
        gmw_tubes_well = models.GroundwaterMonitoringTubes.objects.filter(
            groundwater_monitoring_well_id=registration_object_id_well
        )

        # Loop over all filters within the well
        for tube in gmw_tubes_well:
            tube_id = tube.tube_number

            # Ignore filters that should not be delivered to BRO
            if tube.deliver_to_bro == False:
                continue

            # Check if there is already a registration for this tube
            if not models.gmw_registration_log.objects.filter(
                gwm_bro_id=gwm_bro_id, filter_id=tube_id, quality_regime=quality_regime
            ).exists():

                # There is not a gmw registration object with this configuration
                # Create a new configuration by creating startregistration sourcedocs
                # By creating the sourcedocs (or failng to do so), a registration is made in the database
                # This registration is used to track the progress of the delivery in further steps

                delivery_accountable_party = str(well.delivery_accountable_party)
                well_bro_id = well.bro_id
                location_code_internal = well.nitg_code
                startregistration = create_start_registration_sourcedocs(
                    quality_regime,
                    delivery_accountable_party,
                    well_bro_id,
                    tube_id,
                    location_code_internal,
                    registrations_dir,
                    monitoringnetworks,
                )


def gmw_check_existing_startregistrations(
    acces_token_bro_portal, registrations_dir, demo
):
    """
    This function loops over all exists startregistrations in the database
    Depending on the status one of the following actions is carried out:
        - The sourcedocument for the startregistration is validated
>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py
        - The sourcedocument is delivered to the BRO
        - The status of a delivery is checked
        - If a delivery failed, it may be attempted again up to three times

    Parameters
    ----------
    acces_token_bro_portal : str
        access token for BRO bronhouderportaal: https://demo.bronhouderportaal-bro.nl/ .
    registrations_dir : str
<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
        directory where registration sourcedocument xml's are stored
=======
        directory where startregistration sourcedocument xml's are stored
>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py
    demo : bool
        True for test environment, False for production

    Returns
    -------
    None.

    """
    # Get all the current registrations
    gmw_registrations = models.gmw_registration_log.objects.all()

    for registration in gmw_registrations:

        # We check the status of the registration and either validate/deliver/check status/do nothing
        registration_id = registration.id

        # Tijdelijk:
        # if demo == True and registration.gmw_bro_id is None:
        #     continue
        # Tijdelijk tot hier

        

        if (
            get_registration_process_status(registration_id)
            == "succesfully_delivered_sourcedocuments"
            and registration.levering_status != "OPGENOMEN_LVBRO"
            and registration.levering_id is not None
        ):
            # The registration has been delivered, but not yet approved
            status = check_delivery_status_levering(
                registration_id, registrations_dir, acces_token_bro_portal, demo
            )

        else:
<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
            # Succesfully generated a registration sourcedoc in the previous step
            # Validate the created sourcedocument
            if (
                get_registration_process_status(registration_id)
                == "succesfully_generated_registration_request"
            ):
                validation_status = validate_gmw_registration_request(
=======
            # Succesfully generated a startregistration sourcedoc in the previous step
            # Validate the created sourcedocument
            if (
                get_registration_process_status(registration_id)
                == "succesfully_generated_startregistration_request"
            ):
                validation_status = validate_gmw_startregistration_request(
>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py
                    registration_id,
                    registrations_dir,
                    acces_token_bro_portal,
                    demo,
                )

            # If an error occured during validation, try again
            # Failed to validate sourcedocument doesn't mean the document is valid/invalid
            # It means something went wrong during validation (e.g BRO server error)
            # Even if a document is invalid, the validation process has succeeded and won't be reattempted
            if (
                get_registration_process_status(registration_id)
                == "failed_to_validate_source_documents"
            ):
                # If we failed to validate the sourcedocument, try again
                # TODO maybe limit amount of retries? Do not expect validation to fail multiple times..
<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
                validation_status = validate_gmw_registration_request(
=======
                validation_status = validate_gmw_startregistration_request(
>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py
                    registration_id,
                    registrations_dir,
                    acces_token_bro_portal,
                    demo,
                )

            # If validation is succesful and the document is valid, try a delivery
            if (
                get_registration_process_status(registration_id)
                == "source_document_validation_succesful"
                and get_registration_validation_status(registration_id) == "VALIDE"
            ):
                delivery_status = registrations_dir(
                    registration_id,
                    registrations_dir,
                    acces_token_bro_portal,
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
                    acces_token_bro_portal,
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
                    delivery_status = registrations_dir(
                        registration.id,
                        registrations_dir,
                        acces_token_bro_portal,
                        demo,
                    )


class Command(BaseCommand):
    help = """Custom command for import of GIS data."""

    def handle(self, *args, **options):

        demo = GMW_AANLEVERING_SETTINGS["demo"]
        if demo:
            acces_token_bro_portal = GMW_AANLEVERING_SETTINGS[
                "acces_token_bro_portal_demo"
            ]
        else:
            acces_token_bro_portal = GMW_AANLEVERING_SETTINGS[
                "acces_token_bro_portal_bro_connector"
            ]

        monitoringnetworks = GMW_AANLEVERING_SETTINGS["monitoringnetworks"]
        registrations_dir = GMW_AANLEVERING_SETTINGS["registrations_dir"]

        #print('start registrations')
        # Check the database for new wells/tubes and start a gmw registration for these objects if its it needed
<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
        registration = gmw_registration_wells(
=======
        registration = gmw_start_registration_wells(
>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py
            acces_token_bro_portal, monitoringnetworks, registrations_dir, demo
        )

        #print('check status')
        # Check existing registrations
<<<<<<< HEAD:bro_connector/gmw_aanlevering/management/commands/gmw_registrations_create.py
        check = gmw_check_existing_registrations(
            acces_token_bro_portal, registrations_dir, demo
        )
=======
        check = gmw_check_existing_startregistrations(
            acces_token_bro_portal, registrations_dir, demo
        )
>>>>>>> b47177d8d20a6e3896463e7083cda2e9b474cd1e:bro_connector/main/management/commands/gmw_registrations_create.py
