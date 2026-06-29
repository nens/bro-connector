from django.core.management.base import BaseCommand
from django.db.models import Count

from gmw.models import GeoOhmCable, GroundwaterMonitoringTubeStatic


class Command(BaseCommand):
    help = (
        "Sync geo_ohm_cable_count on every GroundwaterMonitoringTubeStatic "
        "to match the number of GeoOhmCable objects that are actually linked to it. "
        "Run this once after the 0004 migration to bring existing data in sync."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be updated without writing to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Annotate every tube with its actual cable count in a single query.
        tubes = GroundwaterMonitoringTubeStatic.objects.annotate(
            actual_cable_count=Count("geo_ohm_cable")
        )

        updated = 0
        skipped = 0

        for tube in tubes:
            actual = tube.actual_cable_count
            if tube.geo_ohm_cable_count != actual:
                self.stdout.write(
                    f"  {'[DRY-RUN] ' if dry_run else ''}"
                    f"{tube} — geo_ohm_cable_count "
                    f"{tube.geo_ohm_cable_count} → {actual}"
                )
                if not dry_run:
                    # Use update_fields to skip the reconciliation logic in save().
                    GroundwaterMonitoringTubeStatic.objects.filter(
                        pk=tube.pk
                    ).update(geo_ohm_cable_count=actual)
                updated += 1
            else:
                skipped += 1

        action = "Would update" if dry_run else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} {updated} tube(s). {skipped} already in sync."
            )
        )
