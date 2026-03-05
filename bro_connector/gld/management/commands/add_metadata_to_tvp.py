from main.settings.base import KVK_USER
from django.core.management.base import BaseCommand
from gld.models import Observation, Organisation, MeasurementPointMetadata, MeasurementTvp
from django.db import transaction

BATCH_SIZE = 10_000


def get_organisation() -> Organisation:
    return Organisation.objects.get_or_create(
        company_number=KVK_USER
    )[0]


class Command(BaseCommand):
    def handle(self, *args, **options):
        user_organisation = get_organisation()

        measurements_qs = (
            MeasurementTvp.objects
            .filter(
                measurement_point_metadata__isnull=True,
                observation__groundwater_level_dossier__quality_regime="IMBRO",
                observation__groundwater_level_dossier__groundwater_monitoring_tube__groundwater_monitoring_well_static__delivery_accountable_party=user_organisation,
            )
            .only("measurement_tvp_id")
        )

        total = measurements_qs.count()
        self.stdout.write(f"Processing {total} measurements...")

        offset = 0
        while True:
            batch = list(
                measurements_qs[offset:offset + BATCH_SIZE]
            )
            if not batch:
                break

            with transaction.atomic():

                # Create metadata in bulk
                metadata_objects = [
                    MeasurementPointMetadata(
                        status_quality_control="nogNietBeoordeeld"
                    )
                    for _ in batch
                ]

                created_metadata = MeasurementPointMetadata.objects.bulk_create(
                    metadata_objects,
                    batch_size=BATCH_SIZE,
                )

                # Attach metadata to measurements
                for measurement, metadata in zip(batch, created_metadata):
                    measurement.measurement_point_metadata = metadata

                MeasurementTvp.objects.bulk_update(
                    batch,
                    ["measurement_point_metadata"],
                    batch_size=BATCH_SIZE,
                )

            offset += BATCH_SIZE
            self.stdout.write(f"Processed {min(offset, total)} / {total}")