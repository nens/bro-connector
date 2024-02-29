from django.core.management.base import BaseCommand
from gmw.models import (
    ElectrodeStatic,
    ElectrodeDynamic,
)
import reversion


class Command(BaseCommand):
    def handle(self, *args, **options):
        electrodes = ElectrodeStatic.objects.all()

        for electrode in electrodes:
            print(electrode)

            dynamic = ElectrodeDynamic.objects.filter(
                electrode_static=electrode
            ).first()

            print(dynamic)

            if dynamic == None:
                continue

            with reversion.create_revision():
                electrode.electrode_number = dynamic.electrode_number
                electrode.save()
                reversion.set_comment(
                    "Used a script to copy the electrode number from the dynamic to the static object."
                )
