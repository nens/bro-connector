from django.core.management.base import BaseCommand
from ..tasks import sync_gmw_events
from main.settings.base import gmw_SETTINGS


class Command(BaseCommand):
    help = (
        """Command to automatically register all new events and send them to the BRO."""
    )

    def handle(self, *args, **options):
        # Initialize settings
        demo = gmw_SETTINGS["demo"]
        if demo:
            bro_info = gmw_SETTINGS["bro_info_demo"]
        else:
            bro_info = gmw_SETTINGS["bro_info_bro_connector"]

        registrations_dir = gmw_SETTINGS["registrations_dir"]

        # Check the database for new wells/tubes and start a gmw registration for these objects if its it needed
        sync_gmw_events.gmw_create_sourcedocs_wells(
            registrations_dir,
        )

        # Check existing registrations
        sync_gmw_events.gmw_check_existing_registrations(
            bro_info, registrations_dir, demo
        )
