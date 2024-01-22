import os
import time

from django.core.management.base import BaseCommand
from bro_exchange.broxml.frd.requests import FrdStartregistrationTool, ConfigurationRegistrationTool
from bro_exchange.bhp.connector import (
    validate_sourcedoc,
    upload_sourcedocs_from_dict,
    check_delivery_status,
)
from frd.models import FormationResistanceDossier, FrdSyncLog, MeasurementConfiguration
from datetime import datetime
from main.settings.base import FRD_SETTINGS

def get_xml_payload(xml_filepath):
    """
    Creates a payload of the xml file, based on the filepath
    """
    filepath = xml_filepath
    with open(filepath) as file:
        xml_payload = file.read()

    return xml_payload

class Command(BaseCommand):
    """
    Handles the sync between the bro-connector and the BRO.
    Runs daily as cronjob.
    """

    help = "Syncs the FRD data to the BRO"

    def handle(self, *args, **kwargs):
        self.handle_startregistrations()
        self.handle_configurations()
        self.handle_measurements()

    def handle_startregistrations(self):
        """
        Handles the startregistrations for all FRD's without bro_id.
        For each unsynced FRD, the FrdStartregistration class is used to handle the registration
        """
        unsynced_startregistration_dossiers = self.get_unsynced_dossiers()

        for dossier in unsynced_startregistration_dossiers:
            startregistration = FrdStartregistration(dossier)
            startregistration.sync()
    
    def handle_configurations(self):
        """
        Handles the measurement configurations for all configurations without bro_id.
        For each new FRD, the FrdStartregistration class is used to hande the registration
        """
        unsynced_configurations = self.get_unsynced_configurations()

        for measurement_configuration in unsynced_configurations:
            configuration_registration = ConfigurationRegistration(measurement_configuration)
            configuration_registration.sync()

    def handle_measurements(self):
        """
        Develop when startregistrations and configurations are done
        """
        pass

    def get_unsynced_dossiers(self):
        return FormationResistanceDossier.objects.filter(frd_bro_id=None)
    
    def get_unsynced_configurations(self):
        return MeasurementConfiguration.objects.filter(bro_id=None)


class FrdStartregistration:
    """
    Handles the startregistration of a new FRD in the BRO-Connector.
    The sync method is the main function which should always be called
    """

    def __init__(self, frd_obj):
        self.output_dir = "frd/xml_files/"
        self.frd_obj = frd_obj
        self.startregistration_xml_file = None
        self.frd_startregistration_log = None
        self.demo = FRD_SETTINGS["demo"]
        self.api_version = FRD_SETTINGS["api_version"]

        if self.demo:
            self.bro_info = FRD_SETTINGS["bro_info_demo"]
        else:
            self.bro_info = FRD_SETTINGS["bro_info_bro_connector"]

    def sync(self):
        """
        Checks if a log on the Dossier allready exists.
        If not, creates one and handles the complete startregistrations.
        If so, checks the status, and picks up the startregistration process where it was left.
        """
        self.frd_startregistration_log, created = FrdSyncLog.objects.update_or_create(
            event_type="FRD_StartRegistration", frd=self.frd_obj
        )

        status_function_mapping = {
            None: self.generate_xml_file,
            "failed_to_generate_startregistration_xml": self.generate_xml_file,
            "failed_to_validate_sourcedocument": self.validate_xml_file,
            "succesfully_generated_startregistration_xml": self.validate_xml_file,
            "failed_to_deliver_sourcedocuments": self.deliver_xml_file,
            "source_document_validation_succesful": self.deliver_xml_file,
            "succesfully_delivered_sourcedocuments": self.check_delivery,
        }

        current_status = self.frd_startregistration_log.process_status
        method_to_call = status_function_mapping.get(current_status)

        method_to_call()

    def generate_xml_file(self):
        """
        Handles the generation of the startregistration xlm file.
        If it is succesfull, it calls the validate_startregistration_xml to continue the startregistration process.
        """
        try:
            self.construct_xml_tree()
            self.save_xml_file()

        except Exception as e:
            self.frd_startregistration_log.process_status = "failed_to_generate_startregistration_xml"
            self.frd_startregistration_log.comment = f"Error message: {e}",
            self.frd_startregistration_log.save()

        else:
            self.frd_startregistration_log.process_status = "succesfully_generated_startregistration_xml"
            self.frd_startregistration_log.comment = "Succesfully generated startregistration request"
            self.frd_startregistration_log.xml_filepath = self.filepath
            self.frd_startregistration_log.save()

            self.validate_xml_file()

    def validate_xml_file(self):
        """
        Validates the xml file, using the BRO validations service.
        If the xml file is VALIDE, the deliver_xml_file method is called
        """
        xml_payload = get_xml_payload(self.frd_startregistration_log.xml_filepath)

        try:
            validation_info = validate_sourcedoc(
                payload=xml_payload,
                bro_info=self.bro_info,
                demo=self.demo,
                api=self.api_version,
            )

        except Exception as e:
            self.frd_startregistration_log.process_status = "failed_to_validate_sourcedocument"
            self.frd_startregistration_log.comment = f"Error message: {e}"
            self.frd_startregistration_log.save()

        else:
            validation_status = validation_info["status"]
            validation_errors = validation_info["errors"]

            if validation_status == "VALIDE":
                self.frd_startregistration_log.process_status = "source_document_validation_succesful"
                self.frd_startregistration_log.comment = "Succesfully validated sourcedocument"
                self.frd_startregistration_log.save()

                self.deliver_xml_file()

            else:
                self.frd_startregistration_log.process_status = "failed_to_validate_sourcedocument"
                self.frd_startregistration_log.comment = f"Validation Status: {validation_status}, errors: {validation_errors}"
                self.frd_startregistration_log.save()


    def deliver_xml_file(self):
        """
        Delivers the xml file after it has succesfully been validated.
        If the delivery status is OK, the check_delivery method is called to check for further details.
        """

        delivery_status = self.frd_startregistration_log.delivery_status

        if delivery_status == 3:
            self.frd_startregistration_log.process_status = "The delivery of the xml file has failed 3 times. Please check manually what's going on, and reset the delivery status on 'Nog niet aangeleverd"
            self.frd_startregistration_log.save()
            return

        xml_payload = self.get_xml_payload()
        xml_filename = self.frd_startregistration_log.xml_filepath.rsplit("/", 1)[-1]
        request_dict = {xml_filename: xml_payload}

        try:
            upload_info = upload_sourcedocs_from_dict(
                reqs=request_dict,
                token=self.bro_info["token"],
                demo=self.demo,
                api=self.api_version,
            )

        except Exception as e:
            delivery_status += 1
            self.frd_startregistration_log.process_status = "failed_to_deliver_sourcedocuments"
            self.frd_startregistration_log.comment = f"Error message: {e}"
            self.frd_startregistration_log.delivery_status = delivery_status
            self.frd_startregistration_log.save()

        else:
            if upload_info == "Error":
                delivery_status += 1
                self.frd_startregistration_log.process_status = "failed_to_deliver_sourcedocuments"
                self.frd_startregistration_log.comment = f"Error message: {upload_info}"
                self.frd_startregistration_log.delivery_status = delivery_status
                self.frd_startregistration_log.save()

            else:
                self.frd_startregistration_log.process_status = "succesfully_delivered_sourcedocuments"
                self.frd_startregistration_log.comment = "Succesfully delivered startregistration xml file"
                self.frd_startregistration_log.delivery_status = 4
                self.frd_startregistration_log.delivery_status_info = upload_info.json()["status"]
                self.frd_startregistration_log.delivery_id = upload_info.json()["identifier"]
                self.frd_startregistration_log.save()

                time.sleep(10)

                self.check_delivery()

    def check_delivery(self):
        """
        Checks the delivery status based on the delivery id.
        Updates the log of the frd, based on the return of the BRO webservice.
        If the delivery is fully succesfull, the finish_startregistration method is called.
        """

        try:
            delivery_status_info = check_delivery_status(
                identifier=self.frd_startregistration_log.delivery_id,
                token=self.bro_info["token"],
                demo=self.demo,
                api=self.api_version,
            )
        except Exception as e:
            self.frd_startregistration_log.comment = f"Error occured during status check of delivery: {e}"
            self.frd_startregistration_log.save()
        else:
            delivery_status = delivery_status_info.json()["status"]
            delivery_brondocument_status = delivery_status_info.json()["brondocuments"][
                0
            ]["status"]
            delivery_errors = delivery_status_info.json()["brondocuments"][0]["errors"]

            if (
                delivery_status == "DOORGELEVERD"
                and delivery_brondocument_status == "OPGENOMEN_LVBRO"
            ):
                self.finish_startregistration(delivery_status_info)

            elif delivery_errors:
                self.frd_startregistration_log.comment = f"Found errors during the delivery check: {delivery_errors}"
                self.frd_startregistration_log.save()

            else:
                self.frd_startregistration_log.delivery_status_info = delivery_status_info.json()[
                            "brondocuments"
                        ][0]["status"]
                self.frd_startregistration_log.comment = "Startregistration request not yet approved"
                self.frd_startregistration_log.save()

    def construct_xml_tree(self):
        """
        Setup the data for the startregistration xml file.
        Then creates the file and saves the xml tree to self.
        """
        quality_regime = self.frd_obj.quality_regime or "IMBRO"
        gmn_bro_id = getattr(self.frd_obj.gmn, "gmn_bro_id", None)
        gmw_bro_id = getattr(
            getattr(self.frd_obj.gmw_tube, "groundwater_monitoring_well", None),
            "bro_id",
            None,
        )
        gmw_tube_number = str(getattr(self.frd_obj.gmw_tube, "tube_number", None))

        srcdocdata = {
            "request_reference": f"startregistration_{self.frd_obj.object_id_accountable_party}",
            "delivery_accountable_party": self.frd_obj.delivery_accountable_party,
            "object_id_accountable_party": self.frd_obj.object_id_accountable_party,
            "quality_regime": quality_regime,
            "gmn_bro_id": gmn_bro_id,
            "gmw_bro_id": gmw_bro_id,
            "gmw_tube_number": gmw_tube_number,
        }

        startregistration_tool = FrdStartregistrationTool(srcdocdata)
        self.startregistration_xml_file = startregistration_tool.generate_xml_file()

    def save_xml_file(self):
        """
        Saves the xmltree as xml file in the filepath as defined in self.
        """
        filename = f"startregistration_{self.frd_obj.object_id_accountable_party}.xml"
        self.filepath = os.path.join(self.output_dir, filename)
        self.startregistration_xml_file.write(self.filepath, pretty_print=True)

    def get_xml_payload(self):
        """
        Creates a payload of the xml file, based on the filepath
        """
        filepath = self.frd_startregistration_log.xml_filepath
        with open(filepath) as file:
            xml_payload = file.read()

        return xml_payload

    def finish_startregistration(self, delivery_status_info):
        """
        Updates the log, saves the bro_id to the frd, and removes the xml file.
        """
        self.frd_startregistration_log.gmn_bro_id = delivery_status_info.json()["brondocuments"][0]["broId"]
        self.frd_startregistration_log.delivery_status_info = delivery_status_info.json()["brondocuments"][0][
                    "status"
                ]
        self.frd_startregistration_log.comments = "Startregistration request approved"
        self.frd_startregistration_log.process_status = "delivery_approved"
        self.frd_startregistration_log.bro_id = delivery_status_info.json()["brondocuments"][0]["broId"]
        self.frd_startregistration_log.synced = True
        self.frd_startregistration_log.save()
        
        self.save_bro_id(delivery_status_info)
        self.remove_xml_file()

    def save_bro_id(self, delivery_status_info):
        """
        Save the Bro_Id to the FRD object
        """
        self.frd_obj.frd_bro_id = delivery_status_info.json()["brondocuments"][0][
            "broId"
        ]
        self.frd_obj.save()

    def remove_xml_file(self):
        """
        Removes the succesfully delivered xml file.
        """
        os.remove(self.frd_startregistration_log.xml_filepath)

class ConfigurationRegistration:
    """
    Handles the sync of of a new measurement configuration in the BRO-Connector.
    The sync method is the main function which should always be called
    """

    def __init__(self, measurement_configuration):
        self.output_dir = "frd/xml_files/"
        self.measurement_configuration = measurement_configuration
        self.xml_file = None
        self.registration_log = None
        self.demo = FRD_SETTINGS["demo"]
        self.api_version = FRD_SETTINGS["api_version"]

        if self.demo:
            self.bro_info = FRD_SETTINGS["bro_info_demo"]
        else:
            self.bro_info = FRD_SETTINGS["bro_info_bro_connector"]

    def sync(self):
        """
        Checks if a log on the configuratino allready exists.
        If not, creates one and handles the complete registration.
        If so, checks the status, and picks up the registration process where it was left.
        """
        self.registration_log, created = FrdSyncLog.objects.update_or_create(
            event_type="FRD_GEM_MeasurementConfiguration", configuration=self.measurement_configuration
        )

        status_function_mapping = {
            None: self.generate_xml_file,
            "failed_to_generate_xml": self.generate_xml_file,
            "failed_to_validate_sourcedocument": self.validate_xml_file,
            "succesfully_generated_xml": self.validate_xml_file,
            "failed_to_deliver_sourcedocuments": self.deliver_xml_file,
            "source_document_validation_succesful": self.deliver_xml_file,
            # "succesfully_delivered_sourcedocuments": self.check_delivery,
        }

        current_status = self.registration_log.process_status
        method_to_call = status_function_mapping.get(current_status)

        method_to_call()

    def generate_xml_file(self):
        """
        Handles the generation of the startregistration xlm file.
        If it is succesfull, it calls the validate_startregistration_xml to continue the startregistration process.
        """
        try:
            self.construct_xml_tree()
            self.save_xml_file()

        except Exception as e:
            self.registration_log.process_status = "failed_to_generate_xml"
            self.registration_log.comment = f"Error message: {e}",
            self.registration_log.save()

        else:
            self.registration_log.process_status = "succesfully_generated_xml"
            self.registration_log.comment = "Succesfully generated request"
            self.registration_log.xml_filepath = self.filepath
            self.registration_log.save()

            self.validate_xml_file()

    def validate_xml_file(self):
        """
        Validates the xml file, using the BRO validations service.
        If the xml file is VALIDE, the deliver_xml_file method is called
        """
        xml_payload = get_xml_payload(self.registration_log.xml_filepath)

        try:
            validation_info = validate_sourcedoc(
                payload=xml_payload,
                bro_info=self.bro_info,
                demo=self.demo,
                api=self.api_version,
            )

        except Exception as e:
            self.registration_log.process_status = "failed_to_validate_sourcedocument"
            self.registration_log.comment = f"Error message: {e}"
            self.registration_log.save()

        else:
            validation_status = validation_info["status"]
            validation_errors = validation_info["errors"]

            if validation_status == "VALIDE":
                self.registration_log.process_status = "source_document_validation_succesful"
                self.registration_log.comment = "Succesfully validated sourcedocument"
                self.registration_log.save()

                self.deliver_xml_file()

            else:
                self.registration_log.process_status = "failed_to_validate_sourcedocument"
                self.registration_log.comment = f"Validation Status: {validation_status}, errors: {validation_errors}"
                self.registration_log.save()

    def deliver_xml_file(self):
        pass

    def construct_xml_tree(self):
        """
        Setup the data for the xml file.
        Then creates the file and saves the xml tree to self.
        """     

        srcdocdata = {
            "request_reference": f"registration_{self.measurement_configuration.configuration_name}",
            "measurement_configuration_id": self.measurement_configuration.configuration_name,
            "measurement_pair":self.measurement_configuration.measurement_pair,
            "flowcurrent_pair":self.measurement_configuration.flowcurrent_pair,
        }

        configuration_registration_tool = ConfigurationRegistrationTool(srcdocdata)
        self.startregistration_xml_file = configuration_registration_tool.generate_xml_file()

    def save_xml_file(self):
        """
        Saves the xmltree as xml file in the filepath as defined in self.
        """
        filename = f"registration_{self.measurement_configuration.configuration_name}.xml"
        self.filepath = os.path.join(self.output_dir, filename)
        self.startregistration_xml_file.write(self.filepath, pretty_print=True)


