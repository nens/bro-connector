from typing import Any
from django.core.management.base import BaseCommand
from gld import models as gld_models


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> str | None:
        for obs in gld_models.Observation.objects.all():
            print(obs)
            count = 0
            duplicates = False
            for tvp in gld_models.MeasurementTvp.objects.filter(
                observation = obs
            ):
                count += 1
                try:
                    tvp_ins = gld_models.MeasurementTvp.objects.get(
                        observation=tvp.observation,
                        measurement_time=tvp.measurement_time,
                        field_value=tvp.field_value,
                        field_value_unit=tvp.field_value_unit,
                    )
                except gld_models.MeasurementTvp.MultipleObjectsReturned:
                    duplicates = True
                    metadata = tvp.measurement_point_metadata
                    metadata.delete()

                if count > 50 and duplicates is False:
                    break
