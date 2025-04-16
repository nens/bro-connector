from gld.models import (
    GroundwaterLevelDossier,
    gld_registration_log,
    gld_addition_log,
    Observation,
)
import os
import logging

from gld.management.commands import gld_sync_to_bro

from main.settings.base import env

logger = logging.getLogger(__name__)

folders = ["./additions/", "./startregistrations/"]


def is_demo():
    if env == "production":
        return False
    return True


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

    gld = gld_sync_to_bro.GldSyncHandler()

    gld_registration_logs = gld_registration_log.objects.filter(
        gwm_bro_id=well.bro_id,
        filter_number=tube_number,
        quality_regime=well.quality_regime,
    )

    # Check if there is already a registration for this tube
    if not gld_registration_logs.exists():
        # There is not a GLD registration object with this configuration
        # Create a new configuration by creating startregistration sourcedocs
        # By creating the sourcedocs (or failng to do so), a registration is made in the database
        # This registration is used to track the progress of the delivery in further steps
        if deliver and not dossier.gld_bro_id:
            gld._set_bro_info(well)
            # Only if the deliver function is used, a new start registration should be created
            # Otherwise, only existing registrations should be checked.
            registration = gld.create_start_registration_sourcedocs(
                well,
                tube_number,
            )
            gld.deliver_startregistration_sourcedocuments(registration)

        elif dossier.gld_bro_id:
            gld_registration_log.objects.update_or_create(
                gwm_bro_id=dossier.gmw_bro_id,
                gld_bro_id=dossier.gld_bro_id,
                filter_number=dossier.tube_number,
                validation_status="VALID",
                delivery_id=None,
                delivery_type="register",
                delivery_status="OPGENOMEN_LVBRO",
                comments="Imported into BRO-Connector.",
                quality_regime=dossier.groundwater_monitoring_tube.groundwater_monitoring_well_static.quality_regime,
            )

    for log in gld_registration_logs:
        gld.check_existing_startregistrations(log)


def form_addition_type(observation: Observation) -> str:
    if observation.observation_type == "controlemeting":
        return "controlemeting"

    if observation.validation_status == "voorlopig":
        return f"regulier_{observation.validation_status}"
    return f"regulier_{observation.validation_status}"


def handle_additions(dossier: GroundwaterLevelDossier, deliver: bool):
    print("handle additions function")
    # Get observations
    observations = Observation.objects.filter(
        groundwater_level_dossier=dossier,
        observation_endtime__isnull=False,
        # Up to date BRO is False
    )

    gld = gld_sync_to_bro.GldSyncHandler()

    for observation in observations:
        print(
            f"Observation: {observation}; End_date: {observation.observation_endtime}"
        )

        addition_log = gld_addition_log.objects.filter(
            observation_id=observation.observation_id,
            addition_type=form_addition_type(observation),
        ).first()

        print(observation)
        print(addition_log)

        well = observation.groundwater_level_dossier.groundwater_monitoring_tube.groundwater_monitoring_well_static
        gld._set_bro_info(well)

        if deliver:
            if not addition_log:
                # STEP 1: Create the document
                logger.info("Creating new sourcedocument as no addition_log existed.")
                (addition_log, created) = (
                    gld.create_addition_sourcedocuments_for_observation(observation)
                )

                if addition_log:
                    # STEP 2: Validate the document
                    validation_status = gld.validate_addition(addition_log)
                    logger.info(f"Validation resulted in: {validation_status}")

                    # STEP 3: Deliver
                    logger.info("Delivering addition")
                    gld.deliver_addition(addition_log)

            elif (
                addition_log.process_status == "failed_to_create_source_document"
                or addition_log.process_status == "source_document_validation_failed"
            ):
                # If the previous failed to create, or if the validation failed, try to regenerate.
                (addition_log, created) = (
                    gld.create_addition_sourcedocuments_for_observation(observation)
                )

            elif observation.up_to_date_in_bro is False:
                # (addition_log) = gld.create_replace_sourcedocuments(observation)
                pass

            else:
                gld.gld_validate_and_deliver(addition_log)

            if not addition_log:
                logger.error(
                    f"Tried to create addition document for Observation ({observation}), and validate and deliver, but this was not possible."
                )
                continue

        if not addition_log:
            logger.error(
                f"Tried to check status for Observation ({observation}), but no addition log exists. Generate an addition log first. "
            )
            continue

        if addition_log.process_status == "delivery_approved":
            logger.info(f"Delivery already approved (DOORGELEVERD): {addition_log}")
            continue

        gld.check_status_gld_addition(addition_log)

    return


def check_and_deliver(dossier: GroundwaterLevelDossier) -> None:
    create_registrations_folder()

    tube = dossier.groundwater_monitoring_tube
    # Ignore filters that should not be delivered to BRO
    if tube.deliver_gld_to_bro is False:
        print(f"deliver tube to BRO: {tube.deliver_gld_to_bro}")
        return

    handle_start_registrations(dossier, deliver=True)

    handle_additions(dossier, deliver=True)


def check_status(dossier: GroundwaterLevelDossier) -> None:
    tube = dossier.groundwater_monitoring_tube
    # Ignore filters that should not be delivered to BRO
    if tube.deliver_gld_to_bro is False:
        print(tube.deliver_gld_to_bro)
        return

    handle_start_registrations(dossier, deliver=False)

    handle_additions(dossier, deliver=False)
