import os
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
        photo upcomming format:
        "{well_code}_yyyymmdd-hhmmss_foto {number}.jpg"
        photo current format:
        "foto {number}_{nitg code}_yyyymmdd-hhmmss.jpg"
    """


    def handle(self, *args, **options):
        # Use FTP Folder of choice (ONBDERHOUD, GLD_PMG, ...)
        ftp_folder_path = str(options["ftp_folder"])

        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None

        try:
            with pysftp.Connection(ls.ftp_ip, username=ls.ftp_username, password=ls.ftp_password, port=22, cnopts=cnopts) as sftp:
                verwerkt_path = ftp_folder_path + '/verwerkt'
                if sftp.exists(verwerkt_path):
                    print(f'folder verwerkt exists.')
                else:
                    sftp.mkdir(verwerkt_path)
                    print('folder verwerkt has been created')

                
                    
                with sftp.cd(ftp_folder_path):
                    files = sftp.listdir(ftp_folder_path)
                    jpgs = [file for file in files if '.jpg' in file]

                    for jpg in jpgs:
                        jpg_short = jpg[:-4]
                        jpg_split = jpg_short.split('_')
                        # current photo filename format
                        photo_nr, well_code, datetime_str = jpg_split[0].split(' ')[-1], jpg_split[1], jpg_split[2]
                        # upcomming filename format
                        # well_code, datetime_str, photo_nr = jpg_split[0], jpg_split[1], jpg_split[2].split(' ')[-1]
                        
                        # convert datetime into correct format (YYYY-MM-DD HH:MM[:ss[.uuuuuu]][TZ])
                        datetime = f'{datetime[:4]}-{datetime[4:6]}-{datetime[6:8]} {datetime[9:11]}:{datetime[11:13]}:{datetime[13:15]}'

                        well = find_monitoring_well(well_code)
                        photo_path = f'{ftp_folder_path}/{jpg}'

                        # Open the .jpg file in binary mode
                        with sftp.open(jpg, mode='rb') as img_file:
                            file_name = os.path.basename(photo_path)
                            picture, created = Picture.objects.update_or_create(
                                groundwater_monitoring_well_static=well,
                                recording_datetime=datetime,
                                picture=File(img_file, name=file_name),
                                description="Foto's inspoelen",
                            )

                        print(f"Image {jpg} saved successfully in image field.")
                        
                        destination_path = verwerkt_path + f'/{jpg}'
                        sftp.rename(photo_path, destination_path)
                        print(f"{jpg} moved from '{ftp_folder_path}' to '{destination_path}'")

        except Exception as e:
            print(f"Failed saving images: {e}")
