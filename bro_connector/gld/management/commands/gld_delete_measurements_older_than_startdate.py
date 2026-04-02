
from django.core.management.base import BaseCommand
from django.db import transaction, models
from gld.models import MeasurementTvp, Observation
from django.db.models import OuterRef, Subquery


class Command(BaseCommand):
    help = "Remove MeasurementTvps for open observations older than starttime."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Looking for observations..."))

        first_measurement_subquery = (
            MeasurementTvp.objects
            .filter(observation=OuterRef("pk"))
            .order_by("measurement_time")
            .values("measurement_time")[:1]
        )

        open_observations = (
            Observation.objects
            .filter(
                groundwater_level_dossier__quality_regime="IMBRO",
                observation_starttime__isnull=False,
                observation_endtime__isnull=True,
            )
            .annotate(first_m=Subquery(first_measurement_subquery))
            .filter(first_m__isnull=False)
        )

        to_delete = MeasurementTvp.objects.filter(
            observation__in=open_observations,
            measurement_time__lt=models.F("observation__observation_starttime"),
        )

        count = to_delete.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS("No old measurements found."))
            return

        with transaction.atomic():
            deleted_count, _ = to_delete.delete()

        self.stdout.write(
            self.style.SUCCESS(f"Deleted {deleted_count} too old measurements.")
        )
