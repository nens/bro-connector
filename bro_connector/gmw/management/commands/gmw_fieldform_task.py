from django.core.management.base import BaseCommand
from main.utils.gmw_fieldform import FieldFormGenerator, delete_old_files_from_ftp


class Command(BaseCommand):
    help = "Generate a FieldForm Locations document."

    def handle(self, *args, **options):
        generator = FieldFormGenerator()
        generator.generate()
        delete_old_files_from_ftp()
