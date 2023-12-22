from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    Handles the sync between the bro-connector and the BRO.
    Runs daily as cronjob.
    """
    help = 'Syncs the FRD data to the BRO'

    def handle(self, *args, **kwargs):
        pass

