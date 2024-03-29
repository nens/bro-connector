from django.core.management.base import BaseCommand
from gmw.models import GroundwaterMonitoringWellStatic

class Command(BaseCommand):
    """
    Run eenmalig om lat long in te vullen. Is nodig om de kaart werkende te krijgen
    """

    def handle(self, *args, **kwargs):
        gmws = GroundwaterMonitoringWellStatic.objects.all()

        for gmw in gmws:
            gmw.save()