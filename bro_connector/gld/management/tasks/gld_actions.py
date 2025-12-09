import logging
import os
import time

from gld.management.commands import gld_sync_to_bro
from gld.models import (
    GroundwaterLevelDossier,
    Observation,
    gld_addition_log,
    gld_registration_log,
)
from main.settings.base import ENV

logger = logging.getLogger(__name__)

folders = ["./additions/", "./startregistrations/"]


def is_demo():
    if ENV == "production":
        return False
    return True


def is_broid(bro_id: str) -> bool:
    """
    Check if the given bro_id is a valid BRO ID.
    """
    if bro_id:
        return (
            bro_id.startswith(("GMW", "GMN", "GLD", "FRD"))
            and len(bro_id) == 15
            and bro_id[3:].isdigit()
        )

    return False


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
    logger.info(
        f"Handling start registrations for dossier {dossier.groundwater_level_dossier_id}"
    )
    # Handle start registrations
    delivery_type = "register" if dossier.correction_reason is None else "replace"

    gld = gld_sync_to_bro.GldSyncHandler()

    gld_registration_logs = gld_registration_log.objects.filter(
        gmw_bro_id=dossier.gmw_bro_id,
        filter_number=dossier.tube_number,
        quality_regime=dossier.quality_regime,
        delivery_type=delivery_type,
    )
    logger.info(
        f"Found {gld_registration_logs.count()} existing registration logs for: {dossier.gmw_bro_id}-{dossier.tube_number}- {dossier.quality_regime}-{delivery_type}"
    )

    # Check if there is already a registration for this tube
    if not gld_registration_logs.exists():
        # There is not a GLD registration object with this configuration
        # Create a new configuration by creating startregistration sourcedocs
        # By creating the sourcedocs (or failng to do so), a registration is made in the database
        # This registration is used to track the progress of the delivery in further steps
        if deliver and not dossier.gld_bro_id or delivery_type == "replace":
            gld._set_bro_info(dossier.groundwater_monitoring_tube.groundwater_monitoring_well_static)
            # Only if the deliver function is used, a new start registration should be created
            # Otherwise, only existing registrations should be checked.
            registration = gld.create_start_registration_sourcedocs(
                dossier
            )
            logger.info(f"Registration created: {registration}")
            registration.validate_sourcedocument()
            registration.deliver_sourcedocument()

        elif dossier.gld_bro_id:
            gld_registration_log.objects.update_or_create(
                gmw_bro_id=dossier.gmw_bro_id,
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
        logger.info(f"Checking existing start registration: {log}")
        gld.check_existing_startregistrations(log)


def form_addition_type(observation: Observation) -> str:
    if observation.observation_type == "controlemeting":
        return "controlemeting"

    if observation.observation_metadata.status == "voorlopig":
        return f"regulier_{observation.observation_metadata.status}"
    return f"regulier_{observation.observation_metadata.status}"


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

        if addition_log:
            if addition_log.process_status == "delivery_approved":
                logger.info(f"Delivery already approved (DOORGELEVERD): {addition_log}")
                continue

            gld.check_status_gld_addition(addition_log)
        else:
            logger.error(
                f"Tried to check status for Observation ({observation}), but no addition log exists. Generate an addition log first. "
            )

    return


def check_and_deliver_start(dossier: GroundwaterLevelDossier) -> None:
    tube = dossier.groundwater_monitoring_tube
    # Ignore filters that should not be delivered to BRO
    if tube.deliver_gld_to_bro is False:
        print(f"deliver tube to BRO: {tube.deliver_gld_to_bro}")
        return

    if not tube.groundwater_monitoring_well_static.bro_id:
        print(
            f"No BRO ID for well {tube.groundwater_monitoring_tube_static_id}. Skipping dossier {dossier.groundwater_level_dossier_id}"
        )
        return

    # Create GLD Registration Log
    print(f"Check and deliver for dossier {dossier.groundwater_level_dossier_id}")
    if is_broid(dossier.gld_bro_id) and dossier.correction_reason is None:
        gld_start_registration = gld_registration_log.objects.update_or_create(
            gmw_bro_id=dossier.gmw_bro_id,
            gld_bro_id=dossier.gld_bro_id,
            filter_number=dossier.tube_number,
            quality_regime=dossier.quality_regime
            if dossier.quality_regime
            else dossier.groundwater_monitoring_tube.groundwater_monitoring_well_static.quality_regime,
            defaults=dict(
                validation_status="VALID",
                delivery_id=None,
                delivery_type="register",
                delivery_status="OPGENOMEN_LVBRO",
                comments="Imported into BRO-Connector.",
            ),
        )[0]
    else:
        delivery_type = "register" if dossier.correction_reason is None else "replace"
        gld_start_registration = gld_registration_log.objects.update_or_create(
            gmw_bro_id=dossier.gmw_bro_id,
            gld_bro_id=dossier.gld_bro_id,
            filter_number=dossier.tube_number,
            delivery_type=delivery_type,
            quality_regime=dossier.quality_regime
            if dossier.quality_regime
            else dossier.groundwater_monitoring_tube.groundwater_monitoring_well_static.quality_regime,
        )[0]

        logger.info(f"Check and deliver; Log created: {gld_start_registration}")

        gld_start_registration.generate_sourcedocument()
        logger.info(f"Check and deliver; File generated: {gld_start_registration.file}")

        gld_start_registration.validate_sourcedocument()
        logger.info(
            f"Check and deliver; File validated: {gld_start_registration.validation_status}"
        )

        gld_start_registration.deliver_sourcedocument()
        logger.info(
            f"Check and deliver; File delivered: {gld_start_registration.delivery_id} {gld_start_registration.delivery_status}"
        )

    # Sleep for 0.3 seconds to avoid overwhelming the server
    time.sleep(0.3)


def check_and_deliver_start_registrations(dossier: GroundwaterLevelDossier) -> None:
    start_log = gld_registration_log.objects.get(
        gmw_bro_id=dossier.gmw_bro_id,
        gld_bro_id=dossier.gld_bro_id,
        filter_number=dossier.tube_number,
        quality_regime=dossier.quality_regime
        if dossier.quality_regime
        else dossier.groundwater_monitoring_tube.groundwater_monitoring_well_static.quality_regime,
    )
    start_log.check_delivery_status()


def check_and_deliver_additions(dossier: GroundwaterLevelDossier) -> None:
    for observation in dossier.observation.filter(
        up_to_date_in_bro=False, result_time__isnull=False
    ):
        addition_log = gld_addition_log.objects.update_or_create(
            broid_registration=dossier.gld_bro_id,
            observation=observation,
            addition_type=observation.addition_type,
        )[0]

        logger.info(f"Check and deliver; Log created: {addition_log}")

        addition_log.generate_sourcedocument()
        logger.info(f"Check and deliver; File generated: {addition_log.file}")
        if addition_log.process_status == "failed_to_create_source_document":
            logger.error(
                f"Check and deliver; File generation failed: {addition_log.comments}"
            )
            return

        addition_log.validate_sourcedocument()
        logger.info(
            f"Check and deliver; File validated: {addition_log.validation_status}"
        )
        if addition_log.process_status == "source_document_validation_failed":
            logger.error(
                f"Check and deliver; File generation failed: {addition_log.comments}"
            )
            return

        addition_log.deliver_sourcedocument()
        logger.info(
            f"Check and deliver; File delivered: {addition_log.delivery_id} {addition_log.delivery_status}"
        )
        if addition_log.process_status == "source_document_validation_failed":
            logger.error(
                f"Check and deliver; File generation failed: {addition_log.comments}"
            )
            return

    # Sleep for 1 seconds to avoid overwhelming the server
    time.sleep(1)


def check_status(dossier: GroundwaterLevelDossier) -> None:
    tube = dossier.groundwater_monitoring_tube
    # Ignore filters that should not be delivered to BRO
    if tube.deliver_gld_to_bro is False:
        print(tube.deliver_gld_to_bro)
        return

    logger.info(f"Check status for dossier {dossier.groundwater_level_dossier_id}")
    handle_start_registrations(dossier, deliver=False)

    handle_additions(dossier, deliver=False)
