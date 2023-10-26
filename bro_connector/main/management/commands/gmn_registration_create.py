from django.core.management.base import BaseCommand
from main.settings.base import GMN_AANLEVERING_SETTINGS
from gmn_aanlevering.models import (
    GroundwaterMonitoringNet,
    MeasuringPoint,
    gmn_registration_log,
)
from datetime import datetime

import bro_exchange as brx
import os


class Command(BaseCommand):
    """
    Command to registrate a GMN command. Demo variable is used througout the command to determine other variables.
    """

    def handle(self, *args, **options):
        """
        This is the main function for the delivery process of the GMN to the BRO.
        It loops over all GMNs in the database, and checks for each instance where in the delivery process it is.
        Depending on this status, it runs the:
            1) Registration
            2) Validation
            3) Delivery
            4) Check of the delivery status
        The process status is stored in an gmn_registration_log object. Each network has one.
        """

        ### SETUP ###
        # Check demo settings and define required acces token
        demo = GMN_AANLEVERING_SETTINGS["demo"]
        if demo:
            acces_token_bro_portal = GMN_AANLEVERING_SETTINGS[
                "acces_token_bro_portal_demo"
            ]
        else:
            acces_token_bro_portal = GMN_AANLEVERING_SETTINGS[
                "acces_token_bro_portal_bro_connector"
            ]

        ### LOOP OVER GMNs ###
        monitoring_networks = GroundwaterMonitoringNet.objects.all()

        for monitoring_network in monitoring_networks:

            # Check if the network should be delivered to the bro. If not, skip this network
            if monitoring_network.deliver_to_bro == False:
                print(
                    f"Het {monitoring_network} moet niet aangeleverd worden, en wordt daarom overgeslagen."
                )
                continue


            # Check for an existing registration log.
            gmn_registration_log_qs = gmn_registration_log.objects.filter(
                gmn_bro_id=monitoring_network.gmn_bro_id,
                object_id_accountable_party=monitoring_network.object_id_accountable_party,
            )


            # Create startregistration xml file if required
            if (
                not gmn_registration_log_qs.exists()
                or gmn_registration_log_qs.first().process_status
                == "failed_to_generate_source_documents"
            ):
                print(
                    f"Geen succesvolle registratie gevonden voor {monitoring_network}. Er wordt nu een registratie bestand aangemaakt."
                )
                gmn_registration_log_obj = self.create_registration_file(
                    monitoring_network,
                )
            else:
                gmn_registration_log_obj = gmn_registration_log_qs.first()

                # If the delivery allready is completely succesfull, skip everything for this meetnet.
                if gmn_registration_log_obj.process_status == "delivery_approved":
                    continue

            # Validate startregistration if required
            if gmn_registration_log_obj.process_status in [
                "succesfully_generated_startregistration_request",
                "failed_to_validate_sourcedocument",
            ]:
                print(f"{monitoring_network} word gevalideerd.")

                self.validate_registration(
                    gmn_registration_log_obj, acces_token_bro_portal
                )

            # Deliver startregistration if validation succeeded, or previous deliveries failed (to a max of 3)
            if (
                gmn_registration_log_obj.process_status
                == "source_document_validation_succesful"
                and gmn_registration_log_obj.validation_status == "VALIDE"
            ) or (
                gmn_registration_log_obj.process_status
                == "failed_to_deliver_sourcedocuments"
                and gmn_registration_log_obj.levering_status in ["1", "2"]
            ):
                print(f"De registratie van {monitoring_network} word aangeleverd.")
                self.deliver_registration(
                    gmn_registration_log_obj, acces_token_bro_portal
                )
                

            # If delivery failed 3 times: break the process
            if (
                gmn_registration_log_obj.process_status
                == "failed_to_deliver_sourcedocuments"
                and gmn_registration_log_obj.levering_status == "3"
            ):
                print(
                    f'De registratie van {monitoring_network} is al 3 keer gefaald. Controleer handmatig wat er fout gaat en reset de leveringstatus handmatig naar "nog niet aangeleverd" om het opnieuw te proberen.'
                )
                continue
            
            # Check the delivery status
            if (
                gmn_registration_log_obj.process_status
                == "succesfully_delivered_sourcedocuments"
                and gmn_registration_log_obj.levering_status_info != "OPGENOMEN_LVBRO"
                and gmn_registration_log_obj.levering_id is not None
            ):
                print(
                    f"De status van de levering van {monitoring_network} wordt gecontroleerd."
                )
                self.check_delivery_status_levering(
                    gmn_registration_log_obj, acces_token_bro_portal
                )

    def create_registration_file(self, monitoring_network):
        """
        This function handles the start registration of a single monitoringnetwork.
        It logs its results in a gmn_registration_log instance, with the monitoringnetwork_name as name.
        Saves the xml file in gmn_aanlevering/registrations
        """
        try:
            # Set default quality regime IMBRO if value is not filled in in GMN instance
            if monitoring_network.quality_regime == None:
                quality_regime = "IMBRO"
            else:
                quality_regime = monitoring_network.quality_regime

            # Creating measuringpoints list
            measuringpoint_objs = MeasuringPoint.objects.filter(gmn=monitoring_network)
            measuringpoints = []

            for measuringpoint_obj in measuringpoint_objs:
                well_code = (
                    measuringpoint_obj.groundwater_monitoring_tube.groundwater_monitoring_well.bro_id
                )
                measuringpoint = {
                    "measuringPointCode": measuringpoint_obj.code,
                    "monitoringTube": {
                        "broId": well_code,
                        "tubeNumber": measuringpoint_obj.groundwater_monitoring_tube.tube_number,
                    },
                }
                measuringpoints.append(measuringpoint)

            # Create source docs
            srcdocdata = {
                "objectIdAccountableParty": monitoring_network.object_id_accountable_party,
                "name": monitoring_network.name,
                "deliveryContext": monitoring_network.delivery_context,
                "monitoringPurpose": monitoring_network.monitoring_purpose,
                "groundwaterAspect": monitoring_network.groundwater_aspect,
                "startDateMonitoring": [
                    str(monitoring_network.start_date_monitoring),
                    "date",
                ],
                "measuringPoints": measuringpoints,
            }

            # Initialize the gmn_registration_request instance
            gmn_startregistration_request = brx.gmn_registration_request(
                srcdoc="GMN_StartRegistration",
                requestReference=f"register {monitoring_network.name}",
                deliveryAccountableParty=monitoring_network.delivery_accountable_party,
                qualityRegime=quality_regime,
                srcdocdata=srcdocdata,
            )

            # Generate the startregistration request
            gmn_startregistration_request.generate()

            # Write the request
            xml_filename = f"register {monitoring_network.name}.xml"
            gmn_startregistration_request.write_request(
                output_dir=GMN_AANLEVERING_SETTINGS["registrations_dir"],
                filename=xml_filename,
            )

            # Create a log instance for the request
            log_obj = gmn_registration_log.objects.update_or_create(
                object_id_accountable_party=monitoring_network.object_id_accountable_party,
                gmn_bro_id=monitoring_network.gmn_bro_id,
                quality_regime=monitoring_network.quality_regime,
                defaults=dict(
                    comments="Succesfully generated startregistration request",
                    date_modified=datetime.now(),
                    validation_status=None,
                    process_status="succesfully_generated_startregistration_request",
                    file=xml_filename,
                ),
            )
            return log_obj[0]

        except Exception as e:
            log_obj = gmn_registration_log.objects.update_or_create(
                object_id_accountable_party=monitoring_network.object_id_accountable_party,
                gmn_bro_id=monitoring_network.gmn_bro_id,
                quality_regime=monitoring_network.quality_regime,
                defaults=dict(
                    comments=f"Failed to create startregistration source document: {e}",
                    date_modified=datetime.now(),
                    process_status="failed_to_generate_source_documents",
                ),
            )

            return log_obj[0]

    def validate_registration(self, gmn_registration_log_obj, acces_token_bro_portal):
        """
        This function validates new registrations, and registers its process in the log instance.
        """
        try:
            filename = gmn_registration_log_obj.file
            filepath = os.path.join(
                GMN_AANLEVERING_SETTINGS["registrations_dir"], filename
            )
            payload = open(filepath)
            validation_info = brx.validate_sourcedoc(
                payload, acces_token_bro_portal, demo =  GMN_AANLEVERING_SETTINGS["demo"]
            )
            validation_status = validation_info["status"]

            if "errors" in validation_info:
                validation_errors = validation_info["errors"]
                comments = f"Found errors during the validation of {gmn_registration_log_obj.object_id_accountable_party}: {validation_errors}"
                process_status = "failed_to_validate_sourcedocument"
            elif validation_status == 500:
                comments = f"BRO server is down. Please try again later"
                process_status = "failed_to_validate_sourcedocument"
            elif validation_status == 400:
                comments = f"Something went wrong while validating. Try again."
                process_status = "failed_to_validate_sourcedocument"
            else:
                comments = f"Succesfully validated sourcedocument for meetnet {gmn_registration_log_obj.object_id_accountable_party}."
                process_status = "source_document_validation_succesful"

            print(comments)

            gmn_registration_log.objects.update_or_create(
                id=gmn_registration_log_obj.id,
                defaults=dict(
                    comments=comments,
                    validation_status=validation_status,
                    process_status=process_status,
                ),
            )

        except Exception as e:
            gmn_registration_log.objects.update_or_create(
                id=gmn_registration_log_obj.id,
                defaults=dict(
                    comments=f"Exception occured during validation of sourcedocuments: {e}",
                    process_status="failed_to_validate_sourcedocument",
                ),
            )

    def deliver_registration(self, gmn_registration_log_obj, acces_token_bro_portal):
        """
        Function to actually deliver the registration.
        """
        current_delivery_status = int(gmn_registration_log_obj.levering_status)

        try:
            # Prepare and deliver registration
            filename = gmn_registration_log_obj.file
            filepath = os.path.join(
                GMN_AANLEVERING_SETTINGS["registrations_dir"], filename
            )
            payload = open(filepath)
            request = {filename: payload}

            upload_info = brx.upload_sourcedocs_from_dict(
                request, acces_token_bro_portal, demo = GMN_AANLEVERING_SETTINGS["demo"]
            )

            # Log the result
            if upload_info == "Error":
                delivery_status = str(current_delivery_status + 1)

                print(
                    f"De aanlevering van {gmn_registration_log_obj.object_id_accountable_party} is niet gelukt. De levering is nu {delivery_status} keer gefaald."
                )
                gmn_registration_log.objects.update_or_create(
                    id=gmn_registration_log_obj.id,
                    defaults={
                        "date_modified": datetime.now(),
                        "comments": "Error occured during delivery of sourcedocument",
                        "levering_status": delivery_status,
                        "process_status": "failed_to_deliver_sourcedocuments",
                    },
                )
            else:
                print(
                    f"De levering van {gmn_registration_log_obj.object_id_accountable_party} is geslaagd"
                )
                gmn_registration_log.objects.update_or_create(
                    id=gmn_registration_log_obj.id,
                    defaults={
                        "date_modified": datetime.now(),
                        "comments": "Succesfully delivered startregistration sourcedocument",
                        "levering_status": "4",
                        "levering_status_info": upload_info.json()["status"],
                        "lastchanged": upload_info.json()["lastChanged"],
                        "levering_id": upload_info.json()["identifier"],
                        "process_status": "succesfully_delivered_sourcedocuments",
                    },
                )

        except Exception as e:
            delivery_status = str(current_delivery_status + 1)
            print(
                f"De aanlevering van {gmn_registration_log_obj.object_id_accountable_party} is niet gelukt. De levering is nu {delivery_status} keer gefaald."
            )

            gmn_registration_log.objects.update_or_create(
                id=gmn_registration_log_obj.id,
                defaults={
                    "date_modified": datetime.now(),
                    "comments": f"Exception occured during delivery of startregistration sourcedocument: {e}",
                    "levering_status": delivery_status,
                    "process_status": "failed_to_deliver_sourcedocuments",
                },
            )

    def check_delivery_status_levering(
        self, gmn_registration_log_obj, acces_token_bro_portal
    ):
        """
        Function to check and log the status of the delivery
        """
        try:
            delivery_status_info = brx.check_delivery_status(
                gmn_registration_log_obj.levering_id,
                acces_token_bro_portal,
                demo = GMN_AANLEVERING_SETTINGS["demo"],
            )

            delivery_errors = delivery_status_info.json()['brondocuments'][0]['errors']
            
            if delivery_status_info.json()['status'] == "DOORGELEVERD" and delivery_status_info.json()["brondocuments"][0]["status"] == "OPGENOMEN_LVBRO":
                gmn_registration_log.objects.update_or_create(
                    id=gmn_registration_log_obj.id,
                    defaults=dict(
                        gmn_bro_id=delivery_status_info.json()["brondocuments"][0]["broId"],
                        levering_status_info=delivery_status_info.json()["brondocuments"][0]["status"],
                        last_changed=delivery_status_info.json()["lastChanged"],
                        comments="Startregistration request approved",
                        process_status="delivery_approved",
                    ),
                )

                # Remove the sourcedocument file if delivery is approved
                filename = gmn_registration_log_obj.file
                filepath = os.path.join(
                    GMN_AANLEVERING_SETTINGS["registrations_dir"], filename
                )
                os.remove(filepath)

            
            elif delivery_errors:
                
                gmn_registration_log.objects.update_or_create(
                    id=gmn_registration_log_obj.id,
                    defaults=dict(
                        last_changed=delivery_status_info.json()["lastChanged"],
                        comments=f"Found errors during the check of {gmn_registration_log_obj.object_id_accountable_party}: {delivery_errors}",
                    ),
                )
            
            else:
                gmn_registration_log.objects.update_or_create(
                    id=gmn_registration_log_obj.id,
                    defaults=dict(
                        levering_status_info=delivery_status_info.json()["brondocuments"][0]["status"],
                        last_changed=delivery_status_info.json()["lastChanged"],
                        comments="Startregistration request not yet approved",
                    ),
                )


        except Exception as e:
            gmn_registration_log.objects.update_or_create(
                id=gmn_registration_log_obj.id,
                defaults={
                    "comments": f"Error occured during status check of delivery: {e}",
                },
            )
