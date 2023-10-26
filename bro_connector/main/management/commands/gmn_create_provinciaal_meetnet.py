from django.core.management.base import BaseCommand
from gmn_aanlevering.models import (
    GroundwaterMonitoringNet,
    MeasuringPoint,
)
from gmw_aanlevering.models import GroundwaterMonitoringTubesStatic


class Command(BaseCommand):
    """
    Class to:
        - set up a GMN
        - check up al existing filters in database
        - create measuringpoints for each filter.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "meetnet_naam", type=str, help="Hoe moet het meetnet heten?"
        )

    def handle(self, *args, **options):
        meetnet_naam = options["meetnet_naam"]

        # Check of het meetnet onder deze naam al bestaat
        meetnet_exists = self.check_existence_meetnet(meetnet_naam)
        if meetnet_exists:
            print(
                f"Het meetnet {meetnet_naam} bestaat al. Verwijder dit object of kies een andere naam."
            )
            return
        else:
            print(f"Het meetnet {meetnet_naam} wordt aangemaakt.")
            new_gmn_obj = GroundwaterMonitoringNet(name=meetnet_naam)
            new_gmn_obj.save()

        # Haal all Filters op en maak hiervoor Measuring points aan
        gmw_tubes = GroundwaterMonitoringTubesStatic.objects.all()

        print(
            f"{len(gmw_tubes)} filters gevonden in de database. Hiervoor worden Measuring Points aangemaakt, gelinkt aan het '{meetnet_naam}' Meetnet"
        )

        for tube in gmw_tubes:
            measuring_point = MeasuringPoint(
                gmn=new_gmn_obj,
                groundwater_monitoring_tube=tube,
                code=f"{tube.groundwater_monitoring_well.bro_id}_{tube.tube_number}",
            )
            measuring_point.save()

        print("Operatie succesvol afgerond.")

    def check_existence_meetnet(self, meetnet_naam):
        qs_count = GroundwaterMonitoringNet.objects.filter(name=meetnet_naam).count()

        if qs_count == 0:
            return False

        else:
            return True
