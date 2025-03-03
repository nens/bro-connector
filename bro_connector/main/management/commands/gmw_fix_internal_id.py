from django.core.management.base import BaseCommand
from gmw.models import GroundwaterMonitoringWellStatic


class Command(BaseCommand):
    help = "Fixes internal_id of GroundwaterMonitoringWellStatic after creating internal_id."

    def handle(self, *args, **options):
        for well in GroundwaterMonitoringWellStatic.objects.all():
            well.internal_id = str(well)
            well.save()
