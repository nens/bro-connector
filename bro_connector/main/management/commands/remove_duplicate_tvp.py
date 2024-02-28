from typing import Any
from django.core.management.base import BaseCommand
from gld.models import (
    Observation,
    MeasurementTvp,
    MeasurementPointMetadata,
)
import reversion


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> str | None:
        for observation in Observation.objects.all():
            MeasurementTvp.objects.filter(
                observation=observation,
                measurement_time__lt=observation.observation_starttime,
            ).delete()

            if observation.observation_endtime is not None:
                MeasurementTvp.objects.filter(
                    observation=observation,
                    measurement_time__gt=observation.observation_endtime,
                ).delete()

            print(observation.observation_id)
