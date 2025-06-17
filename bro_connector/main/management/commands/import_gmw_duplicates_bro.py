from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import division

from django.core.management.base import BaseCommand
from ..tasks import retrieve_duplicates_gmw


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--kvk_number",
            type=int,
            help="Gebruik een KVK-nummer om de data in te spoelen",
        )
        parser.add_argument(
            "--properties",
            type=str,
            nargs="+",
            default=["well_code", "nitg_code"],
            help="Specificeer de properties om duplicaten op te filteren (default: well_code nitg_code)",
        )
        parser.add_argument(
            "--logging",
            type=str,
            choices=["True", "False"],
            default="True",
            help="Enable or disable logging (True or False)",
        )

    def handle(self, *args, **options):
        kvk_number = options["kvk_number"]
        properties = options["properties"]
        logging = options["logging"] == "True"

        retrieve_duplicates_gmw.run(
            kvk_number=kvk_number, properties=properties, logging=logging
        )
