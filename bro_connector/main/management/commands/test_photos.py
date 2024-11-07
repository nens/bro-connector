import os
import cv2 as cv
from base64 import b64decode, b64encode

from django.core.management.base import BaseCommand
from django.core.files import File
from django.urls import path
from gmn.models import GroundwaterMonitoringNet, MeasuringPoint
from gmw.models import GroundwaterMonitoringTubeStatic, Picture, GroundwaterMonitoringWellStatic

from django.shortcuts import render


# herschrijf functie naar find_monitoring_well en GroundwaterMonitoringWellStatic
def find_monitoring_well(well_code: str) -> GroundwaterMonitoringWellStatic:
    print(f'well: {well_code}')

    well = GroundwaterMonitoringWellStatic.objects.filter(
        nitg_code = well_code
    ).order_by('groundwater_monitoring_well_static_id').first()
    return well

# def jpg_to_binary (image_path: str):
#     img = cv.imread(image_path, 2)
#     # ret, bw_img = cv.threshold(img, 127, 255, cv.THRESH_BINARY)
#     bw = cv.threshold(img, 127, 255, cv.THRESH_BINARY)
#     print(type(bw))
#     return bw



class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--foto",
            type=str,
            help="Het path naar de foto's.",
        )

    def handle(self, *args, **options):
        photo_folder_path = str(options["foto"])

        files = os.listdir(photo_folder_path)

        jpgs = [file for file in files if '.jpg' in file]



        for jpg in jpgs:
            photo_nr, well_nr, filter_nr, datetime = jpg.split('_')[:-1] + [jpg.split('_')[-1][:-4]]
            
            # convert datetime into correct format (YYYY-MM-DD HH:MM[:ss[.uuuuuu]][TZ])
            datetime = f'{datetime[:4]}-{datetime[4:6]}-{datetime[6:8]} {datetime[9:11]}:{datetime[11:13]}:{datetime[13:15]}'

            well = find_monitoring_well(well_nr)
            photo_path = f'{photo_folder_path}\{jpg}'
            print(jpg)

            # Open the .jpg file in binary mode
            with open(photo_path, "rb") as img_file:

                file_name = os.path.basename(photo_path)
                picture = Picture.objects.create(
                    groundwater_monitoring_well_static=well,
                    recording_datetime=datetime,
                    picture=File(img_file, name=file_name),
                    description="Foto's inspoelen",
                    )
                           
            

            # Create a Picture instance and assign the binary data
            # picture = Picture(
            #     groundwater_monitoring_well_static = well,
            #     recording_datetime=datetime,
            #     picture=binary_data,
            #     description="Foto's inspoelen",
            # )

            picture.save()

            print(f"Image {jpg} saved successfully as binary data.")
            print("")

        

        print('start listing pictures')

        picture_data = []
        pictures = Picture.objects.all()


        # for picture in pictures:
        #     if picture.picture:
        #         picture.image_base64 = b64encode(picture.picture).decode('ascii')





            # print(binary_image_path)
            # print(binary_image_path_2)
            # print(len(photo_path))
            # print(len(binary_image_path))
            # print(len(binary_image_path_2))
            # binary_test = jpg_to_binary (photo_path)
            # print(photo_path)
            # print(binary_image_path)
            # print(len(binary_image_path))
            # print(list(binary_image_path[:10]))

            # print(len(bytes(str(list(binary_image_path)), 'utf-8')))

# print(foto)
# print(put)
# print(buis)
# print(datetime) 


# print('')