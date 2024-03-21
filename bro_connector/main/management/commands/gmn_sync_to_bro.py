from django.core.management.base import BaseCommand
from main.management.tasks.gmn_sync import sync_gmn


class Command(BaseCommand):
    """This command handles all 4 type of registrations for GMN's
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
        sync_gmn()