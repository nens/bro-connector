import os

from django.core.management.base import BaseCommand
from bro_exchange.broxml.frd.requests import FrdStartregistrationTool
from frd.models import FormationResistanceDossier, FrdSyncLog
from datetime import datetime


class Command(BaseCommand):
    """
    Handles the sync between the bro-connector and the BRO.
    Runs daily as cronjob.
    """

    help = "Syncs the FRD data to the BRO"

    def handle(self, *args, **kwargs):
        sync = FrdSync()
        sync.run()


def update_log_obj(log_obj, field_value_dict):
    """
    Updates the date modified field to now, and changes the values found in the dict
    """
    now = datetime.now()
    log_obj.date_modified = now
    
    for key, value in field_value_dict.items():
        setattr(log_obj, key, value)
    
    log_obj.save()

    
class FrdSync:
    """
    Syncs all data from the BRO-Connector to the BRO.
    Loops over the FRDs in the database to check if startregistrations are required,
    And checks for new measurement values.
    If new data is found, the BRO-Exchange tool is used to create, validate, and send the XML files.
    """

    def run(self):
        """
        Handle startregistrations
        """
        new_dossiers_qs = self.get_new_dossiers()
        if len(new_dossiers_qs) != 0:
            for new_dossier in new_dossiers_qs:
                startregistration = FrdStartregistration(new_dossier)
                startregistration.sync()



    def get_new_dossiers(self):
        return FormationResistanceDossier.objects.filter(frd_bro_id=None)


class FrdStartregistration:
    """
    Handles the startregistration of a new FRD in the system,
    based on the qs obj_id.
    """

    def __init__(self, frd_obj):
        self.output_dir = r"frd/xml_files/"
        self.frd_obj = frd_obj
        self.startregistration_xml_file = None
        self.frd_startregistration_log = None

    def sync(self):
        self.frd_startregistration_log, created = FrdSyncLog.objects.update_or_create(
            event_type="FRD_StartRegistration", frd=self.frd_obj
        )

        if self.frd_startregistration_log.process_status in [
            None,
            "failed_to_generate_startregistration_xml",
        ]:
            try:
                self.test()
                self.generate_startregistration_xml()
                self.save_xml_file()
                update_log_obj(
                    self.frd_startregistration_log,
                    {"process_status": "succesfully_generated_startregistration_xml"},
                )

            except Exception as e:
                update_log_obj(
                    self.frd_startregistration_log,
                    {"process_status": "failed_to_generate_startregistration_xml",
                     "comment":f"Error message: {e}"},
                )

    def generate_startregistration_xml(self):
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
        self.startregistration_xml_file.write(
            os.path.join(self.output_dir, filename), pretty_print=True
        )
