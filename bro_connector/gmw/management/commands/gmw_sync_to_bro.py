from django.core.management.base import BaseCommand
from gmw.management.tasks import sync_gmw_events
from main.settings.base import env
from django.apps import apps


def _is_demo(self):
    if env == "production":
        return False
    return True


def _get_registrations_dir(app: str):
    app_config = apps.get_app_config(app)
    base_dir = app_config.path
    return f"{base_dir}\\registrations"


class Command(BaseCommand):
    help = (
        """Command to automatically register all new events and send them to the BRO."""
    )

    def handle(self, *args, **options):
        # Initialize settings
        demo = _is_demo()
        registrations_dir = _get_registrations_dir("gmw")
        print(registrations_dir)

        # Check the database for new wells/tubes and start a gmw registration for these objects if its it needed
        sync_gmw_events.gmw_create_sourcedocs_wells(
            registrations_dir,
        )

        # Check existing registrations
        sync_gmw_events.gmw_check_existing_registrations(registrations_dir, demo)
