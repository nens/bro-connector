from django.core.management.base import BaseCommand
from main.settings.base import GMN_AANLEVERING_SETTINGS
from gmn_aanlevering.models import IntermediateEvent
from main.management.commands.tasks.gmn_tasks.gmn_requests import *

class Command(BaseCommand):
    """
    This command handles all 4 type of registrations for GMN's
    It uses the IntermediateEvents table as input.
    In this table, the event_type column holds the information for which BRO request to handle.
    The synced_to_bro column is the administration for whether the information is allready sent to the BRO.
    
    The 4 requests that are handled are:
        - GMN_StartRegistration
        - GMN_MeasuringPoint
        - GMN_MeasuringPointEndDate
        - GMN_Closure
    """

    def handle(self, *args, **options):
        
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

        ### LOOP OVER UNSYNCED EVENTS AND HANDLE REQUESTS ###
        events = IntermediateEvent.objects.filter(synced_to_bro=False)

        for event in events:
            if event.event_type == 'GMN_StartRegistration':
                handle_gmn_registration()

            if event.event_type == 'GMN_MeasuringPoint':
                handle_add_measuringpoint()

            if event.event_type == 'GMN_MeasuringPointEndDate':
                handle_remove_measuringpoint()

            if event.event_type == 'GMN_Closure':
                handle_gmn_closure()
