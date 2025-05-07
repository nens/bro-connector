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
            "--handler", type=str, help="API handler: kvk, ogc"
        )

    def handle(self, *args, **options):
        kvk_number = options["kvk_number"]
        handler = options["handler"]
        print("KVK number: ",kvk_number)

        retrieve_duplicates_gmw.run(kvk_number=kvk_number,handler=handler)



