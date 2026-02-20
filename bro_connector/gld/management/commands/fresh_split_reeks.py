from typing import Literal
from main.settings.base import KVK_USER
from django.core.management.base import BaseCommand
from gld.models import GroundwaterLevelDossier, Observation, ObservationMetadata, ObservationProcess, Organisation, MeasurementTvp
from django.db.models import Count
from django.db import transaction

def get_organisation() -> Organisation:
    return Organisation.objects.get_or_create(
        company_number = KVK_USER
    )[0]

def setup_observation_metadata(type: Literal["volledigBeoordeeld", "voorlopig", "controle"]):
    user_org = get_organisation()
    match type:
        case "volledigBeoordeeld":
            return ObservationMetadata.objects.get_or_create(
                observation_type = "reguliereMeting",
                status = "volledigBeoordeeld",
                responsible_party = user_org,
            )
        case "voorlopig":
            return ObservationMetadata.objects.get_or_create(
                observation_type = "reguliereMeting",
                status = "voorlopig",
                responsible_party = user_org,
            )
        case "controle":
            return ObservationMetadata.objects.get_or_create(
                observation_type = "controlemeting",
                responsible_party = user_org,
            )

def setup_observation_proces(type: Literal["sensor", "manual"]):
    if type == "sensor":
        return ObservationProcess.objects.get_or_create(
            process_reference = "STOWAgwst",
            measurement_instrument_type = "druksensor",
            air_pressure_compensation_type = "capillair",
            evaluation_procedure = "oordeelDeskundig",
        )[0]
    return ObservationProcess.objects.get_or_create(
        process_reference = "STOWAgwst",
        measurement_instrument_type = "analoogPeilklokje",
        evaluation_procedure = "oordeelDeskundig",
    )[0]


def check_too_many_measurements(gld: GroundwaterLevelDossier):
    Observation.objects.filter().annotate()

class Command(BaseCommand):
    def handle(self, *args, **options):
        user_organisation = get_organisation()
        qs = (
            Observation.objects
            .annotate(measurement_count=Count("measurement"))
            .filter(
                measurement_count__gt=8000,
                groundwater_level_dossier__quality_regime="IMBRO",
                groundwater_level_dossier__groundwater_monitoring_tube__groundwater_monitoring_well_static__delivery_accountable_party=user_organisation,
            )
        )

        for observation in qs:
            with transaction.atomic():
                BATCH_SIZE = 8000
                all_ids = list(
                    observation.measurement
                    .order_by("measurement_time")
                    .values_list("pk", flat=True)
                )

                total = len(all_ids)

                # If already <= 8000, skip
                if total <= BATCH_SIZE:
                    return

                # Keep first 8000 on original
                remaining_ids = all_ids[BATCH_SIZE:]

                for start in range(0, len(remaining_ids), BATCH_SIZE):
                    batch_ids = remaining_ids[start:start + BATCH_SIZE]

                    new_observation = Observation.objects.create(
                        groundwater_level_dossier=observation.groundwater_level_dossier,
                        observation_metadata=observation.observation_metadata,
                        observation_process=observation.observation_process,
                    )

                    MeasurementTvp.objects.filter(pk__in=batch_ids).update(
                        observation=new_observation
                    )

                    moved_qs = new_observation.measurement.order_by("measurement_time")

                    first_m = moved_qs.first()
                    last_m = moved_qs.last()

                    new_observation.observation_starttime = first_m.measurement_time

                    # Final chunk keeps endtime None if original had None
                    if (
                        observation.observation_endtime is None
                        and len(batch_ids) < BATCH_SIZE
                    ):
                        new_observation.observation_endtime = None
                    else:
                        new_observation.observation_endtime = last_m.measurement_time

                    new_observation.save()

                # Finally update original observation times
                original_qs = observation.measurement.order_by("measurement_time")

                first_m = original_qs.first()
                last_m = original_qs.last()

                observation.observation_starttime = first_m.measurement_time
                observation.observation_endtime = last_m.measurement_time
                observation.save()

            # First try one
            exit(0)