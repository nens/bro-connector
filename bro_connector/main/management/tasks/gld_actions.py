from gld.models import GroundwaterLevelDossier, gld_registration_log, gld_addition_log, Observation
import os
import logging

from main.management.commands import gld_sync_to_bro


from main.settings.base import gld_SETTINGS

logger = logging.getLogger(__name__)

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


def handle_start_registrations(
    dossier: GroundwaterLevelDossier,
    deliver: bool,
) -> None:
    
    well = dossier.groundwater_monitoring_tube.groundwater_monitoring_well_static
    # Handle start registrations
    tube_number = dossier.groundwater_monitoring_tube.tube_number

    gld = gld_sync_to_bro.GldSyncHandler(gld_SETTINGS)

    gld_registration_logs = gld_registration_log.objects.filter(
        gwm_bro_id=well.bro_id,
        filter_id=tube_number,
        quality_regime=well.quality_regime,
    )

    # Check if there is already a registration for this tube
    if not gld_registration_logs.exists():
        # There is not a GLD registration object with this configuration
        # Create a new configuration by creating startregistration sourcedocs
        # By creating the sourcedocs (or failng to do so), a registration is made in the database
        # This registration is used to track the progress of the delivery in further steps
        if deliver:
            # Only if the deliver function is used, a new start registration should be created
            # Otherwise, only existing registrations should be checked.
            gld.create_start_registration_sourcedocs(
                well,
                tube_number,
                monitoringnetworks,
            )

    gld.check_existing_startregistrations(gld_registration_logs)

def handle_additions(
        dossier: GroundwaterLevelDossier, 
        deliver: bool
    ):
    # Get observations
    observations = Observation.objects.filter(
        groundwater_level_dossier = dossier,
        observation_endtime__isnull = False
    )

    gld = gld_sync_to_bro.GldSyncHandler(gld_SETTINGS)

    for observation in observations:
        print(f"Observation: {observation}; End_date: {observation.observation_endtime}")
        addition_log = gld_addition_log.objects.filter(
            observation_id = observation.observation_id,
        ).first()

        if deliver:
            if not addition_log:
                (addition_log, created) = gld.create_addition_sourcedocuments_for_observation(observation)

            elif (
                addition_log.process_status == "failed_to_create_source_document"
                or addition_log.process_status == "source_document_validation_failed"
            ):
                # If the previous failed to create, or if the validation failed, try to regenerate.
                (addition_log, created) = gld.create_addition_sourcedocuments_for_observation(observation)
            
            elif (
                observation.up_to_date_in_bro == False
            ):
                #(addition_log) = gld.create_replace_sourcedocuments(observation)
                pass

            gld.gld_validate_and_deliver(addition_log)

        if not addition_log:
            logger.error(f"Tried to check status for Observation ({observation}), but no addition log exists. Generate an addition log first. ")
            continue
        
        if addition_log.process_status == "delivery_approved":
            logger.info(f"Delivery already approved (DOORGELEVERD): {addition_log}")
            continue
        
        status = gld.check_status_gld_addition(addition_log)
            

        
    
    return


def check_and_deliver(dossier: GroundwaterLevelDossier) -> None:

    create_registrations_folder()

    tube = dossier.groundwater_monitoring_tube
    # Ignore filters that should not be delivered to BRO
    if tube.deliver_gld_to_bro == False:
        print(tube.deliver_gld_to_bro)
        return
    
    handle_start_registrations(dossier, deliver=True)

    handle_additions(dossier, deliver=True)


def check_status(dossier: GroundwaterLevelDossier) -> None:
    tube = dossier.groundwater_monitoring_tube
    # Ignore filters that should not be delivered to BRO
    if tube.deliver_gld_to_bro == False:
        print(tube.deliver_gld_to_bro)
        return
    
    handle_start_registrations(dossier, deliver=False)

    handle_additions(dossier, deliver=False)
    
