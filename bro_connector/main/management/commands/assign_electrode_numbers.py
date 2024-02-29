from django.core.management.base import BaseCommand
from gmw.models import (
    ElectrodeStatic,
    ElectrodeDynamic,
)
import reversion


class Command(BaseCommand):
    def handle(self, *args, **options):
        # Convert from dynamic to Static
        electrodes = ElectrodeDynamic.objects.filter(
            electrode_number__gt=0,
        )

        for electrode in electrodes:
            static = ElectrodeStatic.objects.get(
                electrode_static_id=electrode.electrode_static.electrode_static_id
            )
            static.electrode_number = electrode.electrode_number
            static.save()

        electrodes = ElectrodeStatic.objects.filter(
            electrode_number=None,
        )

        unique_cables = []

        for electrode in electrodes:
            print(electrode)
            if electrode.geo_ohm_cable in unique_cables:
                # Has already been handled.
                continue

            electrodes_of_cable_ordered = ElectrodeStatic.objects.filter(
                geo_ohm_cable=electrode.geo_ohm_cable
            ).order_by("electrode_position")

            num = 1
            for orderded_electrode in electrodes_of_cable_ordered:
                print(orderded_electrode)
                with reversion.create_revision():
                    orderded_electrode.electrode_number = num
                    orderded_electrode.save()
                    reversion.set_comment(
                        "Used a script to assign an electrode number as none was known."
                    )

                num += 1

            unique_cables.append(electrode.geo_ohm_cable)
