import os

from django.core.management.base import BaseCommand
from bro_exchange.broxml.frd.requests import FrdStartregistrationTool
from bro_exchange.bhp.connector import validate_sourcedoc
from frd.models import FormationResistanceDossier, FrdSyncLog
from datetime import datetime
from main.settings.base import FRD_SETTINGS

#############
## Command ##
#############

class Command(BaseCommand):
    """
    Handles the sync between the bro-connector and the BRO.
    Runs daily as cronjob.
    """
    help = "Syncs the FRD data to the BRO"

    def handle(self, *args, **kwargs):
        self.handle_startregistrations()
        self.handle_measurements()

    def handle_startregistrations(self):
        """
        Handles the startregistrations for all FRD's without bro_id.
        For each new FRD, the FrdStartregistration class is used to hande the registration
        """
        new_dossiers_qs = self.get_new_dossiers()

        if len(new_dossiers_qs) != 0:
            for new_dossier in new_dossiers_qs:
                startregistration = FrdStartregistration(new_dossier)
                startregistration.sync()

    def get_new_dossiers(self):
        return FormationResistanceDossier.objects.filter(frd_bro_id=None)
    
    def handle_measurements(self):
        """
        Develop when startregistrations are done
        """
        pass


##############################
## General helper functions ##
##############################

def update_log_obj(log_obj, field_value_dict):
    """
    Updates the date modified field to now, and changes the values found in the dict
    """
    now = datetime.now()
    log_obj.date_modified = now
    
    for key, value in field_value_dict.items():
        setattr(log_obj, key, value)
    
    log_obj.save()


#############
## Classes ##
#############

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
            None:self.generate_xml_file,
            "failed_to_generate_startregistration_xml":self.generate_xml_file,
            "succesfully_generated_startregistration_xml":self.validate_xml_file,
            "source_document_validation_succesful":self.deliver_xml_file,
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
            update_log_obj(
                self.frd_startregistration_log,
                {"process_status": "succesfully_generated_startregistration_xml",
                "comment":"Succesfully generated startregistration request",
                "xml_filepath":self.filepath,
                },
            )

        except Exception as e:
            update_log_obj(
                self.frd_startregistration_log,
                {"process_status": "failed_to_generate_startregistration_xml",
                    "comment":f"Error message: {e}"},
            )
        
        else:
            self.validate_xml_file()

    def validate_xml_file(self):
        """
        Validates the xml file, using the BRO validations service. 
        If the xml file is VALIDE, the deliver_xml_file method is called
        """
        filepath = self.frd_startregistration_log.xml_filepath
        xml_payload = open(filepath)

        try:
            validation_info = validate_sourcedoc(
                payload = xml_payload,
                bro_info = self.bro_info,
                demo = self.demo,
                api = self.api_version,
            )

        except Exception as e:
            update_log_obj(
                self.frd_startregistration_log,
                {"process_status": "failed_to_validate_sourcedocument",
                    "comment":f"Error message: {e}"},
            )

        else:
            validation_status = validation_info["status"]
            validation_errors = validation_info["errors"]
            
            if validation_status == "VALIDE":
                update_log_obj(
                    self.frd_startregistration_log,
                    {"process_status": "source_document_validation_succesful",
                        "comment":"Succesfully validated sourcedocument"},
                )

                self.deliver_xml_file()

            else:
                update_log_obj(
                    self.frd_startregistration_log,
                    {"process_status": "failed_to_validate_sourcedocument",
                        "comment":f"Validation Status: {validation_status}, errors: {validation_errors}"},
                )

    def deliver_xml_file(self):
        print('u heeft post!!')

    def construct_xml_tree(self):
        """
        Setup the data for the startregistration xml file.
        Then creates the file and saves it in the assigned folder.
        """
        # prepare data
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
        filename = f"startregistration_{self.frd_obj.object_id_accountable_party}.xml"
        self.filepath = os.path.join(self.output_dir, filename)
        self.startregistration_xml_file.write(
            self.filepath, pretty_print=True
        )
