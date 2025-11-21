from django.core.management.base import BaseCommand
from gld.models import GroundwaterLevelDossier, Observation, ObservationProcess, MeasurementTvp
from datetime import datetime
from django.utils.timezone import make_aware, utc

cutoff = make_aware(datetime(2021, 1, 1), utc)

class Command(BaseCommand):
    def handle(self, *args, **options):
        for dossier in GroundwaterLevelDossier.objects.filter(quality_regime="IMBRO/A"):
            imbro_dossier = GroundwaterLevelDossier.objects.filter(
                quality_regime="IMBRO",
                groundwater_monitoring_tube=dossier.groundwater_monitoring_tube,
            ).first()

            observations = Observation.objects.filter(
                groundwater_level_dossier=dossier,
                observation_endtime__gt=cutoff,
            )
            for observation in observations:
                measurements = MeasurementTvp.objects.filter(
                    observation=observation,
                    measurement_time__gt=cutoff,
                )
                first_measurement_time = measurements.order_by("measurement_time").first().measurement_time if measurements.exists() else "1900-01-01"

                # Move measurements from imbro a to imbro
                imbro_observation = Observation.objects.filter(
                    groundwater_level_dossier=imbro_dossier,
                    observation_metadata=observation.observation_metadata,
                    observation_starttime__lt=first_measurement_time,
                ).first()

                if imbro_observation is None:
                    continue
                
                print(f"Moving {len(measurements)} measurements from observation {observation.observation_id} to {imbro_observation.observation_id}")
                for measurement in measurements:
                    if MeasurementTvp.objects.filter(
                        observation=imbro_observation,
                        measurement_time=measurement.measurement_time,
                    ).exists():
                        measurement.delete()
                        print("Deleted duplicate measurement")
                        continue
                    measurement.observation = imbro_observation
                    measurement.save()



            observations = Observation.objects.filter(
                groundwater_level_dossier=dossier,
                observation_starttime__lt=cutoff,
                observation_endtime__isnull=True,
            )
            for observation in observations:
                measurements = MeasurementTvp.objects.filter(
                    observation=observation,
                    measurement_time__gt=cutoff,
                )
                first_measurement_time = measurements.order_by("measurement_time").first().measurement_time if measurements.exists() else "1900-01-01"

                # Move measurements from imbro a to imbro
                imbro_observation = Observation.objects.filter(
                    groundwater_level_dossier=imbro_dossier,
                    observation_metadata=observation.observation_metadata,
                    observation_starttime__lt=first_measurement_time,
                ).first()

                if imbro_observation is None:
                    continue

                print(f"Moving {len(measurements)} measurements from observation {observation.observation_id} to {imbro_observation.observation_id}")
                for measurement in measurements:
                    if MeasurementTvp.objects.filter(
                        observation=imbro_observation,
                        measurement_time=measurement.measurement_time,
                    ).exists():
                        measurement.delete()
                        print("Deleted duplicate measurement")
                        continue

                    measurement.observation = imbro_observation
                    measurement.save()