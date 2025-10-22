from django.core.management.base import BaseCommand
from gmw.bro_validators.well_validation import WellValidation
from gmw.models import GroundwaterMonitoringWellStatic


class Command(BaseCommand):
    help = "Valideer alle Grondwatermonitoring Putten in het geheel en update de BRO Compleet en Benodigde acties velden die aangeven of de volledige put BRO Compleet is. Zo niet, dan geeft het Benodigde acties veld weer welke acties in welk (sub)object nodig zijn om het BRO compleet te maken."

    def handle(self, *args, **kwargs):
        well_static_query = GroundwaterMonitoringWellStatic.objects.all()

        for well_static in well_static_query:
            well_validation_state = (
                WellValidation()
            )  # initialize the well validation state
            complete, actions = well_validation_state.well_complete(well_static)

            well_static.complete_bro = complete
            well_static.bro_actions = actions

            well_static.save()
