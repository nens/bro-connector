from django.core.management.base import BaseCommand
import bro_exchange as brx
from frd.models import FormationResistanceDossier


class Command(BaseCommand):
    """
    Handles the sync between the bro-connector and the BRO.
    Runs daily as cronjob.
    """
    help = 'Syncs the FRD data to the BRO'

    def handle(self, *args, **kwargs):
        sync = FrdSync()
        sync.run()


class FrdSync:
    """
    Syncs all data from the BRO-Connector to the BRO.
    Loops over the FRDs in the database to check if startregistrations are required,
    And checks for new measurement values.
    If new data is found, the BRO-Exchange tool is used to create, validate, and send the XML files.
    """

    def run(self):
        # Handle startregistrations
        new_dossiers_qs = self.lookup_new_dossiers()
        if len(new_dossiers_qs) != 0:
            for new_dossier in new_dossiers_qs:
                startregistration = FrdStartregistration(new_dossier)
                startregistration.handle()

        # Handle measurements

    def lookup_new_dossiers(self):
        return FormationResistanceDossier.objects.filter(frd_bro_id=None)
    
        
class FrdStartregistration:
    """
    Handles the startregistration of a new FRD in the system,
    based on the qs obj_id.
    """
    def __init__(self, frd_obj):
        self.frd_obj = frd_obj

    def handle(self):
        print('Handle startregistration here')


