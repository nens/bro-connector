from django.core.management.base import BaseCommand
from gmw.models import GroundwaterMonitoringWellStatic
from bro.models import Organisation


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--kvk",
            type=int,
            help="Het kvk nummer waaraan je putten zonder organizatie wilt toekennen",
        )

    def handle(self, *args, **options):
        kvk_nr = int(options["kvk"])

        org = Organisation.objects.all().filter(company_number=kvk_nr).first()

        for well in GroundwaterMonitoringWellStatic.objects.all().filter(
            delivery_accountable_party=None
        ):
            well.delivery_accountable_party = org
            well.in_management = False
            well.save()
