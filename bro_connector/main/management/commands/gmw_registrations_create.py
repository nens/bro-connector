from django.core.management.base import BaseCommand
from django.db import transaction, models

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

from main.settings.base import GMW_AANLEVERING_SETTINGS
from gmw_aanlevering import models

failed_update_strings = ["failed_once", "failed_twice", "failed_thrice"]

def records_in_registrations(bro_id) -> int:
    return len(models.gmw_registration_log.objects.filter(bro_id = bro_id))


class DjangoTableToDict:
    def __init__(self, well: models.GroundwaterMonitoringWellStatic, datafile):
        self.datafile = datafile
        self.well = well
        self.tubes = {}
        self.geo_ohm_cables = {}
        self.electrodes = {}

    def update_static_well(self):
        static_well_data = {
            "registrationObjectType": self.well.registration_object_type,
            "broId": self.well.bro_id,
            "requestReference": self.well.request_reference,
            "deliveryAccountableParty": self.well.delivery_accountable_party,
            "deliveryResponsibleParty": self.well.delivery_responsible_party,
            "qualityRegime": self.well.quality_regime,
            "underPrivilige": self.well.under_privilege,
            "deliveryContext": self.well.delivery_context,
            "constructionStandard": self.well.construction_standard,
            "initialFunction": self.well.initial_function,
            "nitgCode": self.well.nitg_code,
            "olgaCoda": self.well.olga_code,
            "wellCode": self.well.well_code,
            "monitoringPdokId": self.well.monitoring_pdok_id,
            "coordinates": self.well.coordinates,
            "referenceSystem": self.well.reference_system,
            "horizontalPositioningMethod": self.well.horizontal_positioning_method,
            "localVerticalReferencePoint": self.well.local_vertical_reference_point,
            "offset": self.well.well_offset,
            "verticalDatum": self.well.vertical_datum,
        }
        self.datafile.update(static_well_data)
    
    def get_all_tubes(self):
        return models.GroundwaterMonitoringTubesStatic.objects.filter(
                groundwater_monitoring_well = self.well.groundwater_monitoring_well_static_id,
            )

    def update_static_tube(self, tube: models.GroundwaterMonitoringTubesStatic):
        static_tube_data = {
            "tubeNumber": tube.tube_number,
            "tubeType": tube.tube_type,
            "artesianWellCapPresent": tube.artesian_well_cap_present,
            "sedimentSumpPresent": tube.sediment_sump_present,
            "numberOfGeoOhmCables": tube.number_of_geo_ohm_cables,
            "tubeMaterial": tube.tube_material,
            "screenLength": tube.screen_length,
            "sockMaterial": tube.sock_material,
            "sedimentSumpLength": tube.sediment_sump_length,
        }

        if tube.number_of_geo_ohm_cables > 0:

            geo_ohm_cables = self.get_all_geo_ohm_cables(tube)

            for geo_ohm_cable in geo_ohm_cables:

                self.update_static_geo_ohm_cable(geo_ohm_cable)

                electrodes = self.get_all_electrodes(geo_ohm_cable)
                
                for electrode in electrodes:

                    self.update_static_electrode(electrode)
        
        self.tubes[tube.groundwater_monitoring_tube_static_id] = static_tube_data
        self.datafile['monitoringTubes'] = self.tubes
    
    def get_all_geo_ohm_cables(self, tube: models.GroundwaterMonitoringTubesStatic):
        return models.GeoOhmCable.objects.filter(
                groundwater_monitoring_tube_static = tube.groundwater_monitoring_tube_static_id,
            )

    def update_static_geo_ohm_cable(self, geo_ohm_cable: models.GeoOhmCable):
        geo_ohm_cable_data = {
            "cableNumber": geo_ohm_cable.cable_number
        }
        self.geo_ohm_cables[geo_ohm_cable.geo_ohm_cable_id] = geo_ohm_cable_data
        self.datafile['geoOhmCables'] = self.geo_ohm_cables
    
    def get_all_electrodes(self, geo_ohm_cable: models.GeoOhmCable):
        return models.ElectrodeStatic.objects.filter(
                geo_ohm_cable = geo_ohm_cable.geo_ohm_cable_id
            )

    def update_static_electrode(self, electrode: models.ElectrodeStatic):
        electrode_static_data = {
            "electrodePackingMaterial": electrode.electrode_packing_material,
            "electrodePosition": electrode.electrode_position,
        }

        self.electrodes[electrode.electrode_static_id] = electrode_static_data
        self.datafile['electrodes'] = self.electrodes
    

def get_static_source_doc_data(bro_well: models.GroundwaterMonitoringWellStatic) -> dict:
    """
    Retrieve all the data from the Django database to make it available for the source doc generation.
    """
    source_doc_data = {}

    # Initialize data retriever
    get_data = DjangoTableToDict(well = bro_well, datafile = source_doc_data)

    # Get all static data
    get_data.update_static_well()
    
    tubes = get_data.get_all_tubes()
    for tube in tubes:
        get_data.update_static_tube(tube)

    return source_doc_data

def create_registration_sourcedocs(
    quality_regime: str,
    delivery_accountable_party,
    well: models.GroundwaterMonitoringWellStatic,
    registrations_dir,
    # Might want to add a variable for with or without history
):

    """
    Try to create registration sourcedocuments for a well/tube/quality regime
    Registration requests are saved to .xml file in registrations folder
    """

    try:
        # Retrieve general static information of the well
        srcdocdata = get_static_source_doc_data(well)
        
        # # How many records are already registered -> change the reference
        records_in_register = records_in_registrations(srcdocdata['broId'])
        
        request_reference = f"{srcdocdata['broId']}_Registration_{records_in_register}"

        # Check what kind of request is required and make as followed.
        # Registrate with history
        gmw_registration_request = brx.gmw_registration_request(
            srcdoc="GMW_ConstructionWithHistory",
            requestReference=request_reference,
            deliveryAccountableParty=delivery_accountable_party,
            qualityRegime=quality_regime,
            srcdocdata=srcdocdata,
        )

        filename = request_reference + ".xml"
        gmw_registration_request.generate()
        gmw_registration_request.write_request(
            output_dir=registrations_dir, filename=filename
        )

        process_status = "succesfully_generated_registration_request"
        record, created = models.gmw_registration_log.objects.update_or_create(
            gwm_bro_id=srcdocdata['broId'],
            quality_regime=quality_regime,
            defaults=dict(
                comments="Succesfully generated registration request",
                date_modified=datetime.datetime.now(),
                validation_status=None,
                process_status=process_status,
                file=filename,
            ),
        )

    except Exception as e:

        process_status = "failed_to_generate_source_documents"
        record, created = models.gmw_registration_log.objects.update_or_create(
            bro_id=srcdocdata['broId'],
            quality_regime=quality_regime,
            defaults=dict(
                comments="Failed to create registration source document: {}".format(
                    e
                ),
                date_modified=datetime.datetime.now(),
                process_status=process_status,
            ),
        )


def validate_gmw_registration_request(
    registration_id, registrations_dir, acces_token_bro_portal, demo
):

    """
    Validate generated registration sourcedocuments
    """

    try:
        gmw_registration = models.gmw_registration_log.objects.get(
            id=registration_id
        )
        file = gmw_registration.file
        source_doc_file = os.path.join(registrations_dir, file)
        payload = open(source_doc_file)

        validation_info = brx.validate_sourcedoc(payload, acces_token_bro_portal, demo = demo)
        validation_status = validation_info["status"]

        if "errors" in validation_info:
            validation_errors = validation_info["errors"]
            comments = "Validated registration document, found errors: {}".format(
                validation_errors
            )

            record, created = models.gmw_registration_log.objects.update_or_create(
                id=registration_id,
                defaults=dict(
                    comments="Registration document is invalid, {}".format(
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


def check_delivery_status_levering(
    registration_id, registrations_dir, acces_token_bro_portal, demo
):

    """
    Check the status of a registration delivery
    Logs the status of the delivery in the database
    If delivery is approved, a GroundwaterLevelDossier object is created
    This means the registration process is concluded

    Parameters
    ----------
    registration_id : int
        unique id of the gmw registration in the database.
    acces_token_bro_portal : str
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
                    bro_id=upload_info.json()["brondocuments"][0]["broId"],
                    levering_status=upload_info.json()["brondocuments"][0]["status"],
                    last_changed=upload_info.json()["lastChanged"],
                    comments="registration request approved",
                    process_status="delivery_approved",
                ),
            )

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


class GetEvents:
    """
    A Class that helps retrieving different types of events.
    The events will have information linking to the data that changed.
    """
    def construction():
        return models.Event.objects.filter(
            event_name = 'construction',
            event_in_bro = False,
        )

    def wellHeadProtector():
        return models.Event.objects.filter(
            event_name = 'beschermconstructieVeranderd',
            event_in_bro = False,
        )
    
    def lengthening():
        return models.Event.objects.filter(
            event_name = 'buisOpgelengd',
            event_in_bro = False,
        )
    
    def shortening():
        return models.Event.objects.filter(
            event_name = 'buisIngekort',
            event_in_bro = False,
        )
    
    def groundLevelMeasuring():
        return models.Event.objects.filter(
            event_name = 'nieuweInmetingMaaiveld',
            event_in_bro = False,
        )
    
    def positionMeasuring():
        return models.Event.objects.filter(
            event_name = 'nieuweInmetingPosities',
            event_in_bro = False,
        )
    
    def groundLevel():
        return models.Event.objects.filter(
            event_name = 'nieuweBepalingMaaiveld',
            event_in_bro = False,
        )
    
    def owner():
        return models.Event.objects.filter(
            event_name = 'eigenaarVeranderd',
            event_in_bro = False,
        )
    
    def positions():
        return models.Event.objects.filter(
            event_name = 'construction',
            event_in_bro = False,
        )
    
    def electrodeStatus():
        return models.Event.objects.filter(
            event_name = 'construction',
            event_in_bro = False,
        )
    
    def maintainer():
        return models.Event.objects.filter(
            event_name = 'onderhouderVeranderd',
            event_in_bro = False,
        )
    
    def tubeStatus():
        return models.Event.objects.filter(
            event_name = 'buisstatusVeranderd',
            event_in_bro = False,
        )
    
    def insertion():
        return models.Event.objects.filter(
            event_name = 'buisdeelIngeplaatst',
            event_in_bro = False,
        )
    
    def shift():
        return models.Event.objects.filter(
            event_name = 'maaiveldVerlegd',
            event_in_bro = False,
        )

def gmw_registration_wells(
    acces_token_bro_portal, registrations_dir, demo
):

    """
    Run gmw registrations for all monitoring wells in the database
    Registrations has to be run multiple times to get all tubes registered
    This will not interfere with additions, as a check will be done on registration availibility
    """

    # Pak de construction events, filter welke events al in de BRO staan
    get_events = GetEvents()
    construction_events = get_events.construction()

    for event in construction_events:
        well = models.GroundwaterMonitoringWellStatic.objects.get(
                groundwater_monitoring_well_static_id = event.groundwater_monitoring_well_static
            )

        # Get some well properties
        registration_object_id_well = well.groundwater_monitoring_well_static_id
        quality_regime = well.quality_regime
        bro_id = well.bro_id

        # Check if there is already a registration for this well
        if not models.gmw_registration_log.objects.filter(
            bro_id=bro_id, quality_regime=quality_regime
        ).exists():

            # There is not a gmw registration object with this configuration
            # Create a new configuration by creating registration sourcedocs
            # By creating the sourcedocs (or failng to do so), a registration is made in the database
            # This registration is used to track the progress of the delivery in further steps

            delivery_accountable_party = str(well.delivery_accountable_party)
            registration = create_registration_sourcedocs(
                quality_regime,
                delivery_accountable_party,
                well,
                registrations_dir,
            )


def gmw_check_existing_registrations(
    acces_token_bro_portal, registrations_dir, demo
):
    """
    This function loops over all exists registrations in the database
    Depending on the status one of the following actions is carried out:
        - The sourcedocument for the registration is validated
        - The sourcedocument is delivered to the BRO
        - The status of a delivery is checked
        - If a delivery failed, it may be attempted again up to three times

    Parameters
    ----------
    acces_token_bro_portal : str
        access token for BRO bronhouderportaal: https://demo.bronhouderportaal-bro.nl/ .
    registrations_dir : str
        directory where registration sourcedocument xml's are stored
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
            # Succesfully generated a registration sourcedoc in the previous step
            # Validate the created sourcedocument
            if (
                get_registration_process_status(registration_id)
                == "succesfully_generated_registration_request"
            ):
                validation_status = validate_gmw_registration_request(
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
                validation_status = validate_gmw_registration_request(
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

        registrations_dir = GMW_AANLEVERING_SETTINGS["registrations_dir"]

        #print('start registrations')
        # Check the database for new wells/tubes and start a gmw registration for these objects if its it needed
        registration = gmw_registration_wells(
            acces_token_bro_portal, registrations_dir, demo
        )

        #print('check status')
        # Check existing registrations
        check = gmw_check_existing_registrations(
            acces_token_bro_portal, registrations_dir, demo
        )
