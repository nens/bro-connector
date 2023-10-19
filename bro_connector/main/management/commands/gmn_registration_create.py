from django.core.management.base import BaseCommand
from main.settings.base import GMN_AANLEVERING_SETTINGS

import bro_exchange as brx

class Command(BaseCommand):
    """
    Command to registrate a GMW command
    """

    def handle(self, *args, **options):
        demo = GMN_AANLEVERING_SETTINGS["demo"]

        if demo:
            acces_token_bro_portal = GMN_AANLEVERING_SETTINGS[
                "acces_token_bro_portal_demo"
            ]
        else:
            acces_token_bro_portal = GMN_AANLEVERING_SETTINGS[
                "acces_token_bro_portal_bro_connector"
            ]
        startregistrations_dir = GMN_AANLEVERING_SETTINGS["registrations_dir"]

        self.gmn_start_registration(
            acces_token_bro_portal, startregistrations_dir, demo
        )
    
    def gmn_start_registration(
        self, acces_token_bro_portal, startregistrations_dir, demo
    ):
        print('hi')