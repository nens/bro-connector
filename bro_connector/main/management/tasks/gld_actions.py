from gld.models import GroundwaterLevelDossier
from gmw.models import GroundwaterMonitoringTubeStatic
import os
import reversion

from main.settings.base import gld_SETTINGS

demo = gld_SETTINGS["demo"]
if demo:
    bro_info = gld_SETTINGS["bro_info_demo"]
else:
    bro_info = gld_SETTINGS["bro_info_bro_connector"]

folders = ["./additions/", "./startregistrations/"]
monitoringnetworks = gld_SETTINGS["monitoringnetworks"]


def create_registrations_folder():
    for folder in folders:
        # Check if the folder already exists
        if not os.path.exists(folder):
            try:
                # Create the folder if it doesn't exist
                os.mkdir(folder)
                print(f"Folder '{folder}' created successfully.")
            except OSError:
                print(f"Creation of the folder '{folder}' failed.")
        else:
            print(f"Folder '{folder}' already exists.")


def check_and_deliver(dossier: GroundwaterLevelDossier) -> None:
    pass


def check_status(dossier: GroundwaterLevelDossier) -> None:
    pass
