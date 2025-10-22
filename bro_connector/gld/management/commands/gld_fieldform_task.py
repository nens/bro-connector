import main.localsecret as ls
from django.core.management.base import BaseCommand
from main.utils.gld_fieldform import FieldFormGenerator


class Command(BaseCommand):
    help = "Generate a FieldForm Locations document."

    def handle(self, *args, **options):
        # Create PMG FieldFrom
        try:
            generator1 = FieldFormGenerator(ftp_path=ls.ftp_gld_pmg_path)
            generator1.generate()
            # generator1.delete_old_files_from_ftp()
        except Exception as e:
            print(f"Error during PMG FieldForm: {e}")

        # Create HMN FieldFrom
        try:
            generator2 = FieldFormGenerator(ftp_path=ls.ftp_gld_hmn_path)
            generator2.generate()
            # generator2.delete_old_files_from_ftp()
        except Exception as e:
            print(f"Error during HMN FieldForm: {e}")
