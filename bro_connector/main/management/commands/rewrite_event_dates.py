import datetime
from django.core.management.base import BaseCommand
from gmw.models import (
    Event,
)
import reversion

def convert_event_date_str_to_datetime(event_date: str) -> datetime:
    try:
        date = datetime.datetime.strptime(event_date,'%Y-%m-%d')
    except ValueError:
        date = datetime.datetime.strptime(event_date,'%Y')
    except TypeError:
        date = datetime.datetime.strptime("1900-01-01",'%Y-%m-%d')

    return date


class Command(BaseCommand):
    def handle(self, *args, **options):
        for event in Event.objects.all():
            date = convert_event_date_str_to_datetime(event.event_date)
            with reversion.create_revision():
                event.event_date_new = date
                event.save()

                reversion.set_comment("Adjust the date from char to datetime, filled in new attribute.")
