from django.core.management.base import BaseCommand

import bro_exchange as brx
import os
import datetime
import bisect
import logging
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

from main.settings.base import gld_SETTINGS
from main import settings
from gld import models

failed_update_strings = ["failed_once", "failed_twice", "failed_thrice"]


def validate_gld_addition_source_document(
    observation_id, filename, acces_token_bro_portal, demo
):
    """
    Validate the generated GLD addition sourcedoc
    """
    source_doc_file = os.path.join(gld_SETTINGS["additions_dir"], filename)
    payload = open(source_doc_file)

    try:
        validation_info = brx.validate_sourcedoc(
            payload, acces_token_bro_portal, demo=demo
        )
        validation_status = validation_info["status"]

        if "errors" in validation_info:
            validation_errors = validation_info["errors"]
            comments = "Validated sourcedocument, found errors: {}".format(
                validation_errors
            )

            record, created = models.Observation.objects.update_or_create(
                observation_id=observation_id,
                defaults={"status": "source_document_validation_failed"},
            )

        else:
            comments = "Succesfully validated sourcedocument, no errors"

        models.gld_addition_log.objects.update_or_create(
            observation_id=observation_id,
            defaults={
                "date_modified": datetime.datetime.now(),
                "comments": comments[0:20000],
                "validation_status": validation_status,
            },
        )

        record, created = models.Observation.objects.update_or_create(
            observation_id=observation_id,
            defaults={"status": "source_document_validation_succeeded"},
        )

    except Exception as e:
        models.gld_addition_log.objects.update_or_create(
            observation_id=observation_id,
            defaults={
                "date_modified": datetime.datetime.now(),
                "comments": "Failed to validate source document: {}".format(e),
            },
        )

        record, created = models.Observation.objects.update_or_create(
            observation_id=observation_id,
            defaults={"status": "source_document_validation_failed"},
        )

    return validation_status


def deliver_gld_addition_source_document(
    observation_id, filename, acces_token_bro_portal, demo
):
    """
    Deliver GLD addition sourcedocument to the BRO
    """

    gld_addition = models.gld_addition_log.objects.get(observation_id=observation_id)
    source_doc_file = os.path.join(gld_SETTINGS["additions_dir"], filename)
    payload = open(source_doc_file)
    request = {filename: payload}

    # If the delivery fails, use the this to indicate how many attempts were made
    delivery_status = gld_addition.levering_status
    if delivery_status is None:
        delivery_status_update = "failed_once"
    else:
        position = bisect.bisect_left(failed_update_strings, delivery_status)
        delivery_status_update = failed_update_strings[position + 1]

    try:
        upload_info = brx.upload_sourcedocs_from_dict(
            request, acces_token_bro_portal, demo=demo
        )

        if upload_info == "Error":

            comments = "Error occured during delivery of sourcedocument"

            models.gld_addition_log.objects.update_or_create(
                observation_id=observation_id,
                defaults={
                    "date_modified": datetime.datetime.now(),
                    "comments": comments,
                    "levering_status": delivery_status_update,
                },
            )
        else:
            levering_id = upload_info.json()["identifier"]
            delivery_status = upload_info.json()["status"]
            lastchanged = upload_info.json()["lastChanged"]
            comments = "Succesfully delivered sourcedocument"

            models.gld_addition_log.objects.update_or_create(
                observation_id=observation_id,
                defaults={
                    "date_modified": datetime.datetime.now(),
                    "comments": comments,
                    "levering_status": delivery_status,
                    "lastchanged": lastchanged,
                    "levering_id": levering_id,
                },
            )

            record, created = models.Observation.objects.update_or_create(
                observation_id=observation_id,
                defaults={"status": "source_document_delivered"},
            )

    except Exception as e:

        comments = "Error occured in attempting to deliver sourcedocument, {}".format(e)

        models.gld_addition_log.objects.update_or_create(
            observation_id=observation_id,
            defaults={
                "date_modified": datetime.datetime.now(),
                "comments": comments,
                "levering_status": delivery_status_update,
            },
        )

    return delivery_status_update


def check_status_gld_addition(
    observation_id, levering_id, acces_token_bro_portal, demo
):
    """
    Check the status of a delivery and log to the database what the status is
    """

    gld_addition = models.gld_addition_log.objects.get(observation_id=observation_id)
    try:
        upload_info = brx.check_delivery_status(
            levering_id, acces_token_bro_portal, demo=demo
        )
        delivery_status = upload_info.json()["status"]

        if delivery_status == "DOORGELEVERD":

            comments = "GLD addition is approved"
            models.gld_addition_log.objects.update_or_create(
                observation_id=observation_id,
                defaults={
                    "date_modified": datetime.datetime.now(),
                    "comments": comments,
                    "levering_status": delivery_status,
                },
            )

            # Update the observation status to approved
            record, created = models.Observation.objects.update_or_create(
                observation_id=observation_id, defaults={"status": "delivery_approved"}
            )

            # Update the GLD Registration to show the last time an observation was delivered
            record, created = models.gld_registration_log.objects.update_or_create(
                gld_bro_id=gld_addition.broid_registration,
                defaults=dict(last_changed=upload_info.json()["lastChanged"]),
            )

        else:
            comments = "Status check succesful, not yet approved"
            models.gld_addition_log.objects.update_or_create(
                observation_id=observation_id,
                defaults={
                    "date_modified": datetime.datetime.now(),
                    "comments": comments,
                    "levering_status": delivery_status,
                },
            )

    except Exception as e:
        comments = "Status check failed, {}".format(e)
        models.gld_addition_log.objects.update_or_create(
            observation_id=observation_id,
            defaults={
                "date_modified": datetime.datetime.now(),
                "comments": comments,
                "levering_status": delivery_status,
            },
        )

    return delivery_status


def validate_addition(observation, acces_token_bro_portal, demo):
    """
    Validate the sourcedocuments, register the results in the database
    """

    # Get the GLD addition for this observation
    gld_addition = models.gld_addition_log.objects.get(
        observation_id=observation.observation_id
    )
    filename = gld_addition.file
    validation_status = gld_addition.validation_status

    # Validate the sourcedocument for this observation
    validation_status = validate_gld_addition_source_document(
        observation.observation_id, filename, acces_token_bro_portal, demo
    )

    return validation_status


def deliver_addition(observation, access_token_bro_portal, demo):
    """
    If there is a valid source document, deliver to the BRO
    If delivery has failed three times prior, no more attempts will be made
    """

    # Get the GLD addition for this observation
    gld_addition = models.gld_addition_log.objects.get(
        observation_id=observation.observation_id
    )
    validation_status = gld_addition.validation_status
    filename = gld_addition.file

    if validation_status == "VALIDE" and gld_addition.levering_id is None:
        delivery_status = deliver_gld_addition_source_document(
            observation.observation_id, filename, access_token_bro_portal, demo
        )

        if delivery_status == "failed_thrice":
            # If delivery fails three times, we flag the observation as delivery failed
            record, created = models.Observation.objects.update_or_create(
                observation_id=observation.observation_id,
                defaults={"status": "source_document_delivery_failed"},
            )


def check_status_addition(observation, acces_token_bro_portal, demo):
    """
    Check the status of a delivery
    If the delivery has been approved, remove the source document
    """
    # Get the GLD addition for this observation
    try:
        gld_addition = models.gld_addition_log.objects.get(
            observation_id=observation.observation_id
        )
    except:
        return None
    file_name = gld_addition.file
    levering_id = gld_addition.levering_id
    delivery_status = gld_addition.levering_status

    new_delivery_status = check_status_gld_addition(
        observation.observation_id, levering_id, acces_token_bro_portal, demo
    )
    try:
        if new_delivery_status == "DOORGELEVERD":  # "OPGENOMEN_LVBRO":
            sourcedoc_filepath = os.path.join(gld_SETTINGS["additions_dir"], file_name)
            os.remove(sourcedoc_filepath)
    except:
        pass  # no file to remove

    return new_delivery_status


def gld_validate_and_deliver(additions_dir, acces_token_bro_portal, demo):
    """
    Main algorithm that checks the observations and performs actions based on the status
    """

    observation_set = models.Observation.objects.all()

    for observation in observation_set:
        # For all the observations in the database, check the status and continue with the BRO delivery process
        if observation.status == "source_document_created":
            # TODO check if procedure is same as other observations, use the same procedure uuid
            validation_status = validate_addition(
                observation, acces_token_bro_portal, demo
            )

        elif observation.status == "source_document_validation_succeeded":
            # This observation source document has been validated before
            # If result was NIET_VALIDE try again, otherwise try delivery

            gld_addition = models.gld_addition_log.objects.get(
                observation_id=observation.observation_id
            )
            validation_status = gld_addition.validation_status

            if validation_status == "VALIDE":
                # If a source document has been validated succesfully but failed to deliver, try to deliver again
                # after three tries no more attempts will be made
                delivery_status = deliver_addition(
                    observation, acces_token_bro_portal, demo
                )

        elif observation.status == "source_document_validation_failed":
            # Something went wrong during document validation, try again
            validation_status = validate_addition(
                observation, acces_token_bro_portal, demo
            )

        elif observation.status == "source_document_delivered":
            delivery_status = check_status_addition(
                observation, acces_token_bro_portal, demo
            )

        elif observation.status == "delivery_approved":
            delivery_status = check_status_addition(
                observation, acces_token_bro_portal, demo
            )

        elif observation.status == "flagged_for_deletion":
            # TODO Delete request
            continue

        else:
            continue


class Command(BaseCommand):
    def handle(self, *args, **options):

        demo = gld_SETTINGS["demo"]
        if demo:
            acces_token_bro_portal = gld_SETTINGS["acces_token_bro_portal_demo"]
        else:
            acces_token_bro_portal = gld_SETTINGS[
                "acces_token_bro_portal_bro_connector"
            ]

        additions_dir = gld_SETTINGS["additions_dir"]

        gld_validate_and_deliver(additions_dir, acces_token_bro_portal, demo)
