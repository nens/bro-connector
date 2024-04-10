from django.core.management.base import BaseCommand
import datetime
from gmw.models import (
    Event,
)
import reversion


class Command(BaseCommand):
    def handle(self, *args, **options):
        for event in Event.objects.all():
            with reversion.create_revision():
                wd = event.groundwater_monitoring_well_dynamic
                td = event.groundwater_monitoring_tube_dynamic
                ed = event.electrode_dynamic

                try:
                    date = datetime.datetime.strptime(event.event_date,'%Y-%m-%d')
                except ValueError:
                    date = datetime.datetime.strptime(event.event_date,'%Y')
                except TypeError:
                    date = datetime.datetime.strptime("1900-01-01",'%Y-%m-%d')

                if wd:
                    wd.date_from = date
                    wd.save()
                
                if td:
                    td.date_from = date
                    td.save()

                if ed:
                    ed.date_from = date
                    ed.save()

                reversion.set_comment("Set date based from Event.")
