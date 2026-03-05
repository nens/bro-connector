from main.settings.base import KVK_USER
from django.core.management.base import BaseCommand
from gld.models import Observation, Organisation, MeasurementPointMetadata
from django.db.models import Count
from django.db import transaction

def get_organisation() -> Organisation:
    return Organisation.objects.get_or_create(
        company_number = KVK_USER
    )[0]



class Command(BaseCommand):
    def handle(self, *args, **options):
        user_organisation = get_organisation()

        
        qs = (
            Observation.objects
            .annotate(measurement_count=Count("measurement"))
            .filter(
                groundwater_level_dossier__quality_regime="IMBRO",
                groundwater_level_dossier__groundwater_monitoring_tube__groundwater_monitoring_well_static__delivery_accountable_party=user_organisation,
            )
        )

        for observation in qs:
            print(f"Processing observation {observation} with {observation.measurement.count()} measurements")
            first_measurement = observation.measurement.order_by("measurement_time").first()
            if first_measurement and observation.observation_starttime != first_measurement.measurement_time:
                observation.observation_starttime = first_measurement.measurement_time
                observation.save(update_fields=["observation_starttime"])