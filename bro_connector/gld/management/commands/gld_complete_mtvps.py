from django.core.management.base import BaseCommand
from gld.models import MeasurementTvp


class Command(BaseCommand):
    def handle(self, *args, **options):
        measurement_tvps = MeasurementTvp.objects.filter(
            measurement_point_metadata__isnull=True,
        )

        for measurement in measurement_tvps:
            measurement.save()

        measurement_tvps = MeasurementTvp.objects.filter(
            calculated_value__isnull=True,
        )

        for measurement in measurement_tvps:
            measurement.save()
