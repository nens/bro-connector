from django.core.management.base import BaseCommand
from django.db.models import Count

from gmw.models import GeoOhmCable


class Command(BaseCommand):
    help = (
        "Sync electrode_count on every GeoOhmCable to match the number of "
        "Electrode objects that are actually linked to it. "
        "Run this once after the 0005 migration to bring existing data in sync."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be updated without writing to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        cables = GeoOhmCable.objects.annotate(
            actual_electrode_count=Count("electrode")
        )

        updated = 0
        skipped = 0

        for cable in cables:
            actual = cable.actual_electrode_count
            if cable.electrode_count != actual:
                self.stdout.write(
                    f"  {'[DRY-RUN] ' if dry_run else ''}"
                    f"{cable} -- electrode_count "
                    f"{cable.electrode_count} -> {actual}"
                )
                if not dry_run:
                    # Use update_fields to bypass the reconciliation logic in save().
                    GeoOhmCable.objects.filter(pk=cable.pk).update(
                        electrode_count=actual
                    )
                updated += 1
            else:
                skipped += 1

        action = "Would update" if dry_run else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} {updated} cable(s). {skipped} already in sync."
            )
        )
