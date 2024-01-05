from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import division

from django.core.management.base import BaseCommand
from ..tasks import (
    retrieve_historic_gmw,
    retrieve_historic_frd,
    retrieve_historic_gld,
    retrieve_historic_gmn,
    retrieve_historic_gar,
)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--kvk_number",
            type=int,
            help="Gebruik een KVK-nummer om de data in te spoelen",
        )
        parser.add_argument(
            "--csv_file",
            type=str,
            help="Gebruik een csv bestand met putinformatie om data in te spoelen",
        )
        parser.add_argument(
            "--type", type=str, help="Type BRO bericht: gmw, gld, gar, gmn, frd"
        )

    def handle(self, *args, **options):
        kvk_number = options["kvk_number"]
        csv_file = options["csv_file"]
        bro_type = options["type"]

        if bro_type == "gmw":
            retrieve_historic_gmw.run(kvk_number=kvk_number)

        elif bro_type == "gld":
            retrieve_historic_gld.run(kvk_number=kvk_number)

        elif bro_type == "gar":
            pass
            # retrieve_historic_gar.run(kvk_number = kvk_number)

        elif bro_type == "gmn":
            retrieve_historic_gmn.run(kvk_number=kvk_number)

        elif bro_type == "frd":
            retrieve_historic_frd.run(kvk_number=kvk_number)
