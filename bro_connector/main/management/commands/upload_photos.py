import os
import cv2 as cv
from base64 import b64decode, b64encode

from django.core.management.base import BaseCommand
from django.core.files import File
from gmw.models import Picture, GroundwaterMonitoringWellStatic

import pysftp
from main import localsecret as ls

# herschrijf functie naar find_monitoring_well en GroundwaterMonitoringWellStatic
def find_monitoring_well(well_code: str) -> GroundwaterMonitoringWellStatic:
    print(f'well: {well_code}')

    well = GroundwaterMonitoringWellStatic.objects.filter(
        nitg_code = well_code
    ).order_by('groundwater_monitoring_well_static_id').first()
    return well

class Command(BaseCommand):
    """
    Class to:
        - uploading photo's from a specified path
        
        photo's follow the name:
        "foto {number}_{nitg code}_yyyymmdd-hhmmss.jpg"
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--foto",
            type=str,
            help="Het path naar de foto's.",
        )

    def handle(self, *args, **options):
        photo_folder_path = str(options["foto"])

        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None
        with pysftp.Connection(ls.ftp_ip, username=ls.ftp_username, password=ls.ftp_password, port=22, cnopts=cnopts) as sftp:
            with sftp.cd(ls.ftp_gld_path):
                files = sftp.listdir(ls.ftp_gld_path)

                jpgs = [file for file in files if '.jpg' in file]

                for jpg in jpgs:
                    photo_nr, well_nr, filter_nr, datetime = jpg.split('_')[:-1] + [jpg.split('_')[-1][:-4]]
                    
                    # convert datetime into correct format (YYYY-MM-DD HH:MM[:ss[.uuuuuu]][TZ])
                    datetime = f'{datetime[:4]}-{datetime[4:6]}-{datetime[6:8]} {datetime[9:11]}:{datetime[11:13]}:{datetime[13:15]}'

                    well = find_monitoring_well(well_nr)
                    photo_path = f'{photo_folder_path}\{jpg}'

                    # Open the .jpg file in binary mode
                    with sftp.open(jpg, mode='rb') as img_file:

                        file_name = os.path.basename(photo_path)
                        picture = Picture.objects.create(
                            groundwater_monitoring_well_static=well,
                            recording_datetime=datetime,
                            picture=File(img_file, name=file_name),
                            description="Foto's inspoelen",
                            )

                    picture.save()

                    print(f"Image {jpg} saved successfully as binary data.")
                    
                    verwerkt_path = ls.ftp_gld_path + '\verwerkt'
                    if sftp.exists(verwerkt_path):
                        print(f'folder verwerkt exists.')
                    else:
                        sftp.mkdir(verwerkt_path)
                        print('folder verwerkt created')

                    destination_path = verwerkt_path + f'\{jpg}'
                    sftp.rename(ls.ftp_gld_path, destination_path)
                    print(f"File moved from '{ls.ftp_gld_path}' to '{destination_path}'")