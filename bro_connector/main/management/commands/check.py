from django.core.management.base import BaseCommand


from gld import models

failed_update_strings = ["failed_once", "failed_twice", "failed_thrice"]


class Command(BaseCommand):
    help = """Custom command for import of GIS data."""

    def handle(self, *args, **options):
        for object in models.MeasurementPointMetadata.objects.all():
            print(
                models.TypeStatusQualityControl.objects.filter(
                    id=object.qualifier_by_category_id
                )
            )
