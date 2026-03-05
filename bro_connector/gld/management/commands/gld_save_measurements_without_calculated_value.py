from django.core.management.base import BaseCommand
from gld.models import MeasurementTvp
from gmw.models import GroundwaterMonitoringTubeStatic
from gld.signals import _calculate_value, _calculate_value_tube
import time

def on_save_measurement(instance: MeasurementTvp):
    if not instance.calculated_value and instance.field_value:
        if instance.field_value_unit in ["m", "cm", "mm"]:
            instance.calculated_value = _calculate_value(
                instance.field_value, instance.field_value_unit
            )
        else:
            # Access the related groundwater_monitoring_tube_static instance
            tube_static = GroundwaterMonitoringTubeStatic.objects.get(
                groundwater_monitoring_tube_static_id = instance.observation.groundwater_level_dossier.groundwater_monitoring_tube_id
            )
            # Retrieve the latest state
            latest_state = tube_static.state.order_by("-date_from").first()

            # Get the tube_top_position
            if latest_state:
                tube_top_position = latest_state.tube_top_position
            else:
                tube_top_position = None

            instance.calculated_value = _calculate_value_tube(
                float(instance.field_value), instance.field_value_unit, tube_top_position
            )


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("Saving Measurements:")
        start = time.time()
        measurements_for_update = []
        measurements = MeasurementTvp.objects.filter(calculated_value__isnull=True, field_value__isnull=False)
        for m in measurements:
            on_save_measurement(m)
            measurements_for_update.append(m)

        end = time.time()
        print(f"Processing time: {end-start}s")
        print(f"Number of instances: {len(measurements_for_update)}")

        MeasurementTvp.objects.bulk_update(
            measurements_for_update, 
            ["calculated_value"], 
            batch_size=5000
        )
        end2 = time.time()
        print(f"Updating time: {end2-end}s")