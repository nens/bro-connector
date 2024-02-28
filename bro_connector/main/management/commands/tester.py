from typing import Any
from django.core.management.base import BaseCommand
from frd.models import FormationresistanceRecord
import reversion


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> str | None:
        resistance_records = FormationresistanceRecord.objects.all()

        for record in resistance_records:
            record.vertical_position = record.vertical_position * -1
            record.save()
