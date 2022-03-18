from django.core.management.base import BaseCommand
from django.db import transaction

import sys
import pandas as pd
import logging

from _nens_demo.models import aanleverinfo_filters




logger = logging.getLogger(__name__)

def transform_code(csvfile):
    csvfile['filternr'] = csvfile['Meetpunt'].str.split('-').apply(lambda x:('000'+x[1])).apply(lambda x: x[len(x)-3:len(x)])
    csvfile['grondwaterstation'] = csvfile['Meetpunt'].str.split('-').apply(lambda x:x[0])
    csvfile['code'] = csvfile['grondwaterstation']+'-'+csvfile['filternr']
    csvfile['Voorlopig aanleveren aan BRO?'][csvfile['Voorlopig aanleveren aan BRO?']!='Ja']='Nee'

    return(csvfile)

@transaction.atomic
def import_csv(csv_path):
    try:
        csvfile = pd.read_csv(csv_path,sep = ';', header=0)
        csvfile = transform_code(csvfile)
    except:
        logger.error("Error: failed reading csvfile")

    try:
        for i in range(len(csvfile)):
            print(csvfile.iloc[i]['code'],csvfile.iloc[i]['Voorlopig aanleveren aan BRO?'])
            record, created = \
            aanleverinfo_filters.objects.update_or_create(
                meetpunt=csvfile.iloc[i]['code'],
                defaults=dict(
                    aanleveren=csvfile.iloc[i]['Voorlopig aanleveren aan BRO?']
                )
            )

    except:
            logger.error("Error: failed processing csvfile")

class Command(BaseCommand):
    help = """Custom command for import of GIS data."""

    def add_arguments(self, parser):
        parser.add_argument(
            '-csv_path',
            action='store',
            dest='csv_path',
            nargs='+',
            default=None,
            help='path to csv delivery settings filters')

    def handle(self, *args, **options):
        print(options['csv_path'])
        for csv in options['csv_path']:
            try:
                import_csv(csv)
            except:
                logger.error("Import failed (partially)")

            logger.error("Import finished succesfully")
