from django.core.management.base import BaseCommand
from gld.models import Observation, ObservationProcess
# import polars as pl


class Command(BaseCommand):
    def handle(self, *args, **options):
        # unique_processes = ObservationProcess.objects.values(
        #     "process_reference",
        #     "measurement_instrument_type",
        #     "air_pressure_compensation_type",
        #     "process_type",
        #     "evaluation_procedure",
        # ).distinct()
        # obs_processes = Observation.objects.values_list("observation_process__observation_process_id",flat=True).distinct()
        # print(obs_processes)
        # unique_process_ids = []
        for obs in Observation.objects.all():
            obs_process: ObservationProcess = obs.observation_process
            procedure = (
                ObservationProcess.objects.filter(
                    process_reference=obs_process.process_reference,
                    measurement_instrument_type=obs_process.measurement_instrument_type,
                    air_pressure_compensation_type=obs_process.air_pressure_compensation_type,
                    process_type=obs_process.process_type,
                    evaluation_procedure=obs_process.evaluation_procedure,
                )
                .order_by("observation_process_id")
                .first()
            )
            # if procedure.observation_process_id not in unique_process_ids:
            #     unique_process_ids.append(procedure.observation_process_id)
            obs.observation_process = procedure
            obs.save()
            # print(obs.observation_process.observation_process_id)

        # print(unique_process_ids)

        # obs_processes = Observation.objects.values_list("observation_process__observation_process_id", flat=True).distinct()
        # print(obs_processes)
