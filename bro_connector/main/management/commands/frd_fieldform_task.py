from django.core.management.base import BaseCommand

from main.utils.fieldform import FieldFormGenerator, delete_old_files_from_ftp


class Command(BaseCommand):
    help = "Generate a FieldForm Locations document."

    def handle(self, *args, **options):
        generator = FieldFormGenerator()
        generator.inputfields = ["weerstand", "opmerking"]
        generator.optimal=True
        generator.generate()
        delete_old_files_from_ftp()