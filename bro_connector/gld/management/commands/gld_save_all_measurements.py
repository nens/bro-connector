from django.core.management.base import BaseCommand
from gld.models import MeasurementTvp


class Command(BaseCommand):
    def handle(self, *args, **options):
        measurements = MeasurementTvp.objects.all()
        for measurement in measurements:
            measurement.save()
