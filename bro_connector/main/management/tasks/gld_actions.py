from gld.models import GroundwaterLevelDossier, gld_registration_log
from gmw.models import GroundwaterMonitoringTubeStatic
import os
import reversion

from main.management.commands import gld_registrations_create

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

    create_registrations_folder()

    gld = gld_registrations_create.GldSyncHandler(gld_SETTINGS)

    tube = dossier.groundwater_monitoring_tube
    well = tube.groundwater_monitoring_well_static
    # Handle start registrations
    tube_id = tube.tube_number

    # Ignore filters that should not be delivered to BRO
    if tube.deliver_gld_to_bro == False:
        print(tube.deliver_gld_to_bro)
        return

    # Check if there is already a registration for this tube
    if not gld_registration_log.objects.filter(
        gwm_bro_id=well.bro_id,
        filter_id=tube_id,
        quality_regime=well.quality_regime,
    ).exists():
        print("log does not exist.")
        # There is not a GLD registration object with this configuration
        # Create a new configuration by creating startregistration sourcedocs
        # By creating the sourcedocs (or failng to do so), a registration is made in the database
        # This registration is used to track the progress of the delivery in further steps

        gld.create_start_registration_sourcedocs(
            well.quality_regime,
            str(well.delivery_accountable_party),
            well.bro_id,
            tube_id,
            well.nitg_code,
            monitoringnetworks,
        )

    print("check existing")
    gld.check_existing_startregistrations()


def check_status(dossier: GroundwaterLevelDossier) -> None:
    pass
