from django.core.management.base import BaseCommand
from main.settings.base import GMN_AANLEVERING_SETTINGS
from gmn_aanlevering.models import IntermediateEvent
from main.management.commands.tasks.gmn_tasks.gmn_request_handlers import (
    StartRegistrationGMN, MeasuringPointAddition, MeasuringPointRemoval, ClosureGMN
)


class Command(BaseCommand):
    """
    This command handles all 4 type of registrations for GMN's
    It uses the IntermediateEvents table as input.
    In this table, the event_type column holds the information for which BRO request to handle.
    The synced_to_bro column is the administration for whether the information is allready sent to the BRO.
    The deliver_to_bro in the event determines whether a event should be synced.
    
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
        events = IntermediateEvent.objects.filter(synced_to_bro=False, deliver_to_bro=True)

        for event in events:
            if event.event_type == 'GMN_StartRegistration':
                print(f"De startregistratie van {event.gmn} wordt geinitialiseerd of opgepakt")
                registration = StartRegistrationGMN(event, demo, acces_token_bro_portal)
                registration.handle()

            if event.event_type == 'GMN_MeasuringPoint':
                print(f"De toevoeging van {event.measuring_point} aan het {event.gmn} wordt geinitialiseerd of opgepakt")
                addition = MeasuringPointAddition(event, demo, acces_token_bro_portal)
                addition.handle()

            if event.event_type == 'GMN_MeasuringPointEndDate':
                print(f"De verwijdering van {event.measuring_point} aan het {event.gmn} wordt geinitialiseerd of opgepakt")
                MeasuringPointRemoval(event, demo, acces_token_bro_portal)

            if event.event_type == 'GMN_Closure':
                print(f"De eindregistratie van {event.gmn} wordt geinitialiseerd of opgepakt")
                ClosureGMN(event, demo, acces_token_bro_portal)
