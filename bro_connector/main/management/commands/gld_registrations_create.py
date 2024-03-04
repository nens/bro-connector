from django.core.management.base import BaseCommand
import bro_exchange as brx
import os
import datetime
import bisect

from main.settings.base import gld_SETTINGS
from gld import models
from gmw import models as gmw_models

failed_update_strings = ["failed_once", "failed_twice", "failed_thrice"]


def get_registration_process_status(registration_id):
    registration = models.gld_registration_log.objects.get(id=registration_id)
    process_status = registration.process_status
    return process_status


def get_registration_validation_status(registration_id):
    registration = models.gld_registration_log.objects.get(id=registration_id)
    validation_status = registration.validation_status
    return validation_status


class GldSyncHandler:
    def __init__(self, gld_settings):
        self.registrations_dir = gld_settings["startregistrations_dir"]
        self.demo = gld_settings["demo"]
        if self.demo:
            self.access_info = gld_settings["bro_info_demo"]
        else:
            self.access_info = gld_settings["bro_info_bro_connector"]

    def create_start_registration_sourcedocs(
        self,
        quality_regime,
        deliveryaccountableparty,
        broidgmw,
        filtrnr,
        locationcode,  # nitg code
        monitoringnetworks,
    ):
        """
        Try to create startregistration sourcedocuments for a well/tube/quality regime
        Startregistration requests are saved to .xml file in startregistrations folder
        """

        try:
            monitoringpoints = [{"broId": broidgmw, "tubeNumber": filtrnr}]

            if monitoringnetworks == None:
                srcdocdata = {
                    "objectIdAccountableParty": locationcode + str(filtrnr),
                    "monitoringPoints": monitoringpoints,
                }
            else:
                srcdocdata = {
                    "objectIdAccountableParty": locationcode + str(filtrnr),
                    "groundwaterMonitoringNets": monitoringnetworks,  #
                    "monitoringPoints": monitoringpoints,
                }

            request_reference = "GLD_StartRegistration_{}_tube_{}".format(
                broidgmw, str(filtrnr)
            )
            gld_startregistration_request = brx.gld_registration_request(
                srcdoc="GLD_StartRegistration",
                requestReference=request_reference,
                deliveryAccountableParty=deliveryaccountableparty,
                qualityRegime=quality_regime,
                srcdocdata=srcdocdata,
            )

            filename = request_reference + ".xml"
            gld_startregistration_request.generate()
            gld_startregistration_request.write_request(
                output_dir=self.registrations_dir, filename=filename
            )

            process_status = "succesfully_generated_startregistration_request"
            record, created = models.gld_registration_log.objects.update_or_create(
                gwm_bro_id=broidgmw,
                filter_id=filtrnr,
                quality_regime=quality_regime,
                defaults=dict(
                    comments="Succesfully generated startregistration request",
                    date_modified=datetime.datetime.now(),
                    validation_status=None,
                    process_status=process_status,
                    file=filename,
                ),
            )

        except Exception as e:
            process_status = "failed_to_generate_source_documents"
            record, created = models.gld_registration_log.objects.update_or_create(
                gwm_bro_id=broidgmw,
                filter_id=filtrnr,
                quality_regime=quality_regime,
                defaults=dict(
                    comments="Failed to create startregistration source document: {}".format(
                        e
                    ),
                    date_modified=datetime.datetime.now(),
                    process_status=process_status,
                ),
            )

    def validate_gld_startregistration_request(self, start_registration_id):
        """
        Validate generated startregistration sourcedocuments
        """

        try:
            gld_registration = models.gld_registration_log.objects.get(
                id=start_registration_id
            )
            file = gld_registration.file
            source_doc_file = os.path.join(self.registrations_dir, file)
            payload = open(source_doc_file)

            if gld_SETTINGS["api_version"] == "v2":
                validation_info = brx.validate_sourcedoc(
                    payload, bro_info=self.access_info, demo=self.demo, api="v2"
                )

            else:
                validation_info = brx.validate_sourcedoc(
                    payload, bro_info=self.access_info, demo=self.demo
                )

            validation_status = validation_info["status"]

            if "errors" in validation_info:
                validation_errors = validation_info["errors"]
                comments = (
                    "Validated startregistration document, found errors: {}".format(
                        validation_errors
                    )
                )

                record, created = models.gld_registration_log.objects.update_or_create(
                    id=start_registration_id,
                    defaults=dict(
                        comments="Startregistration document is invalid, {}".format(
                            validation_errors
                        ),
                        validation_status=validation_status,
                        process_status="source_document_validation_succesful",
                    ),
                )

            else:
                comments = "Succesfully validated sourcedocument, no errors"
                record, created = models.gld_registration_log.objects.update_or_create(
                    id=start_registration_id,
                    defaults=dict(
                        # date_modified = datetime.datetime.now(),
                        comments=comments,
                        validation_status=validation_status,
                        process_status="source_document_validation_succesful",
                    ),
                )

        except Exception as e:
            process_status = "failed_to_validate_sourcedocument"
            comments = (
                "Exception occured during validation of sourcedocuments: {}".format(e)
            )
            record, created = models.gld_registration_log.objects.update_or_create(
                id=start_registration_id,
                defaults=dict(comments=comments, process_status=process_status),
            )

    def deliver_startregistration_sourcedocuments(self, start_registration_id):
        """
        Deliver generated startregistration sourcedoc to the BRO
        """

        # Get the registration
        gld_registration = models.gld_registration_log.objects.get(
            id=start_registration_id
        )

        # If the delivery fails, use the this to indicate how many attempts were made
        delivery_status = gld_registration.levering_status
        if delivery_status is None:
            delivery_status_update = "failed_once"
        else:
            position = bisect.bisect_left(failed_update_strings, delivery_status)
            delivery_status_update = failed_update_strings[position + 1]

        try:
            file = gld_registration.file
            source_doc_file = os.path.join(self.registrations_dir, file)
            payload = open(source_doc_file)
            request = {file: payload}

            if gld_SETTINGS["api_version"] == "v2":
                upload_info = brx.upload_sourcedocs_from_dict(
                    request,
                    self.access_info,
                    api="v2",
                    project_id=self.access_info["projectnummer"],
                    demo=self.demo,
                )
            else:
                upload_info = brx.upload_sourcedocs_from_dict(
                    request, self.access_info, demo=self.demo
                )

            if upload_info == "Error":
                comments = "Error occured during delivery of sourcedocument"
                models.gld_registration_log.objects.update_or_create(
                    id=start_registration_id,
                    defaults={
                        "date_modified": datetime.datetime.now(),
                        "comments": comments,
                        "levering_status": delivery_status_update,
                        "process_status": "failed_to_deliver_sourcedocuments",
                    },
                )
            else:
                levering_id = upload_info.json()["identifier"]
                delivery_status = upload_info.json()["status"]
                lastchanged = upload_info.json()["lastChanged"]
                comments = "Succesfully delivered startregistration sourcedocument"

                models.gld_registration_log.objects.update_or_create(
                    id=start_registration_id,
                    defaults={
                        "date_modified": datetime.datetime.now(),
                        "comments": comments,
                        "levering_status": delivery_status,
                        "lastchanged": lastchanged,
                        "levering_id": levering_id,
                        "process_status": "succesfully_delivered_sourcedocuments",
                    },
                )

        except Exception as e:
            comments = "Exception occured during delivery of startregistration sourcedocument: {}".format(
                e
            )
            models.gld_registration_log.objects.update_or_create(
                id=start_registration_id,
                defaults={
                    "date_modified": datetime.datetime.now(),
                    "comments": comments,
                    "levering_status": delivery_status_update,
                    "process_status": "failed_to_deliver_sourcedocuments",
                },
            )

    def check_delivery_status_levering(self, registration_id):
        """
        Check the status of a startregistration delivery
        Logs the status of the delivery in the database
        If delivery is approved, a GroundwaterLevelDossier object is created
        This means the startregistration process is concluded

        Parameters
        ----------
        registration_id : int
            unique id of the gld registration in the database.

        Returns
        -------
        None.

        """

        registration = models.gld_registration_log.objects.get(id=registration_id)
        levering_id = registration.levering_id

        try:
            if gld_SETTINGS["api_version"] == "v2":
                upload_info = brx.check_delivery_status(
                    levering_id,
                    self.access_info,
                    api="v2",
                    project_id=self.access_info["projectnummer"],
                    demo=self.demo,
                )
            else:
                upload_info = brx.check_delivery_status(
                    levering_id, self.access_info, demo=self.demo
                )

            if (
                upload_info.json()["status"] == "DOORGELEVERD"
                and upload_info.json()["brondocuments"][0]["status"]
                == "OPGENOMEN_LVBRO"
            ):
                record, created = models.gld_registration_log.objects.update_or_create(
                    id=registration_id,
                    defaults=dict(
                        gld_bro_id=upload_info.json()["brondocuments"][0]["broId"],
                        levering_status=upload_info.json()["brondocuments"][0][
                            "status"
                        ],
                        last_changed=upload_info.json()["lastChanged"],
                        comments="Startregistration request approved",
                        process_status="delivery_approved",
                    ),
                )

                # Create new GroundWaterLevelDossier
                start_date_research = datetime.datetime.now().date().isoformat()
                (
                    record,
                    created,
                ) = models.GroundwaterLevelDossier.objects.update_or_create(
                    groundwater_monitoring_tube_id=registration.filter_id,
                    gmw_bro_id=registration.gwm_bro_id,
                    research_start_date=start_date_research,
                    gld_bro_id=upload_info.json()["brondocuments"][0]["broId"],
                )

                # Remove the sourcedocument file if delivery is approved
                file = registration.file
                source_doc_file = os.path.join(self.registrations_dir, file)
                os.remove(source_doc_file)

            else:
                record, created = models.gld_registration_log.objects.update_or_create(
                    id=registration_id,
                    defaults=dict(
                        levering_status=upload_info.json()["status"],
                        last_changed=upload_info.json()["lastChanged"],
                        comments="Startregistration request not yet approved",
                    ),
                )

        except Exception as e:
            record, created = models.gld_registration_log.objects.update_or_create(
                id=registration_id,
                defaults=dict(
                    comments="Error occured during status check of delivery: {}".format(
                        e
                    )
                ),
            )

    def create_sourcedocs_start_registrations(self, monitoringnetworks):
        """
        Run GLD start registrations for all monitoring wells in the database
        Start registrations has to be run multiple times to get all tubes registered
        This will not interfere with additions, as a check will be done on registration availibility
        """

        gwm_wells = gmw_models.GroundwaterMonitoringWellStatic.objects.all()
        # Loop over all GMW objects in the database
        for well in gwm_wells:
            # Ignore wells that are not (yet) delivered to BRO
            if well.deliver_gmw_to_bro == False:
                continue

            if self.demo == True:
                if well.bro_id != "GMW000000042583":
                    continue

            # Get some well properties
            quality_regime = "IMBRO"

            # Get all filters that are installed in this well
            tubes = gmw_models.GroundwaterMonitoringTubeStatic.objects.filter(
                groundwater_monitoring_well_id=well.groundwater_monitoring_well_static_id
            )

            # Loop over all filters within the well
            for tube in tubes:
                tube_id = tube.tube_number

                # Ignore filters that should not be delivered to BRO
                if tube.deliver_gld_to_bro == False:
                    continue

                # Check if there is already a registration for this tube
                if not models.gld_registration_log.objects.filter(
                    gwm_bro_id=well.bro_id,
                    filter_id=tube_id,
                    quality_regime=quality_regime,
                ).exists():
                    # There is not a GLD registration object with this configuration
                    # Create a new configuration by creating startregistration sourcedocs
                    # By creating the sourcedocs (or failng to do so), a registration is made in the database
                    # This registration is used to track the progress of the delivery in further steps

                    self.create_start_registration_sourcedocs(
                        quality_regime,
                        str(well.delivery_accountable_party),
                        well.bro_id,
                        tube_id,
                        well.nitg_code,
                        monitoringnetworks,
                    )

    def check_existing_startregistrations(
        self,
    ):
        """
        This function loops over all exists startregistrations in the database
        Depending on the status one of the following actions is carried out:
            - The sourcedocument for the startregistration is validated
            - The sourcedocument is delivered to the BRO
            - The status of a delivery is checked
            - If a delivery failed, it may be attempted again up to three times

        Parameters
        ----------
        None.

        Returns
        -------
        None.

        """
        # Get all the current registrations
        gld_registrations = models.gld_registration_log.objects.all()

        for registration in gld_registrations:
            # We check the status of the registration and either validate/deliver/check status/do nothing
            registration_id = registration.id

            if (
                get_registration_process_status(registration_id)
                == "succesfully_delivered_sourcedocuments"
                and registration.levering_status != "OPGENOMEN_LVBRO"
                and registration.levering_id is not None
            ):
                # The registration has been delivered, but not yet approved
                self.check_delivery_status_levering(registration_id)

            else:
                # Succesfully generated a startregistration sourcedoc in the previous step
                # Validate the created sourcedocument
                if (
                    get_registration_process_status(registration_id)
                    == "succesfully_generated_startregistration_request"
                ):
                    self.validate_gld_startregistration_request(registration_id)

                # If an error occured during validation, try again
                # Failed to validate sourcedocument doesn't mean the document is valid/invalid
                # It means something went wrong during validation (e.g BRO server error)
                # Even if a document is invalid, the validation process has succeeded and won't be reattempted
                if (
                    get_registration_process_status(registration_id)
                    == "failed_to_validate_sourcedocument"
                ):
                    # If we failed to validate the sourcedocument, try again
                    # TODO maybe limit amount of retries? Do not expect validation to fail multiple times..
                    self.validate_gld_startregistration_request(registration_id)

                # If validation is succesful and the document is valid, try a delivery
                if (
                    get_registration_process_status(registration_id)
                    == "source_document_validation_succesful"
                    and get_registration_validation_status(registration_id) == "VALIDE"
                ):
                    self.deliver_startregistration_sourcedocuments(registration_id)

                # If delivery is succesful, check the status of the delivery
                if (
                    get_registration_process_status(registration_id)
                    == "succesfully_delivered_sourcedocuments"
                    and registration.levering_status != "OPGENOMEN_LVBRO"
                    and registration.levering_id is not None
                ):
                    # The registration has been delivered, but not yet approved
                    self.check_delivery_status_levering(registration_id)

                # If the delivery failed previously, we can retry
                if (
                    get_registration_process_status(registration_id)
                    == "failed_to_deliver_sourcedocuments"
                ):
                    # This will not be the case on the first try
                    if registration.levering_status == "failed_thrice":
                        # TODO report with mail?
                        continue
                    else:
                        self.deliver_startregistration_sourcedocuments(registration.id)


class Command(BaseCommand):
    help = """Custom command for import of GIS data."""

    def handle(self, *args, **options):
        demo = gld_SETTINGS["demo"]
        if demo:
            access_info = gld_SETTINGS["bro_info_demo"]
        else:
            access_info = gld_SETTINGS["bro_info_bro_connector"]

        monitoringnetworks = gld_SETTINGS["monitoringnetworks"]

        gld = GldSyncHandler(gld_SETTINGS)

        # Check the database for new wells/tubes and start a GLD registration for these objects if its it needed
        gld.create_sourcedocs_start_registrations(monitoringnetworks)

        # print('check status')
        # Check existing registrations
        gld.check_existing_startregistrations()
