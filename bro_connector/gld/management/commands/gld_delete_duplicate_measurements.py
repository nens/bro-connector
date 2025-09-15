from django.core.management.base import BaseCommand
from gld.models import MeasurementTvp
from django.db import transaction
from collections import defaultdict

class Command(BaseCommand):
    help = "Remove duplicate MeasurementTvp rows (same observation_id + measurement_time), keeping only one."

    def handle(self, *args, **options):
        self.stdout.write("Looking for duplicate measurements...")

        duplicates_map = defaultdict(list)

        # Group rows by (observation_id, measurement_time)
        for mtvp in MeasurementTvp.objects.all().only(
                "measurement_tvp_id", 
                "observation", 
                "measurement_time",
                "field_value",
                "field_value_unit",
            ):
            key = (mtvp.observation.observation_id, mtvp.measurement_time, mtvp.field_value, mtvp.field_value_unit)
            duplicates_map[key].append(mtvp.measurement_tvp_id)

        # Keep the first, mark the rest for deletion
        ids_to_delete = []
        for key, ids in duplicates_map.items():
            if len(ids) > 1:
                ids_to_delete.extend(ids[1:])  # keep the first, delete the rest

        print(ids_to_delete)
        stop

        if not ids_to_delete:
            self.stdout.write(self.style.SUCCESS("✅ No duplicates found."))
            return

        # Delete in one transaction
        with transaction.atomic():
            deleted_count, _ = MeasurementTvp.objects.filter(id__in=ids_to_delete).delete()

        self.stdout.write(
            self.style.SUCCESS(f"✅ Deleted {deleted_count} duplicate measurement(s).")
        )
