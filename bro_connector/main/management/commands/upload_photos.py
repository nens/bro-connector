import os

from django.core.management.base import BaseCommand
from django.core.files import File
from gmw.models import Picture, GroundwaterMonitoringWellStatic

import pysftp
from main import localsecret as ls


# herschrijf functie naar find_monitoring_well en GroundwaterMonitoringWellStatic
def find_monitoring_well(well_code: str) -> GroundwaterMonitoringWellStatic:
    print(f"well: {well_code}")

    well = (
        GroundwaterMonitoringWellStatic.objects.filter(nitg_code=well_code)
        .order_by("groundwater_monitoring_well_static_id")
        .first()
    )
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

    def add_arguments(self, parser):
        parser.add_argument(
            "--ftp_folder",
            type=str,
            help="Gebruik een ftp_folder om fotos in te spoelen",
        )

    def handle(self, *args, **options):
        # Use FTP Folder of choice (ONBDERHOUD, GLD_PMG, ...)
        ftp_folder_path = str(options["ftp_folder"])

        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None

        try:
            with pysftp.Connection(
                ls.ftp_ip,
                username=ls.ftp_username,
                password=ls.ftp_password,
                port=22,
                cnopts=cnopts,
            ) as sftp:
                verwerkt_path = ftp_folder_path + "/verwerkt"
                with sftp.cd(ftp_folder_path):
                    files = sftp.listdir(ftp_folder_path)
                    jpgs = [file for file in files if ".jpg" in file]

                    for jpg in jpgs:
                        jpg_short = jpg[:-4]
                        jpg_split = jpg_short.split("_")
                        # current photo filename format
                        well_code, datetime_str = (
                            jpg_split[1],
                            jpg_split[2],
                        )

                        datetime = f"{datetime_str[:4]}-{datetime_str[4:6]}-{datetime_str[6:8]} {datetime_str[9:11]}:{datetime_str[11:13]}:{datetime_str[13:15]}"

                        well = find_monitoring_well(well_code)
                        photo_path = f"{ftp_folder_path}/{jpg}"

                        # Open the .jpg file in binary mode
                        with sftp.open(jpg, mode="rb") as img_file:
                            file_name = os.path.basename(photo_path)
                            Picture.objects.create(
                                groundwater_monitoring_well_static=well,
                                recording_datetime=datetime,
                                picture=File(img_file, name=file_name),
                                description="Foto's inspoelen",
                            )

                        print(f"Image {jpg} saved successfully in image field.")

                        destination_path = verwerkt_path + f"/{jpg}"
                        sftp.rename(photo_path, destination_path)
                        print(
                            f"{jpg} moved from '{ftp_folder_path}' to '{destination_path}'"
                        )

        except Exception as e:
            print(f"Failed saving images: {e}")
