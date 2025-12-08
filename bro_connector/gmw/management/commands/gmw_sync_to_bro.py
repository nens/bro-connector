from django.core.management.base import BaseCommand
from gmw.management.tasks import sync_gmw_events


class Command(BaseCommand):
    help = (
        """Command to automatically register all new events and send them to the BRO."""
    )

    def handle(self, *args, **options):
        # Check the database for new wells/tubes and start a gmw registration for these objects if its it needed
        sync_gmw_events.gmw_create_sourcedocs_wells()

        # Check existing registrations
        sync_gmw_events.gmw_check_existing_registrations()
