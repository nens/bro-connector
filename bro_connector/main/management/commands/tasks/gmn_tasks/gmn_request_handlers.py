from gmn.models import (
    gmn_bro_sync_log,
    IntermediateEvent,
    MeasuringPoint,
    GroundwaterMonitoringNet,
)
from datetime import datetime
from main.settings.base import gmn_SETTINGS

import bro_exchange as brx
import os
import time


class StartRegistrationGMN:
    """
    Class to handle the startregistration of a GMN.
    """

    def __init__(self, event, demo, acces_token_bro_portal):
        self.event = event
        self.demo = demo
        self.acces_token_bro_portal = acces_token_bro_portal
        self.monitoring_network = event.gmn
        self.gmn_bro_register_log_obj = None

    def handle(self, check_only):
        """
        Main function to handle the startregistration of a GMN.
        The status of the delivery is registered in a gmn_bro_sync_log instance.
        When the registration delivery has successfully been handled, the synced_to_bro of the event is set to True.
        As long as synced_to_bro is False, this function will be triggered, and the delivery process will be picked up, depending on the status found in the log.
        """

        # Check for an existing registration log.
        gmn_bro_sync_log_qs = gmn_bro_sync_log.objects.filter(
            gmn_bro_id=self.monitoring_network.gmn_bro_id,
            object_id_accountable_party=self.monitoring_network.object_id_accountable_party,
            event_type="GMN_StartRegistration",
        )

        if not check_only:

            # Create startregistration xml file if required
            if (
                not gmn_bro_sync_log_qs.exists()
                or gmn_bro_sync_log_qs.first().process_status
                == "failed_to_generate_source_documents"
            ):
                print(
                    f"Geen succesvolle registratie gevonden voor {self.monitoring_network}. Er wordt nu een registratie bestand aangemaakt."
                )
                self.create_registration_file()
            else:
                self.gmn_bro_register_log_obj = gmn_bro_sync_log_qs.first()

            # Validate startregistration if required
            if self.gmn_bro_register_log_obj.process_status in [
                "succesfully_generated_startregistration_request",
                "failed_to_validate_sourcedocument",
            ]:
                print(f"{self.monitoring_network} word gevalideerd.")

                self.validate_registration()

            # Deliver startregistration if validation succeeded, or previous deliveries failed (to a max of 3)
            if (
                self.gmn_bro_register_log_obj.process_status
                == "source_document_validation_succesful"
                and self.gmn_bro_register_log_obj.validation_status == "VALIDE"
            ) or (
                self.gmn_bro_register_log_obj.process_status
                == "failed_to_deliver_sourcedocuments"
                and self.gmn_bro_register_log_obj.levering_status in ["1", "2"]
            ):
                print(f"De registratie van {self.monitoring_network} word aangeleverd.")
                self.deliver_registration()

            # If delivery failed 3 times: break the process
            if (
                self.gmn_bro_register_log_obj.process_status
                == "failed_to_deliver_sourcedocuments"
                and self.gmn_bro_register_log_obj.levering_status == "3"
            ):
                print(
                    f'De registratie van {self.monitoring_network} is al 3 keer gefaald. Controleer handmatig wat er fout gaat en reset de leveringstatus handmatig naar "nog niet aangeleverd" om het opnieuw te proberen.'
                )
                return

        # Check the delivery status
        if not self.gmn_bro_register_log_obj:
            return
        if (
            self.gmn_bro_register_log_obj.process_status
            == "succesfully_delivered_sourcedocuments"
            and self.gmn_bro_register_log_obj.levering_status_info != "OPGENOMEN_LVBRO"
            and self.gmn_bro_register_log_obj.levering_id is not None
        ):
            print(
                f"De status van de levering van {self.monitoring_network} wordt gecontroleerd."
            )
            self.check_delivery_status_levering()

    def create_registration_file(self):
        """
        Function to create registration xml file for a startregistration of a gmn
        """
        try:
            # Set default quality regime IMBRO if value is not filled in in GMN instance
            if self.monitoring_network.quality_regime == None:
                quality_regime = "IMBRO"
            else:
                quality_regime = self.monitoring_network.quality_regime

            # Creating measuringpoints list
            measuringpoint_objs = MeasuringPoint.objects.filter(
                gmn=self.monitoring_network
            )

            if not measuringpoint_objs.exists():
                print(
                    f"Er zijn geen meetpunten gevonden in het {self.monitoring_network}. Voeg er minimaal 1 toe, zodat de startregistratie kan starten"
                )
                raise Exception("No Measuringpoints found in GMN")

            measuringpoints = []

            for measuringpoint_obj in measuringpoint_objs:
                well_code = (
                    measuringpoint_obj.groundwater_monitoring_tube.groundwater_monitoring_well_static.bro_id
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
                "objectIdAccountableParty": self.monitoring_network.object_id_accountable_party,
                "name": self.monitoring_network.name,
                "deliveryContext": self.monitoring_network.delivery_context,
                "monitoringPurpose": self.monitoring_network.monitoring_purpose,
                "groundwaterAspect": self.monitoring_network.groundwater_aspect,
                "startDateMonitoring": [
                    str(self.monitoring_network.start_date_monitoring),
                    "date",
                ],
                "measuringPoints": measuringpoints,
            }

            # Initialize the gmn_registration_request instance
            gmn_startregistration_request = brx.gmn_registration_request(
                srcdoc="GMN_StartRegistration",
                requestReference=f"register {self.monitoring_network.name}",
                deliveryAccountableParty=self.monitoring_network.delivery_accountable_party,
                qualityRegime=quality_regime,
                srcdocdata=srcdocdata,
            )

            # Generate the startregistration request
            gmn_startregistration_request.generate()

            # Write the request
            xml_filename = f"register {self.monitoring_network.name}.xml"
            gmn_startregistration_request.write_request(
                output_dir=gmn_SETTINGS["registrations_dir"],
                filename=xml_filename,
            )

            # Create a log instance for the request
            (
                self.gmn_bro_register_log_obj,
                created,
            ) = gmn_bro_sync_log.objects.update_or_create(
                object_id_accountable_party=self.monitoring_network.object_id_accountable_party,
                gmn_bro_id=self.monitoring_network.gmn_bro_id,
                quality_regime=self.monitoring_network.quality_regime,
                event_type="GMN_StartRegistration",
                defaults=dict(
                    comments="Succesfully generated startregistration request",
                    date_modified=datetime.now(),
                    validation_status=None,
                    process_status="succesfully_generated_startregistration_request",
                    file=xml_filename,
                ),
            )

        except Exception as e:
            (
                self.gmn_bro_register_log_obj,
                created,
            ) = gmn_bro_sync_log.objects.update_or_create(
                object_id_accountable_party=self.monitoring_network.object_id_accountable_party,
                gmn_bro_id=self.monitoring_network.gmn_bro_id,
                quality_regime=self.monitoring_network.quality_regime,
                event_type="GMN_StartRegistration",
                defaults=dict(
                    comments=f"Failed to create startregistration source document: {e}",
                    date_modified=datetime.now(),
                    process_status="failed_to_generate_source_documents",
                ),
            )

    def validate_registration(self):
        """
        This function validates new registrations, and registers its process in the log instance.
        """
        try:
            filename = self.gmn_bro_register_log_obj.file
            filepath = os.path.join(gmn_SETTINGS["registrations_dir"], filename)
            payload = open(filepath)

            validation_info = brx.validate_sourcedoc(
                payload, bro_info=self.acces_token_bro_portal, demo=self.demo
            )

            errors_count = len(validation_info["errors"])

            validation_status = validation_info["status"]

            if errors_count > 0:
                validation_errors = validation_info["errors"]
                comments = f"Found errors during the validation of {self.monitoring_network}: {validation_errors}"
                process_status = "failed_to_validate_sourcedocument"
            elif validation_status == 500:
                comments = f"BRO server is down. Please try again later"
                process_status = "failed_to_validate_sourcedocument"
            elif validation_status == 400:
                comments = f"Something went wrong while validating. Try again."
                process_status = "failed_to_validate_sourcedocument"
            else:
                comments = f"Succesfully validated sourcedocument for meetnet {self.monitoring_network}."
                process_status = "source_document_validation_succesful"

            print(comments)

            (
                self.gmn_bro_register_log_obj,
                created,
            ) = gmn_bro_sync_log.objects.update_or_create(
                id=self.gmn_bro_register_log_obj.id,
                defaults=dict(
                    comments=comments,
                    validation_status=validation_status,
                    process_status=process_status,
                ),
            )

        except Exception as e:
            (
                self.gmn_bro_register_log_obj,
                created,
            ) = gmn_bro_sync_log.objects.update_or_create(
                id=self.gmn_bro_register_log_obj.id,
                defaults=dict(
                    comments=f"Exception occured during validation of sourcedocuments: {e}",
                    process_status="failed_to_validate_sourcedocument",
                ),
            )

    def deliver_registration(self):
        """
        Function to actually deliver the registration.
        """
        current_delivery_status = int(self.gmn_bro_register_log_obj.levering_status)

        try:
            # Prepare and deliver registration
            filename = self.gmn_bro_register_log_obj.file
            filepath = os.path.join(gmn_SETTINGS["registrations_dir"], filename)
            payload = open(filepath)
            request = {filename: payload}

            upload_info = brx.upload_sourcedocs_from_dict(
                request, token=self.acces_token_bro_portal["token"], demo=self.demo
            )

            # Log the result
            if upload_info == "Error":
                delivery_status = str(current_delivery_status + 1)

                print(
                    f"De aanlevering van {self.monitoring_network} is niet gelukt. De levering is nu {delivery_status} keer gefaald."
                )
                (
                    self.gmn_bro_register_log_obj,
                    created,
                ) = gmn_bro_sync_log.objects.update_or_create(
                    id=self.gmn_bro_register_log_obj.id,
                    defaults={
                        "date_modified": datetime.now(),
                        "comments": "Error occured during delivery of sourcedocument",
                        "levering_status": delivery_status,
                        "process_status": "failed_to_deliver_sourcedocuments",
                    },
                )

            else:
                print(f"De levering van {self.monitoring_network} is geslaagd")
                (
                    self.gmn_bro_register_log_obj,
                    created,
                ) = gmn_bro_sync_log.objects.update_or_create(
                    id=self.gmn_bro_register_log_obj.id,
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
                time.sleep(10)

        except Exception as e:
            delivery_status = str(current_delivery_status + 1)
            print(
                f"De aanlevering van {self.monitoring_network} is niet gelukt. De levering is nu {delivery_status} keer gefaald."
            )

            (
                self.gmn_bro_register_log_obj,
                created,
            ) = gmn_bro_sync_log.objects.update_or_create(
                id=self.gmn_bro_register_log_obj.id,
                defaults={
                    "date_modified": datetime.now(),
                    "comments": f"Exception occured during delivery of startregistration sourcedocument: {e}",
                    "levering_status": delivery_status,
                    "process_status": "failed_to_deliver_sourcedocuments",
                },
            )

    def check_delivery_status_levering(self):
        """
        Function to check and log the status of the delivery
        """
        try:
            delivery_status_info = brx.check_delivery_status(
                self.gmn_bro_register_log_obj.levering_id,
                self.acces_token_bro_portal["token"],
                demo=self.demo,
            )

            delivery_errors = delivery_status_info.json()["brondocuments"][0]["errors"]

            if (
                delivery_status_info.json()["status"] == "DOORGELEVERD"
                and delivery_status_info.json()["brondocuments"][0]["status"]
                == "OPGENOMEN_LVBRO"
            ):
                (
                    self.gmn_bro_register_log_obj,
                    created,
                ) = gmn_bro_sync_log.objects.update_or_create(
                    id=self.gmn_bro_register_log_obj.id,
                    defaults=dict(
                        gmn_bro_id=delivery_status_info.json()["brondocuments"][0][
                            "broId"
                        ],
                        levering_status_info=delivery_status_info.json()[
                            "brondocuments"
                        ][0]["status"],
                        last_changed=delivery_status_info.json()["lastChanged"],
                        comments="Startregistration request approved",
                        process_status="delivery_approved",
                    ),
                )

                # Save the BRO ID to the GMN
                GroundwaterMonitoringNet.objects.update_or_create(
                    object_id_accountable_party=self.monitoring_network.object_id_accountable_party,
                    defaults=dict(
                        gmn_bro_id=delivery_status_info.json()["brondocuments"][0][
                            "broId"
                        ],
                    ),
                )

                # Set the synced_to_bro of the event that triggered this process tot True
                IntermediateEvent.objects.update_or_create(
                    id=self.event.id,
                    defaults=dict(
                        synced_to_bro=True,
                    ),
                )

                # Set the synced_to_bro of all events of GMN_MeasuringPoint to True, because these measuringpoints were handled with the startregistration
                added_measuringpoints = MeasuringPoint.objects.filter(
                    gmn=self.monitoring_network
                )

                for added_measuringpoint in added_measuringpoints:
                    IntermediateEvent.objects.update_or_create(
                        gmn=self.monitoring_network,
                        measuring_point=added_measuringpoint,
                        defaults=dict(
                            synced_to_bro=True,
                        ),
                    )

                    MeasuringPoint.objects.update_or_create(
                        id=added_measuringpoint.id,
                        defaults=dict(
                            synced_to_bro=True,
                        ),
                    )

                # Remove the sourcedocument file if delivery is approved
                filename = self.gmn_bro_register_log_obj.file
                filepath = os.path.join(gmn_SETTINGS["registrations_dir"], filename)
                os.remove(filepath)

            elif delivery_errors:
                (
                    self.gmn_bro_register_log_obj,
                    created,
                ) = gmn_bro_sync_log.objects.update_or_create(
                    id=self.gmn_bro_register_log_obj.id,
                    defaults=dict(
                        last_changed=delivery_status_info.json()["lastChanged"],
                        comments=f"Found errors during the check of {self.monitoring_network}: {delivery_errors}",
                    ),
                )

            else:
                (
                    self.gmn_bro_register_log_obj,
                    created,
                ) = gmn_bro_sync_log.objects.update_or_create(
                    id=self.gmn_bro_register_log_obj.id,
                    defaults=dict(
                        levering_status_info=delivery_status_info.json()[
                            "brondocuments"
                        ][0]["status"],
                        last_changed=delivery_status_info.json()["lastChanged"],
                        comments="Startregistration request not yet approved",
                    ),
                )

        except Exception as e:
            (
                self.gmn_bro_register_log_obj,
                created,
            ) = gmn_bro_sync_log.objects.update_or_create(
                id=self.gmn_bro_register_log_obj.id,
                defaults={
                    "comments": f"Error occured during status check of delivery: {e}",
                },
            )


class MeasuringPointAddition:
    """
    Class to handle the addition of a Measuringpoint to a GMN.
    """

    def __init__(self, event, demo, acces_token_bro_portal):
        self.event = event
        self.demo = demo
        self.acces_token_bro_portal = acces_token_bro_portal
        self.monitoring_network = event.gmn
        self.measuringpoint = event.measuring_point
        self.gmn_bro_addition_log_obj = None

    def handle(self, check_only):
        """
        Main function to handle the addition of a meauringpoint to a GMN.
        The status of the delivery is registered in a GMN_sync_log instance.
        When the addition delivery has successfully been handled, the synced_to_bro of the event is set to True.
        As long as synced_to_bro is False, this function will be triggered, and the delivery process will be picked up, depending on the status found in the log.
        """
        # If gmn bro id doesnt exist yet, the network hasnt been registered yet
        if self.monitoring_network.gmn_bro_id is None:
            return

        # Check for an existing addition log.
        gmn_bro_sync_log_qs = gmn_bro_sync_log.objects.filter(
            gmn_bro_id=self.monitoring_network.gmn_bro_id,
            object_id_accountable_party=self.monitoring_network.object_id_accountable_party,
            event_type="GMN_MeasuringPoint",
            measuringpoint=self.measuringpoint,
        )

        if not check_only:

            # Create addition xml file if required
            if (
                not gmn_bro_sync_log_qs.exists()
                or gmn_bro_sync_log_qs.first().process_status
                == "failed_to_generate_source_documents"
            ):
                print(
                    f"Geen succesvolle addition gevonden voor {self.event.measuring_point}. Er wordt nu een addition bestand aangemaakt."
                )
                self.create_addition_file()
            else:
                self.gmn_bro_addition_log_obj = gmn_bro_sync_log_qs.first()

            # Validate addition registration if required
            if self.gmn_bro_addition_log_obj.process_status in [
                "succesfully_generated_addition_request",
                "failed_to_validate_sourcedocument",
            ]:
                print(
                    f"De toevoeging van {self.measuringpoint} aan het {self.monitoring_network} word gevalideerd."
                )

                self.validate_registration()

            # Deliver addition registratino if validation succeeded, or previous deliveries failed (to a max of 3)
            if (
                self.gmn_bro_addition_log_obj.process_status
                == "source_document_validation_succesful"
                and self.gmn_bro_addition_log_obj.validation_status == "VALIDE"
            ) or (
                self.gmn_bro_addition_log_obj.process_status
                == "failed_to_deliver_sourcedocuments"
                and self.gmn_bro_addition_log_obj.levering_status in ["1", "2"]
            ):
                print(
                    f"De registratie van de addition aan {self.monitoring_network} word aangeleverd."
                )
                self.deliver_registration()

            # If delivery failed 3 times: break the process
            if (
                self.gmn_bro_addition_log_obj.process_status
                == "failed_to_deliver_sourcedocuments"
                and self.gmn_bro_addition_log_obj.levering_status == "3"
            ):
                print(
                    f'De registratie van de addition aan  {self.monitoring_network} is al 3 keer gefaald. Controleer handmatig wat er fout gaat en reset de leveringstatus handmatig naar "nog niet aangeleverd" om het opnieuw te proberen.'
                )
                return

        # Check the delivery status
        if not self.gmn_bro_addition_log_obj:
            return
        if (
            self.gmn_bro_addition_log_obj.process_status
            == "succesfully_delivered_sourcedocuments"
            and self.gmn_bro_addition_log_obj.levering_status_info != "OPGENOMEN_LVBRO"
            and self.gmn_bro_addition_log_obj.levering_id is not None
        ):
            print(
                f"De status van de addition van {self.measuringpoint} aan {self.monitoring_network} wordt gecontroleerd."
            )
            self.check_delivery_status_levering()

    def create_addition_file(self):
        """
        Function to create the addition xml file
        """
        try:
            # Set default quality regime IMBRO if value is not filled in in GMN instance
            if self.monitoring_network.quality_regime == None:
                quality_regime = "IMBRO"
            else:
                quality_regime = self.monitoring_network.quality_regime

            measuringpoint = {
                "measuringPointCode": self.measuringpoint.code,
                "monitoringTube": {
                    "broId": self.measuringpoint.groundwater_monitoring_tube.groundwater_monitoring_well.bro_id,
                    "tubeNumber": self.measuringpoint.groundwater_monitoring_tube.tube_number,
                },
            }

            # Create source docs
            srcdocdata = {
                "eventDate": [
                    str(self.event.event_date),
                    "date",
                ],
                "measuringPoint": measuringpoint,
            }

            # Initialize the gmn_registration_request instance
            gmn_addition_request = brx.gmn_registration_request(
                srcdoc="GMN_MeasuringPoint",
                broId=self.monitoring_network.gmn_bro_id,
                requestReference=f"add {self.measuringpoint} to {self.monitoring_network.name}",
                deliveryAccountableParty=self.monitoring_network.delivery_accountable_party,
                qualityRegime=quality_regime,
                srcdocdata=srcdocdata,
            )

            # Generate the startregistration request
            gmn_addition_request.generate()

            # Write the request
            xml_filename = f"addition {self.monitoring_network.name}.xml"
            gmn_addition_request.write_request(
                output_dir=gmn_SETTINGS["additions_dir"],
                filename=xml_filename,
            )

            # Create a log instance for the request
            (
                self.gmn_bro_addition_log_obj,
                created,
            ) = gmn_bro_sync_log.objects.update_or_create(
                object_id_accountable_party=self.monitoring_network.object_id_accountable_party,
                gmn_bro_id=self.monitoring_network.gmn_bro_id,
                quality_regime=self.monitoring_network.quality_regime,
                measuringpoint=self.measuringpoint,
                event_type="GMN_MeasuringPoint",
                defaults=dict(
                    comments="Succesfully generated addition request",
                    date_modified=datetime.now(),
                    validation_status=None,
                    process_status="succesfully_generated_addition_request",
                    file=xml_filename,
                ),
            )

        except Exception as e:
            (
                self.gmn_bro_addition_log_obj,
                created,
            ) = gmn_bro_sync_log.objects.update_or_create(
                object_id_accountable_party=self.monitoring_network.object_id_accountable_party,
                gmn_bro_id=self.monitoring_network.gmn_bro_id,
                quality_regime=self.monitoring_network.quality_regime,
                event_type="GMN_MeasuringPoint",
                measuringpoint=self.measuringpoint,
                defaults=dict(
                    comments=f"Failed to create addition source document: {e}",
                    date_modified=datetime.now(),
                    process_status="failed_to_generate_source_documents",
                ),
            )

    def validate_registration(self):
        """
        This function validates new additions, and registers its process in the log instance.
        """
        try:
            filename = self.gmn_bro_addition_log_obj.file
            filepath = os.path.join(gmn_SETTINGS["additions_dir"], filename)
            payload = open(filepath)

            validation_info = brx.validate_sourcedoc(
                payload, self.acces_token_bro_portal, self.demo
            )

            errors_count = len(validation_info["errors"])

            validation_status = validation_info["status"]

            if errors_count > 0:
                validation_errors = validation_info["errors"]
                comments = f"Found errors during the validation of the addition to {self.monitoring_network}: {validation_errors}"
                process_status = "failed_to_validate_sourcedocument"
            elif validation_status == 500:
                comments = f"BRO server is down. Please try again later"
                process_status = "failed_to_validate_sourcedocument"
            elif validation_status == 400:
                comments = f"Something went wrong while validating. Try again."
                process_status = "failed_to_validate_sourcedocument"
            else:
                comments = f"Succesfully validated sourcedocument for addition to meetnet {self.monitoring_network}."
                process_status = "source_document_validation_succesful"

            print(comments)

            (
                self.gmn_bro_addition_log_obj,
                created,
            ) = gmn_bro_sync_log.objects.update_or_create(
                id=self.gmn_bro_addition_log_obj.id,
                defaults=dict(
                    comments=comments,
                    validation_status=validation_status,
                    process_status=process_status,
                ),
            )

        except Exception as e:
            (
                self.gmn_bro_addition_log_obj,
                created,
            ) = gmn_bro_sync_log.objects.update_or_create(
                id=self.gmn_bro_addition_log_obj.id,
                defaults=dict(
                    comments=f"Exception occured during validation of sourcedocuments: {e}",
                    process_status="failed_to_validate_sourcedocument",
                ),
            )

    def deliver_registration(self):
        """
        Function to actually deliver the addition.
        """
        current_delivery_status = int(self.gmn_bro_addition_log_obj.levering_status)

        try:
            # Prepare and deliver registration
            filename = self.gmn_bro_addition_log_obj.file
            filepath = os.path.join(gmn_SETTINGS["additions_dir"], filename)
            payload = open(filepath)
            request = {filename: payload}
            print(self.acces_token_bro_portal["token"])
            upload_info = brx.upload_sourcedocs_from_dict(
                request, token=self.acces_token_bro_portal["token"], demo=self.demo
            )

            # Log the result
            if upload_info == "Error":
                delivery_status = str(current_delivery_status + 1)

                print(
                    f"De addition van {self.measuringpoint} aan het {self.monitoring_network} is niet gelukt. De levering is nu {delivery_status} keer gefaald."
                )
                (
                    self.gmn_bro_addition_log_obj,
                    created,
                ) = gmn_bro_sync_log.objects.update_or_create(
                    id=self.gmn_bro_addition_log_obj.id,
                    defaults={
                        "date_modified": datetime.now(),
                        "comments": "Error occured during delivery of sourcedocument",
                        "levering_status": delivery_status,
                        "process_status": "failed_to_deliver_sourcedocuments",
                    },
                )

            else:
                print(
                    f"De levering van de addition van {self.measuringpoint} aan het {self.monitoring_network} is geslaagd"
                )
                (
                    self.gmn_bro_addition_log_obj,
                    created,
                ) = gmn_bro_sync_log.objects.update_or_create(
                    id=self.gmn_bro_addition_log_obj.id,
                    defaults={
                        "date_modified": datetime.now(),
                        "comments": f"Succesfully delivered addition of {self.measuringpoint} to {self.monitoring_network} sourcedocument",
                        "levering_status": "4",
                        "levering_status_info": upload_info.json()["status"],
                        "lastchanged": upload_info.json()["lastChanged"],
                        "levering_id": upload_info.json()["identifier"],
                        "process_status": "succesfully_delivered_sourcedocuments",
                    },
                )
                time.sleep(10)

        except Exception as e:
            delivery_status = str(current_delivery_status + 1)
            print(
                f"De addition van {self.measuringpoint} aan{self.monitoring_network} is niet gelukt. De levering is nu {delivery_status} keer gefaald."
            )

            (
                self.gmn_bro_addition_log_obj,
                created,
            ) = gmn_bro_sync_log.objects.update_or_create(
                id=self.gmn_bro_addition_log_obj.id,
                defaults={
                    "date_modified": datetime.now(),
                    "comments": f"Exception occured during delivery of addition sourcedocument: {e}",
                    "levering_status": delivery_status,
                    "process_status": "failed_to_deliver_sourcedocuments",
                },
            )

    def check_delivery_status_levering(self):
        """
        Function to check and log the status of the delivery
        """
        print(323)
        try:
            delivery_status_info = brx.check_delivery_status(
                self.gmn_bro_addition_log_obj.levering_id,
                self.acces_token_bro_portal,
                demo=self.demo,
            )

            delivery_errors = delivery_status_info.json()["brondocuments"][0]["errors"]

            if (
                delivery_status_info.json()["status"] == "DOORGELEVERD"
                and delivery_status_info.json()["brondocuments"][0]["status"]
                == "OPGENOMEN_LVBRO"
            ):
                (
                    self.gmn_bro_addition_log_obj,
                    created,
                ) = gmn_bro_sync_log.objects.update_or_create(
                    id=self.gmn_bro_addition_log_obj.id,
                    defaults=dict(
                        gmn_bro_id=delivery_status_info.json()["brondocuments"][0][
                            "broId"
                        ],
                        levering_status_info=delivery_status_info.json()[
                            "brondocuments"
                        ][0]["status"],
                        last_changed=delivery_status_info.json()["lastChanged"],
                        comments="Addition request approved",
                        process_status="delivery_approved",
                    ),
                )

                # Set the synced_to_bro of the event that triggered this process to True
                IntermediateEvent.objects.update_or_create(
                    id=self.event.id,
                    defaults=dict(
                        synced_to_bro=True,
                    ),
                )

                # Set measuringpoint.synced_to_bro to True
                MeasuringPoint.objects.update_or_create(
                    id=self.measuringpoint.id,
                    defaults=dict(
                        synced_to_bro=True,
                    ),
                )

                # Remove the sourcedocument file if delivery is approved
                filename = self.gmn_bro_addition_log_obj.file
                filepath = os.path.join(gmn_SETTINGS["additions_dir"], filename)
                os.remove(filepath)

            elif delivery_errors:
                (
                    self.gmn_bro_addition_log_obj,
                    created,
                ) = gmn_bro_sync_log.objects.update_or_create(
                    id=self.gmn_bro_addition_log_obj.id,
                    defaults=dict(
                        last_changed=delivery_status_info.json()["lastChanged"],
                        comments=f"Found errors during the check of {self.monitoring_network}: {delivery_errors}",
                    ),
                )

            else:
                (
                    self.gmn_bro_addition_log_obj,
                    created,
                ) = gmn_bro_sync_log.objects.update_or_create(
                    id=self.gmn_bro_addition_log_obj.id,
                    defaults=dict(
                        levering_status_info=delivery_status_info.json()[
                            "brondocuments"
                        ][0]["status"],
                        last_changed=delivery_status_info.json()["lastChanged"],
                        comments="Addition request not yet approved",
                    ),
                )

        except Exception as e:
            (
                self.gmn_bro_addition_log_obj,
                created,
            ) = gmn_bro_sync_log.objects.update_or_create(
                id=self.gmn_bro_addition_log_obj.id,
                defaults={
                    "comments": f"Error occured during status check of delivery: {e}",
                },
            )


class MeasuringPointRemoval:
    """
    Class to handle the removal of a Measuringpoint from a GMN.
    """

    def __init__(self, event, demo, acces_token_bro_portal):
        self.event = event
        self.demo = demo
        self.acces_token_bro_portal = acces_token_bro_portal
        self.monitoring_network = event.gmn
        self.measuringpoint = event.measuring_point
        self.gmn_bro_removal_log_obj = None

    def handle(self, check_only):
        """
        Main function to handle the removal of a meauringpoint from a GMN.
        The status of the delivery is registered in a GMN_sync_log instance.
        When the removal delivery has successfully been handled, the synced_to_bro of the event is set to True.
        As long as synced_to_bro is False, this function will be triggered, and the delivery process will be picked up, depending on the status found in the log.
        """
        if not check_only:
            # If gmn bro id doesnt exist yet, the network hasnt been registered yet
            if self.monitoring_network.gmn_bro_id is None:
                return

            # Check if measuring point has allready been added to the network
            addition_event = IntermediateEvent.objects.filter(
                gmn=self.monitoring_network,
                measuring_point=self.measuringpoint,
                event_type="GMN_MeasuringPoint",
            ).first()
            if not addition_event or addition_event.synced_to_bro is False:
                return

            # Check for an existing removal log.
            gmn_bro_sync_log_qs = gmn_bro_sync_log.objects.filter(
                gmn_bro_id=self.monitoring_network.gmn_bro_id,
                object_id_accountable_party=self.monitoring_network.object_id_accountable_party,
                event_type="GMN_MeasuringPointEndDate",
                measuringpoint=self.measuringpoint,
            )

            # Create removal xml file if required
            if (
                not gmn_bro_sync_log_qs.exists()
                or gmn_bro_sync_log_qs.first().process_status
                == "failed_to_generate_source_documents"
            ):
                print(
                    f"Geen succesvolle removal gevonden voor {self.event.measuring_point}. Er wordt nu een removal bestand aangemaakt."
                )
                self.create_removal_file()
            else:
                self.gmn_bro_removal_log_obj = gmn_bro_sync_log_qs.first()

            # Validate Removal registration if required
            if self.gmn_bro_removal_log_obj.process_status in [
                "succesfully_generated_removal_request",
                "failed_to_validate_sourcedocument",
            ]:
                print(
                    f"De verwijdering van {self.measuringpoint} aan het {self.monitoring_network} word gevalideerd."
                )

                self.validate_registration()

            # Deliver removal registration if validation succeeded, or previous deliveries failed (to a max of 3)
            if (
                self.gmn_bro_removal_log_obj.process_status
                == "source_document_validation_succesful"
                and self.gmn_bro_removal_log_obj.validation_status == "VALIDE"
            ) or (
                self.gmn_bro_removal_log_obj.process_status
                == "failed_to_deliver_sourcedocuments"
                and self.gmn_bro_removal_log_obj.levering_status in ["1", "2"]
            ):
                print(
                    f"De registratie van de removal van {self.measuringpoint} uit {self.monitoring_network} word aangeleverd."
                )
                self.deliver_registration()

            # If delivery failed 3 times: break the process
            if (
                self.gmn_bro_removal_log_obj.process_status
                == "failed_to_deliver_sourcedocuments"
                and self.gmn_bro_removal_log_obj.levering_status == "3"
            ):
                print(
                    f'De registratie van de removal van {self.measuringpoint} uit {self.monitoring_network} is al 3 keer gefaald. Controleer handmatig wat er fout gaat en reset de leveringstatus handmatig naar "nog niet aangeleverd" om het opnieuw te proberen.'
                )
                return

        # Check the delivery status
        if not self.gmn_bro_removal_log_obj:
            return
        if (
            self.gmn_bro_removal_log_obj.process_status
            == "succesfully_delivered_sourcedocuments"
            and self.gmn_bro_removal_log_obj.levering_status_info != "OPGENOMEN_LVBRO"
            and self.gmn_bro_removal_log_obj.levering_id is not None
        ):
            print(
                f"De status van de removal van {self.measuringpoint} uit het {self.monitoring_network} wordt gecontroleerd."
            )
            self.check_delivery_status_levering()

    def create_removal_file(self):
        """
        Function to create the removal xml file
        """
        try:
            # Set default quality regime IMBRO if value is not filled in in GMN instance
            if self.monitoring_network.quality_regime == None:
                quality_regime = "IMBRO"
            else:
                quality_regime = self.monitoring_network.quality_regime

            # Create source docs
            srcdocdata = {
                "eventDate": [
                    str(self.event.event_date),
                    "date",
                ],
                "measuringPoint": self.measuringpoint.code,
            }

            # Initialize the gmn_registration_request instance
            gmn_removal_request = brx.gmn_registration_request(
                srcdoc="GMN_MeasuringPointEndDate",
                broId=self.monitoring_network.gmn_bro_id,
                requestReference=f"remove {self.measuringpoint} from {self.monitoring_network.name}",
                deliveryAccountableParty=self.monitoring_network.delivery_accountable_party,
                qualityRegime=quality_regime,
                srcdocdata=srcdocdata,
            )

            # Generate the startregistration request
            gmn_removal_request.generate()

            # Write the request
            xml_filename = f"remove {self.monitoring_network.name}.xml"
            gmn_removal_request.write_request(
                output_dir=gmn_SETTINGS["removals_dir"],
                filename=xml_filename,
            )

            # Create a log instance for the request
            (
                self.gmn_bro_removal_log_obj,
                created,
            ) = gmn_bro_sync_log.objects.update_or_create(
                object_id_accountable_party=self.monitoring_network.object_id_accountable_party,
                gmn_bro_id=self.monitoring_network.gmn_bro_id,
                quality_regime=self.monitoring_network.quality_regime,
                measuringpoint=self.measuringpoint,
                event_type="GMN_MeasuringPointEndDate",
                defaults=dict(
                    comments="Succesfully generated removal request",
                    date_modified=datetime.now(),
                    validation_status=None,
                    process_status="succesfully_generated_removal_request",
                    file=xml_filename,
                ),
            )

        except Exception as e:
            (
                self.gmn_bro_removal_log_obj,
                created,
            ) = gmn_bro_sync_log.objects.update_or_create(
                object_id_accountable_party=self.monitoring_network.object_id_accountable_party,
                gmn_bro_id=self.monitoring_network.gmn_bro_id,
                quality_regime=self.monitoring_network.quality_regime,
                event_type="GMN_MeasuringPointEndDate",
                measuringpoint=self.measuringpoint,
                defaults=dict(
                    comments=f"Failed to create removal source document: {e}",
                    date_modified=datetime.now(),
                    process_status="failed_to_generate_source_documents",
                ),
            )

    def validate_registration(self):
        """
        This function validates removal, and registers its process in the log instance.
        """
        try:
            filename = self.gmn_bro_removal_log_obj.file
            filepath = os.path.join(gmn_SETTINGS["removals_dir"], filename)
            payload = open(filepath)

            validation_info = brx.validate_sourcedoc(
                payload, self.acces_token_bro_portal, self.demo
            )

            errors_count = len(validation_info["errors"])

            validation_status = validation_info["status"]

            if errors_count > 0:
                validation_errors = validation_info["errors"]
                comments = f"Found errors during the validation of the removal from {self.monitoring_network}: {validation_errors}"
                process_status = "failed_to_validate_sourcedocument"
            elif validation_status == 500:
                comments = f"BRO server is down. Please try again later"
                process_status = "failed_to_validate_sourcedocument"
            elif validation_status == 400:
                comments = f"Something went wrong while validating. Try again."
                process_status = "failed_to_validate_sourcedocument"
            else:
                comments = f"Succesfully validated sourcedocument for removal from meetnet {self.monitoring_network}."
                process_status = "source_document_validation_succesful"

            print(comments)

            (
                self.gmn_bro_removal_log_obj,
                created,
            ) = gmn_bro_sync_log.objects.update_or_create(
                id=self.gmn_bro_removal_log_obj.id,
                defaults=dict(
                    comments=comments,
                    validation_status=validation_status,
                    process_status=process_status,
                ),
            )

        except Exception as e:
            (
                self.gmn_bro_removal_log_obj,
                created,
            ) = gmn_bro_sync_log.objects.update_or_create(
                id=self.gmn_bro_removal_log_obj.id,
                defaults=dict(
                    comments=f"Exception occured during validation of sourcedocuments: {e}",
                    process_status="failed_to_validate_sourcedocument",
                ),
            )

    def deliver_registration(self):
        """
        Function to actually deliver the removal.
        """
        current_delivery_status = int(self.gmn_bro_removal_log_obj.levering_status)

        try:
            # Prepare and deliver registration
            filename = self.gmn_bro_removal_log_obj.file
            filepath = os.path.join(gmn_SETTINGS["removals_dir"], filename)
            payload = open(filepath)
            request = {filename: payload}

            upload_info = brx.upload_sourcedocs_from_dict(
                request, token=self.acces_token_bro_portal["token"], demo=self.demo
            )

            # Log the result
            if upload_info == "Error":
                delivery_status = str(current_delivery_status + 1)

                print(
                    f"De removan van {self.measuringpoint} uit het {self.monitoring_network} is niet gelukt. De levering is nu {delivery_status} keer gefaald."
                )
                (
                    self.gmn_bro_removal_log_obj,
                    created,
                ) = gmn_bro_sync_log.objects.update_or_create(
                    id=self.gmn_bro_removal_log_obj.id,
                    defaults={
                        "date_modified": datetime.now(),
                        "comments": "Error occured during delivery of sourcedocument",
                        "levering_status": delivery_status,
                        "process_status": "failed_to_deliver_sourcedocuments",
                    },
                )

            else:
                print(
                    f"De levering van de removal van {self.measuringpoint} uit het {self.monitoring_network} is geslaagd"
                )
                (
                    self.gmn_bro_removal_log_obj,
                    created,
                ) = gmn_bro_sync_log.objects.update_or_create(
                    id=self.gmn_bro_removal_log_obj.id,
                    defaults={
                        "date_modified": datetime.now(),
                        "comments": f"Succesfully delivered removal of {self.measuringpoint} from {self.monitoring_network} sourcedocument",
                        "levering_status": "4",
                        "levering_status_info": upload_info.json()["status"],
                        "lastchanged": upload_info.json()["lastChanged"],
                        "levering_id": upload_info.json()["identifier"],
                        "process_status": "succesfully_delivered_sourcedocuments",
                    },
                )
                time.sleep(10)

        except Exception as e:
            delivery_status = str(current_delivery_status + 1)
            print(
                f"De removal van {self.measuringpoint} uit het {self.monitoring_network} is niet gelukt. De levering is nu {delivery_status} keer gefaald."
            )

            (
                self.gmn_bro_removal_log_obj,
                created,
            ) = gmn_bro_sync_log.objects.update_or_create(
                id=self.gmn_bro_removal_log_obj.id,
                defaults={
                    "date_modified": datetime.now(),
                    "comments": f"Exception occured during delivery of removal sourcedocument: {e}",
                    "levering_status": delivery_status,
                    "process_status": "failed_to_deliver_sourcedocuments",
                },
            )

    def check_delivery_status_levering(self):
        """
        Function to check and log the status of the delivery
        """
        try:
            delivery_status_info = brx.check_delivery_status(
                self.gmn_bro_removal_log_obj.levering_id,
                self.acces_token_bro_portal,
                demo=self.demo,
            )

            delivery_errors = delivery_status_info.json()["brondocuments"][0]["errors"]

            if (
                delivery_status_info.json()["status"] == "DOORGELEVERD"
                and delivery_status_info.json()["brondocuments"][0]["status"]
                == "OPGENOMEN_LVBRO"
            ):
                (
                    self.gmn_bro_removal_log_obj,
                    created,
                ) = gmn_bro_sync_log.objects.update_or_create(
                    id=self.gmn_bro_removal_log_obj.id,
                    defaults=dict(
                        gmn_bro_id=delivery_status_info.json()["brondocuments"][0][
                            "broId"
                        ],
                        levering_status_info=delivery_status_info.json()[
                            "brondocuments"
                        ][0]["status"],
                        last_changed=delivery_status_info.json()["lastChanged"],
                        comments="Removal request approved",
                        process_status="delivery_approved",
                    ),
                )

                # Set the synced_to_bro of the event that triggered this process to True
                IntermediateEvent.objects.update_or_create(
                    id=self.event.id,
                    defaults=dict(
                        synced_to_bro=True,
                    ),
                )

                # Set measuringpoint.synced_to_bro to True
                MeasuringPoint.objects.update_or_create(
                    id=self.measuringpoint.id,
                    defaults=dict(removed_from_BRO_gmn=True),
                )

                # Remove the sourcedocument file if delivery is approved
                filename = self.gmn_bro_removal_log_obj.file
                filepath = os.path.join(gmn_SETTINGS["removals_dir"], filename)
                os.remove(filepath)

            elif delivery_errors:
                (
                    self.gmn_bro_removal_log_obj,
                    created,
                ) = gmn_bro_sync_log.objects.update_or_create(
                    id=self.gmn_bro_removal_log_obj.id,
                    defaults=dict(
                        last_changed=delivery_status_info.json()["lastChanged"],
                        comments=f"Found errors during the check of {self.monitoring_network}: {delivery_errors}",
                    ),
                )

            else:
                (
                    self.gmn_bro_removal_log_obj,
                    created,
                ) = gmn_bro_sync_log.objects.update_or_create(
                    id=self.gmn_bro_removal_log_obj.id,
                    defaults=dict(
                        levering_status_info=delivery_status_info.json()[
                            "brondocuments"
                        ][0]["status"],
                        last_changed=delivery_status_info.json()["lastChanged"],
                        comments="Removal request not yet approved",
                    ),
                )

        except Exception as e:
            (
                self.gmn_bro_removal_log_obj,
                created,
            ) = gmn_bro_sync_log.objects.update_or_create(
                id=self.gmn_bro_removal_log_obj.id,
                defaults={
                    "comments": f"Error occured during status check of delivery: {e}",
                },
            )


class ClosureGMN:
    """
    Class to handle the closure of a GMN.
    """

    def __init__(self, event, demo, acces_token_bro_portal):
        self.event = event
        self.demo = demo
        self.acces_token_bro_portal = acces_token_bro_portal
        self.monitoring_network = event.gmn
        self.measuringpoint = event.measuring_point
        self.gmn_bro_closure_log_obj = None

    def handle(self,check_only):
        """
        Main function to handle the Closure of a GMN.
        The status of the delivery is registered in a GMN_sync_log instance.
        When the Closure delivery has successfully been handled, the synced_to_bro of the event is set to True.
        As long as synced_to_bro is False, this function will be triggered, and the delivery process will be picked up, depending on the status found in the log.
        """

        # If gmn bro id doesnt exist yet, the network hasnt been registered yet
        if self.monitoring_network.gmn_bro_id is None:
            return

        # Check for an existing Closure log.
        gmn_bro_sync_log_qs = gmn_bro_sync_log.objects.filter(
            gmn_bro_id=self.monitoring_network.gmn_bro_id,
            object_id_accountable_party=self.monitoring_network.object_id_accountable_party,
            event_type="GMN_Closure",
        )

        if not check_only:
                
            # Create closure xml file if required
            if (
                not gmn_bro_sync_log_qs.exists()
                or gmn_bro_sync_log_qs.first().process_status
                == "failed_to_generate_source_documents"
            ):
                print(
                    f"Geen succesvolle closure gevonden voor {self.monitoring_network}. Er wordt nu een closure bestand aangemaakt."
                )
                self.create_closure_file()
            else:
                self.gmn_bro_closure_log_obj = gmn_bro_sync_log_qs.first()

            # Validate closure if required
            if self.gmn_bro_closure_log_obj.process_status in [
                "succesfully_generated_closure_request",
                "failed_to_validate_sourcedocument",
            ]:
                print(f"{self.monitoring_network} word gevalideerd.")

                self.validate_closure()

            # Deliver closure if validation succeeded, or previous deliveries failed (to a max of 3)
            if (
                self.gmn_bro_closure_log_obj.process_status
                == "source_document_validation_succesful"
                and self.gmn_bro_closure_log_obj.validation_status == "VALIDE"
            ) or (
                self.gmn_bro_closure_log_obj.process_status
                == "failed_to_deliver_sourcedocuments"
                and self.gmn_bro_closure_log_obj.levering_status in ["1", "2"]
            ):
                print(f"De closure van {self.monitoring_network} word aangeleverd.")
                self.deliver_closure()

            # If delivery failed 3 times: break the process
            if (
                self.gmn_bro_closure_log_obj.process_status
                == "failed_to_deliver_sourcedocuments"
                and self.gmn_bro_closure_log_obj.levering_status == "3"
            ):
                print(
                    f'De closure van {self.monitoring_network} is al 3 keer gefaald. Controleer handmatig wat er fout gaat en reset de leveringstatus handmatig naar "nog niet aangeleverd" om het opnieuw te proberen.'
                )
                return

        # Check the delivery status
        if not self.gmn_bro_closure_log_obj:
            return
        if (
            self.gmn_bro_closure_log_obj.process_status
            == "succesfully_delivered_sourcedocuments"
            and self.gmn_bro_closure_log_obj.levering_status_info != "OPGENOMEN_LVBRO"
            and self.gmn_bro_closure_log_obj.levering_id is not None
        ):
            print(
                f"De status van de closure van {self.monitoring_network} wordt gecontroleerd."
            )
            self.check_delivery_status_levering()

    def create_closure_file(self):
        """
        Function to create closure xml file for a closure of a gmn
        """
        try:
            # Set default quality regime IMBRO if value is not filled in in GMN instance
            if self.monitoring_network.quality_regime == None:
                quality_regime = "IMBRO"
            else:
                quality_regime = self.monitoring_network.quality_regime

            # Create source docs
            srcdocdata = {
                "endDateMonitoring": [
                    str(self.event.event_date),
                    "date",
                ],
            }

            # Initialize the gmn_registration_request instance
            gmn_removal_request = brx.gmn_registration_request(
                srcdoc="GMN_Closure",
                broId=self.monitoring_network.gmn_bro_id,
                requestReference=f"close {self.monitoring_network.name}",
                deliveryAccountableParty=self.monitoring_network.delivery_accountable_party,
                qualityRegime=quality_regime,
                srcdocdata=srcdocdata,
            )

            # Generate the startregistration request
            gmn_removal_request.generate()

            # Write the request
            xml_filename = f"closure {self.monitoring_network.name}.xml"
            gmn_removal_request.write_request(
                output_dir=gmn_SETTINGS["closures_dir"],
                filename=xml_filename,
            )

            # Create a log instance for the request
            (
                self.gmn_bro_closure_log_obj,
                created,
            ) = gmn_bro_sync_log.objects.update_or_create(
                object_id_accountable_party=self.monitoring_network.object_id_accountable_party,
                gmn_bro_id=self.monitoring_network.gmn_bro_id,
                quality_regime=self.monitoring_network.quality_regime,
                event_type="GMN_Closure",
                defaults=dict(
                    comments="Succesfully generated closure request",
                    date_modified=datetime.now(),
                    validation_status=None,
                    process_status="succesfully_generated_closure_request",
                    file=xml_filename,
                ),
            )

        except Exception as e:
            (
                self.gmn_bro_closure_log_obj,
                created,
            ) = gmn_bro_sync_log.objects.update_or_create(
                object_id_accountable_party=self.monitoring_network.object_id_accountable_party,
                gmn_bro_id=self.monitoring_network.gmn_bro_id,
                quality_regime=self.monitoring_network.quality_regime,
                event_type="GMN_Closure",
                defaults=dict(
                    comments=f"Failed to create closure source document: {e}",
                    date_modified=datetime.now(),
                    process_status="failed_to_generate_source_documents",
                ),
            )

    def validate_closure(self):
        """
        This function validates closure request files, and registers its process in the log instance.
        """
        try:
            filename = self.gmn_bro_closure_log_obj.file
            filepath = os.path.join(gmn_SETTINGS["closures_dir"], filename)
            payload = open(filepath)

            validation_info = brx.validate_sourcedoc(
                payload, self.acces_token_bro_portal, self.demo
            )

            errors_count = len(validation_info["errors"])

            validation_status = validation_info["status"]

            if errors_count > 0:
                validation_errors = validation_info["errors"]
                comments = f"Found errors during the validation of {self.monitoring_network}: {validation_errors}"
                process_status = "failed_to_validate_sourcedocument"
            elif validation_status == 500:
                comments = f"BRO server is down. Please try again later"
                process_status = "failed_to_validate_sourcedocument"
            elif validation_status == 400:
                comments = f"Something went wrong while validating. Try again."
                process_status = "failed_to_validate_sourcedocument"
            else:
                comments = f"Succesfully validated sourcedocument for meetnet {self.monitoring_network}."
                process_status = "source_document_validation_succesful"

            print(comments)

            (
                self.gmn_bro_closure_log_obj,
                created,
            ) = gmn_bro_sync_log.objects.update_or_create(
                id=self.gmn_bro_closure_log_obj.id,
                defaults=dict(
                    comments=comments,
                    validation_status=validation_status,
                    process_status=process_status,
                ),
            )

        except Exception as e:
            (
                self.gmn_bro_closure_log_obj,
                created,
            ) = gmn_bro_sync_log.objects.update_or_create(
                id=self.gmn_bro_closure_log_obj.id,
                defaults=dict(
                    comments=f"Exception occured during validation of sourcedocuments: {e}",
                    process_status="failed_to_validate_sourcedocument",
                ),
            )

    def deliver_closure(self):
        """
        Function to actually deliver the closure.
        """
        current_delivery_status = int(self.gmn_bro_closure_log_obj.levering_status)

        try:
            # Prepare and deliver registration
            filename = self.gmn_bro_closure_log_obj.file
            filepath = os.path.join(gmn_SETTINGS["closures_dir"], filename)
            payload = open(filepath)
            request = {filename: payload}

            upload_info = brx.upload_sourcedocs_from_dict(
                request, token=self.acces_token_bro_portal["token"], demo=self.demo
            )

            # Log the result
            if upload_info == "Error":
                delivery_status = str(current_delivery_status + 1)

                print(
                    f"De closure van {self.monitoring_network} is niet gelukt. De closure is nu {delivery_status} keer gefaald."
                )
                (
                    self.gmn_bro_closure_log_obj,
                    created,
                ) = gmn_bro_sync_log.objects.update_or_create(
                    id=self.gmn_bro_closure_log_obj.id,
                    defaults={
                        "date_modified": datetime.now(),
                        "comments": "Error occured during delivery of sourcedocument",
                        "levering_status": delivery_status,
                        "process_status": "failed_to_deliver_sourcedocuments",
                    },
                )

            else:
                print(f"De closure van {self.monitoring_network} is geslaagd")
                (
                    self.gmn_bro_closure_log_obj,
                    created,
                ) = gmn_bro_sync_log.objects.update_or_create(
                    id=self.gmn_bro_closure_log_obj.id,
                    defaults={
                        "date_modified": datetime.now(),
                        "comments": "Succesfully delivered closure sourcedocument",
                        "levering_status": "4",
                        "levering_status_info": upload_info.json()["status"],
                        "lastchanged": upload_info.json()["lastChanged"],
                        "levering_id": upload_info.json()["identifier"],
                        "process_status": "succesfully_delivered_sourcedocuments",
                    },
                )
                time.sleep(10)

        except Exception as e:
            delivery_status = str(current_delivery_status + 1)
            print(
                f"De closure van {self.monitoring_network} is niet gelukt. De closure is nu {delivery_status} keer gefaald."
            )

            (
                self.gmn_bro_closure_log_obj,
                created,
            ) = gmn_bro_sync_log.objects.update_or_create(
                id=self.gmn_bro_closure_log_obj.id,
                defaults={
                    "date_modified": datetime.now(),
                    "comments": f"Exception occured during delivery of closure sourcedocument: {e}",
                    "levering_status": delivery_status,
                    "process_status": "failed_to_deliver_sourcedocuments",
                },
            )

    def check_delivery_status_levering(self):
        """
        Function to check and log the status of the delivery
        """
        try:
            delivery_status_info = brx.check_delivery_status(
                self.gmn_bro_closure_log_obj.levering_id,
                self.acces_token_bro_portal,
                demo=self.demo,
            )

            delivery_errors = delivery_status_info.json()["brondocuments"][0]["errors"]

            if (
                delivery_status_info.json()["status"] == "DOORGELEVERD"
                and delivery_status_info.json()["brondocuments"][0]["status"]
                == "OPGENOMEN_LVBRO"
            ):
                (
                    self.gmn_bro_closure_log_obj,
                    created,
                ) = gmn_bro_sync_log.objects.update_or_create(
                    id=self.gmn_bro_closure_log_obj.id,
                    defaults=dict(
                        gmn_bro_id=delivery_status_info.json()["brondocuments"][0][
                            "broId"
                        ],
                        levering_status_info=delivery_status_info.json()[
                            "brondocuments"
                        ][0]["status"],
                        last_changed=delivery_status_info.json()["lastChanged"],
                        comments="Startregistration request approved",
                        process_status="delivery_approved",
                    ),
                )

                # Set removed_from_BRO to True on GMN
                GroundwaterMonitoringNet.objects.update_or_create(
                    object_id_accountable_party=self.monitoring_network.object_id_accountable_party,
                    defaults=dict(removed_from_BRO=True),
                )

                # Set the synced_to_bro of the event that triggered this process tot True
                IntermediateEvent.objects.update_or_create(
                    id=self.event.id,
                    defaults=dict(
                        synced_to_bro=True,
                    ),
                )

                # Remove the sourcedocument file if delivery is approved
                filename = self.gmn_bro_closure_log_obj.file
                filepath = os.path.join(gmn_SETTINGS["closures_dir"], filename)
                os.remove(filepath)

            elif delivery_errors:
                (
                    self.gmn_bro_closure_log_obj,
                    created,
                ) = gmn_bro_sync_log.objects.update_or_create(
                    id=self.gmn_bro_closure_log_obj.id,
                    defaults=dict(
                        last_changed=delivery_status_info.json()["lastChanged"],
                        comments=f"Found errors during the check of {self.monitoring_network}: {delivery_errors}",
                    ),
                )

            else:
                (
                    self.gmn_bro_closure_log_obj,
                    created,
                ) = gmn_bro_sync_log.objects.update_or_create(
                    id=self.gmn_bro_closure_log_obj.id,
                    defaults=dict(
                        levering_status_info=delivery_status_info.json()[
                            "brondocuments"
                        ][0]["status"],
                        last_changed=delivery_status_info.json()["lastChanged"],
                        comments="Startregistration request not yet approved",
                    ),
                )

        except Exception as e:
            (
                self.gmn_bro_closure_log_obj,
                created,
            ) = gmn_bro_sync_log.objects.update_or_create(
                id=self.gmn_bro_closure_log_obj.id,
                defaults={
                    "comments": f"Error occured during status check of delivery: {e}",
                },
            )
