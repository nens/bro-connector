from typing import Any
from django.core.management.base import BaseCommand
from gld.models import (
    MeasurementTvp,
    MeasurementPointMetadata,
)
import reversion


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> str | None:
        for mpm in MeasurementPointMetadata.objects.all():
            print(".")
            if MeasurementTvp.objects.filter(
                measurement_point_metadata = mpm
            ).count() == 0:
                print(f"delete: {mpm}")
                mpm.delete()
