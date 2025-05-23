from django.core.management.base import BaseCommand
import bro_exchange as brx
import os
import datetime
import bisect
import reversion
import uuid
from xml.etree import ElementTree as ET
from copy import deepcopy
from main.settings.base import ENV

from django.apps import apps
from gld import models
from gmw.models import GroundwaterMonitoringWellStatic
from bro.models import Organisation

import logging

logger = logging.getLogger(__name__)

app_config = apps.get_app_config("gld")
REGISTRATIONS_DIR = os.path.join(app_config.path, "startregistrations")
ADDITION_DIR = os.path.join(app_config.path, "additions")

failed_update_strings = ["failed_once", "failed_twice", "failed_thrice"]
field_value_division_dict = {"cm": 100, "mm": 1000, "m": 1}


def get_registration_process_status(registration: models.gld_registration_log) -> str:
    process_status = registration.process_status
    return process_status


def registration_is_valid(registration: models.gld_registration_log) -> bool:
    validation_status = registration.validation_status
    return validation_status == "VALIDE"


def convert_value_to_meter(measurement: models.MeasurementTvp) -> models.MeasurementTvp:
    waterstand_waarde = float(measurement.field_value)
    waterstand_waarde_converted = (
        waterstand_waarde / field_value_division_dict[measurement.field_value_unit]
    )

    with reversion.create_revision():
        measurement.calculated_value = waterstand_waarde_converted
        measurement.save()

        reversion.set_comment("Calculated the measurment value (conversion to m).")

    return measurement


def order_measurements_list(measurement_list: list):
    datetime_values = [
        datetime.datetime.fromisoformat(tvp["time"]) for tvp in measurement_list
    ]
    datetime_ordered = sorted(datetime_values)
    indices = [
        datetime_values.index(datetime_value) for datetime_value in datetime_ordered
    ]

    measurement_list_ordered = []
    for index in indices:
        measurement_list_ordered.append(measurement_list[index])

    # print(measurement_list_ordered)
    return measurement_list_ordered


def get_measurement_point_metadata_for_measurement(
    measurement_point_metadata: models.MeasurementPointMetadata,
):
    metadata = {
        "StatusQualityControl": measurement_point_metadata.status_quality_control,
        "interpolationType": "Discontinuous",
    }
    if measurement_point_metadata.censor_reason:
        metadata["censoredReason"] = measurement_point_metadata.censor_reason

    return metadata


def get_timeseries_tvp_for_observation_id(observation: models.Observation):
    """
    Get all timeseries values between start and stop datetime, including metadata
    """
    # TODO checken of toegepaste filter/check werkt (of de measurement_list alleen de goedgekeurde waardes heeft)

    measurement_tvp = observation.measurement.all()
    measurements_list = []
    for measurement in measurement_tvp:
        metadata = get_measurement_point_metadata_for_measurement(
            measurement.measurement_point_metadata
        )

        # discard a measurement with quality control type 1 (afgekeurd)
        if metadata["StatusQualityControl"] == "afgekeurd":
            continue

        # If the measurement value  is None, this value must have been censored
        if measurement.field_value is None:
            if metadata["censoredReason"] is None:
                # We can't include a missing value without a censoring reason
                continue
        else:
            convert_value_to_meter(measurement)

        measurement_data = {
            "time": measurement.measurement_time.isoformat(),
            "value": measurement.calculated_value,
            "metadata": metadata,
        }

        measurements_list += [measurement_data]

    measurements_list_ordered = order_measurements_list(measurements_list)

    return measurements_list_ordered


def get_observation_procedure_data(
    observation_process: models.ObservationProcess, quality_regime
):
    """
    Get the procedure data for the observation
    This is unique for each observation
    """

    air_pressure_compensation_type = observation_process.air_pressure_compensation_type

    measurement_instrument_type = observation_process.measurement_instrument_type

    evaluation_procedure = observation_process.evaluation_procedure

    if quality_regime == "IMBRO":
        if (
            air_pressure_compensation_type is None
            or air_pressure_compensation_type == "onbekend"
        ):
            observation_procedure_data = {
                "evaluationProcedure": evaluation_procedure,
                "measurementInstrumentType": measurement_instrument_type,
            }
        else:
            observation_procedure_data = {
                "airPressureCompensationType": air_pressure_compensation_type,
                "evaluationProcedure": evaluation_procedure,
                "measurementInstrumentType": measurement_instrument_type,
            }
    else:
        observation_procedure_data = {
            "airPressureCompensationType": air_pressure_compensation_type,
            "evaluationProcedure": evaluation_procedure,
            "measurementInstrumentType": measurement_instrument_type,
        }

    return observation_procedure_data


def get_observation_gld_source_document_data(observation: models.Observation):
    """
    Generate the GLD addition sourcedocs, without result data
    """
    gld = observation.groundwater_level_dossier
    gmw_bro_id = gld.gmw_bro_id

    # Get the quality regime for the well
    gmw_well = GroundwaterMonitoringWellStatic.objects.get(bro_id=gmw_bro_id)
    quality_regime = gmw_well.quality_regime

    # Get the GLD registration id for this measurement timeseries
    # Check which parts of the observation have already been succesfully delivered

    # Get the observation metadata and procedure data
    observation_metadata_instance = observation.observation_metadata
    observation_status = observation.observation_metadata.status

    observation_metadata = {
        "observationType": observation_metadata_instance.observation_type,
        "principalInvestigator": observation_metadata_instance.responsible_party.company_number,
    }

    observation_procedure = get_observation_procedure_data(
        observation.observation_process, quality_regime
    )

    # Result time is the observation endtime
    if not observation.result_time:
        logger.error(
            "Result time is empty. First close the observation before delivering(?)"
        )
    observation_result_time = observation.result_time.astimezone().strftime(
        "%Y-%m-%dT%H:%M:%S%z"
    )
    print(observation_result_time)
    splited_time = observation_result_time.split("+")
    timezone = splited_time[-1]
    observation_result_time = f"{splited_time[0]}+{timezone[0:2]}:{timezone[2:4]}"

    # dateStamp becomes the date of the last observation in a chunk
    # Generate the addition type for the logging
    # Can be either 'controlemeting, 'regulier_voorlopig_beoordeeld' or 'regulier_volledig_beoordeeld'
    source_document_data = {
        "metadata": {"parameters": observation_metadata, "dateStamp": None},
        "procedure": {"parameters": observation_procedure},
        "resultTime": observation_result_time,
        "result": None,
    }
    if observation_metadata["observationType"] == "controlemeting":
        addition_type = "controlemeting"
    else:
        # Create the sourcedocs for the addition, results will later be added in chunks
        source_document_data["metadata"]["status"] = observation_status
        addition_type = "regulier_" + observation_status
    return source_document_data, addition_type


def get_gld_registration_data_for_observation(observation: models.Observation):
    """
    Each observation has a GLD id and GWM id
    When delivering the observations we get the GLD id from the observation
    We use the GWM id to get the quality regime for the well in which the measurement was taken
    """

    # Get the GLD bro id
    gld = observation.groundwater_level_dossier
    gld_bro_id = gld.gld_bro_id
    gmw_bro_id = gld.gmw_bro_id

    # Get the quality regime for the well
    # TODO quality regime changes, new well in database?
    gmw_well = GroundwaterMonitoringWellStatic.objects.get(bro_id=gmw_bro_id)
    quality_regime = gmw_well.quality_regime

    return gld_bro_id, quality_regime


def form_addition_type(observation: models.Observation) -> str:
    if observation.observation_type == "controlemeting":
        return "controlemeting"

    if observation.observation_metadata.status == "voorlopig":
        return f"regulier_{observation.observation_metadata.status}"
    return f"regulier_{observation.observation_metadata.status}"


def create_new_observations():
    """
    Add a new observation for every GLD that has no open observation
    An observation is open if it has no status. Once it has a status, it is
    (being) delivered to BRO and no new time-value pairs can be added.

    This function does not create the first observation of a GLD, this
    should be done manually because of connections with the metadata.
    """

    glds = models.GroundwaterLevelDossier.objects.all()
    for gld in glds:
        gld_id = gld.groundwater_level_dossier_id
        observations_per_gld = models.Observation.objects.filter(
            groundwater_level_dossier_id=gld_id
        )
        observation_status_per_gld = observations_per_gld.filter(status=None)

        # if there is no empty observation status, a new observation is needed
        if not observation_status_per_gld:
            # gather information about the previous observation
            try:
                previous_gld_observation = observations_per_gld.last()
                previous_observation_metadata_id = (
                    previous_gld_observation.observation_metadata_id
                )
                previous_observation_process_id = (
                    previous_gld_observation.observation_process_id
                )
            except Exception as e:
                logger.exception(e)
                print(
                    "No observations exist yet for GLD {}, please create an observation".format(
                        gld_id
                    )
                )
                continue
            # use the metadata id and process id from the previous observation
            new_observation = models.Observation(
                observation_starttime=datetime.datetime.utcnow().replace(
                    tzinfo=datetime.timezone.utc
                ),
                observation_metadata_id=previous_observation_metadata_id,
                observation_process_id=previous_observation_process_id,
                groundwater_level_dossier_id=gld_id,
            )
            new_observation.save()


def _get_token(owner: Organisation):
    return {
        "user": owner.bro_user,
        "pass": owner.bro_token,
    }


def form_bro_info(well: GroundwaterMonitoringWellStatic) -> dict:
    return {
        "token": _get_token(well.delivery_accountable_party),
        "projectnummer": well.project_number,
    }


def retrieve_responsible_kvk_from_observation(observation: models.Observation):
    return observation.groundwater_level_dossier.groundwater_monitoring_tube.groundwater_monitoring_well_static.delivery_accountable_party.company_number


def set_delivery_accountable_party(
    well: GroundwaterMonitoringWellStatic, demo: bool
) -> str:
    if demo:
        delivery_accountable_party = str(27376655)
    else:
        delivery_accountable_party = str(well.delivery_accountable_party.company_number)

    return delivery_accountable_party


class GldSyncHandler:
    def __init__(self):
        self.demo = self._is_demo()

        # Currently not yet dynamically implemented
        self.monitoringnetworks = None
        self.demo = self._is_demo()

    def _is_demo(self):
        if ENV == "production":
            return False
        return True

    def _set_bro_info(self, well: GroundwaterMonitoringWellStatic) -> None:
        self.bro_info = form_bro_info(well)

    def create_start_registration_sourcedocs(
        self,
        well: GroundwaterMonitoringWellStatic,
        filtrnr,
    ) -> models.gld_registration_log:
        """
        Try to create startregistration sourcedocuments for a well/tube/quality regime
        Startregistration requests are saved to .xml file in startregistrations folder
        """
        bro_id_gmw = well.bro_id
        internal_id = well.internal_id
        quality_regime = well.quality_regime
        delivery_accountable_party = set_delivery_accountable_party(
            well, self._is_demo()
        )
        print("Delivery accountable party: ", delivery_accountable_party)
        try:
            monitoringpoints = [{"broId": bro_id_gmw, "tubeNumber": filtrnr}]

            if self.monitoringnetworks is None:
                srcdocdata = {
                    "objectIdAccountableParty": f"{internal_id}{str(filtrnr)}",
                    "monitoringPoints": monitoringpoints,
                }
            else:
                srcdocdata = {
                    "objectIdAccountableParty": f"{internal_id}{str(filtrnr)}",
                    "groundwaterMonitoringNets": self.monitoringnetworks,  #
                    "monitoringPoints": monitoringpoints,
                }

            request_reference = "GLD_StartRegistration_{}_tube_{}".format(
                bro_id_gmw, str(filtrnr)
            )
            gld_startregistration_request = brx.gld_registration_request(
                srcdoc="GLD_StartRegistration",
                requestReference=request_reference,
                deliveryAccountableParty=delivery_accountable_party,
                qualityRegime=quality_regime,
                srcdocdata=srcdocdata,
            )

            filename = request_reference + ".xml"
            gld_startregistration_request.generate()
            gld_startregistration_request.write_request(
                output_dir=REGISTRATIONS_DIR, filename=filename
            )
            process_status = "succesfully_generated_startregistration_request"
            return models.gld_registration_log.objects.update_or_create(
                gmw_bro_id=bro_id_gmw,
                filter_number=filtrnr,
                quality_regime=quality_regime,
                defaults=dict(
                    comments="Succesfully generated startregistration request",
                    date_modified=datetime.datetime.now(),
                    validation_status=None,
                    process_status=process_status,
                    file=filename,
                ),
            )[0]

        except Exception as e:
            process_status = "failed_to_generate_source_documents"
            return models.gld_registration_log.objects.update_or_create(
                gmw_bro_id=bro_id_gmw,
                filter_number=filtrnr,
                quality_regime=quality_regime,
                defaults=dict(
                    comments="Failed to create startregistration source document: {}".format(
                        e
                    ),
                    date_modified=datetime.datetime.now(),
                    process_status=process_status,
                ),
            )[0]

    def validate_gld_startregistration_request(
        self, registration: models.gld_registration_log
    ):
        """
        Validate generated startregistration sourcedocuments
        """
        file = registration.file
        source_doc_file = os.path.join(REGISTRATIONS_DIR, file)
        payload = open(source_doc_file)

        try:
            validation_info = brx.validate_sourcedoc(
                payload, bro_info=self.bro_info, demo=self.demo, api="v2"
            )
        except Exception as e:
            validation_status = validation_info["status"]
            process_status = "failed_to_validate_sourcedocument"
            comments = (
                "Exception occured during validation of sourcedocuments: {}".format(e)
            )

        comments = "Succesfully validated sourcedocument, no errors"
        process_status = "source_document_validation_succesful"

        validation_status = validation_info["status"]  ## 401 = unauthorized
        if "errors" in validation_info:
            if len(validation_info["errors"]) > 0:
                comments = f"Validated startregistration document, found errors: {validation_info['errors']}"
            else:
                comments = "Succesfully validated sourcedocument, no errors"

        registration.comments = comments
        registration.process_status = process_status
        registration.validation_status = validation_status
        registration.save()

    def deliver_startregistration_sourcedocuments(
        self, registration: models.gld_registration_log
    ):
        """
        Deliver generated startregistration sourcedoc to the BRO
        """
        # If the delivery fails, use the this to indicate how many attempts were made
        delivery_status = registration.delivery_status
        if delivery_status is None:
            delivery_status_update = "failed_once"
        else:
            position = bisect.bisect_left(failed_update_strings, delivery_status)
            delivery_status_update = failed_update_strings[position + 1]

        try:
            file = registration.file
            source_doc_file = os.path.join(REGISTRATIONS_DIR, file)
            payload = open(source_doc_file)
            request = {file: payload}

            upload_info = brx.upload_sourcedocs_from_dict(
                request,
                token=self.bro_info["token"],
                api="v2",
                project_id=self.bro_info["projectnummer"],
                demo=self.demo,
            )

            if upload_info == "Error":
                comments = "Error occurred during delivery of sourcedocument"
                registration.date_modified = datetime.datetime.now()
                registration.comments = comments
                registration.delivery_status = delivery_status_update
                registration.process_status = "failed_to_deliver_sourcedocuments"
                registration.save()
            else:
                upload_data = upload_info.json()
                registration.date_modified = datetime.datetime.now()
                registration.comments = (
                    "Successfully delivered startregistration sourcedocument"
                )
                registration.delivery_status = upload_data["status"]
                registration.last_changed = upload_data["lastChanged"]
                registration.delivery_id = upload_data["identifier"]
                registration.process_status = "succesfully_delivered_sourcedocuments"
                registration.save()

        except Exception as e:
            comments = "Exception occured during delivery of startregistration sourcedocument: {}".format(
                e
            )
            registration.date_modified = datetime.datetime.now()
            registration.comments = comments
            registration.delivery_status = delivery_status_update
            registration.process_status = "failed_to_deliver_sourcedocuments"
            registration.save()

    def check_delivery_status_levering(self, registration: models.gld_registration_log):
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

        delivery_id = registration.delivery_id

        try:
            upload_info = brx.check_delivery_status(
                delivery_id,
                token=self.bro_info["token"],
                api="v2",
                project_id=self.bro_info["projectnummer"],
                demo=self.demo,
            )

            if (
                upload_info.json()["status"] == "DOORGELEVERD"
                and upload_info.json()["brondocuments"][0]["status"]
                == "OPGENOMEN_LVBRO"
            ):
                registration.gld_bro_id = upload_info.json()["brondocuments"][0][
                    "broId"
                ]
                registration.delivery_status = upload_info.json()["brondocuments"][0][
                    "status"
                ]
                registration.last_changed = upload_info.json()["lastChanged"]
                registration.comments = "Startregistration request approved"
                registration.process_status = "delivery_approved"
                registration.save()

                tube = models.GroundwaterMonitoringTubeStatic.objects.get(
                    groundwater_monitoring_well_static__bro_id=registration.gmw_bro_id,
                    tube_number=registration.filter_number,
                )
                gld = models.GroundwaterLevelDossier.objects.get(
                    groundwater_monitoring_tube=tube
                )
                gld.gld_bro_id = upload_info.json()["brondocuments"][0]["broId"]
                gld.save()

                # Remove the sourcedocument file if delivery is approved
                file = registration.file
                source_doc_file = os.path.join(REGISTRATIONS_DIR, file)
                os.remove(source_doc_file)

            else:
                registration.delivery_status = upload_info.json()["status"]
                registration.last_changed = upload_info.json()["lastChanged"]
                registration.comments = "Startregistration request not yet approved"
                registration.save()

        except Exception as e:
            comments = f"Error occured during status check of delivery: {e}.\n"
            registration.comments += comments
            registration.save()

    def handle_all_start_registrations(self):
        """
        Run GLD start registrations for all monitoring wells in the database
        Start registrations has to be run multiple times to get all tubes registered
        This will not interfere with additions, as a check will be done on registration availibility
        """

        gwm_wells = GroundwaterMonitoringWellStatic.objects.all()
        # Loop over all GMW objects in the database
        for well in gwm_wells:
            # Ignore wells that are not (yet) delivered to BRO
            if well.deliver_gmw_to_bro is False:
                continue

            # Get some well properties
            quality_regime = "IMBRO"  ## FIXME: derive from GLD

            # Loop over all filters within the well
            for tube in well.tube.all():
                tube_id = tube.tube_number

                # Ignore filters that should not be delivered to BRO
                if tube.deliver_gld_to_bro is False:
                    continue

                # Check if there is already a registration for this tube
                if not models.gld_registration_log.objects.filter(
                    gmw_bro_id=well.bro_id,
                    filter_number=tube_id,
                    quality_regime=quality_regime,
                ).exists():
                    # There is not a GLD registration object with this configuration
                    # Create a new configuration by creating startregistration sourcedocs
                    # By creating the sourcedocs (or failng to do so), a registration is made in the database
                    # This registration is used to track the progress of the delivery in further steps
                    # Check if a GLD already has a start registration
                    gld = models.GroundwaterLevelDossier.objects.get(
                        groundwater_monitoring_tube=tube
                    )

                    if gld.gld_bro_id:
                        models.gld_registration_log.objects.get_or_create(
                            gmw_bro_id=gld.gmw_bro_id,
                            gld_bro_id=gld.gld_bro_id,
                            filter_number=gld.tube_number,
                            delivery_type="register",
                            defaults=dict(
                                validation_status="VALID",
                                delivery_id=None,
                                delivery_type="register",
                                delivery_status="OPGENOMEN_LVBRO",
                                comments="Imported into BRO-Connector.",
                                quality_regime=gld.groundwater_monitoring_tube.groundwater_monitoring_well_static.quality_regime,
                            ),
                        )
                        continue

                    gld_registration_log = self.create_start_registration_sourcedocs(
                        well,
                        tube_id,
                    )
                    self.deliver_startregistration_sourcedocuments(gld_registration_log)

    def read_observation_id_from_xml(self, xml_string) -> str:
        # Define the namespaces
        namespaces = {
            "gml": "http://www.opengis.net/gml/3.2",
            "om": "http://www.opengis.net/om/2.0",
        }

        # Parse the XML string
        root = ET.fromstring(xml_string)

        # Find the OM_Observation element and get its gml:id attribute
        observation_elem = root.find(".//om:OM_Observation", namespaces)
        print(observation_elem)
        if observation_elem is not None:
            return observation_elem.attrib.get("{http://www.opengis.net/gml/3.2}id")

        return None

    def check_existing_startregistrations(
        self,
        registration: models.gld_registration_log,
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
        well = GroundwaterMonitoringWellStatic.objects.get(
            bro_id=registration.gmw_bro_id
        )
        self._set_bro_info(well)

        logger.info(self.bro_info)

        print("Registration process status: ", registration.process_status)

        if (
            registration.process_status == "succesfully_delivered_sourcedocuments"
            and registration.delivery_status != "OPGENOMEN_LVBRO"
            and registration.delivery_id is not None
        ):
            print("1st if statement")
            # The registration has been delivered, but not yet approved
            self.check_delivery_status_levering(registration)
            return
        else:
            # Succesfully generated a startregistration sourcedoc in the previous step
            if registration.process_status == "failed_to_generate_source_documents":
                logger.error(
                    "Failed to generate source documents, so registration log is invalid somehow."
                )
                self.create_start_registration_sourcedocs(well, registration)
                return
            # Validate the created sourcedocument
            if (
                registration.process_status
                == "succesfully_generated_startregistration_request"
            ):
                print("2nd if statement")
                self.validate_gld_startregistration_request(registration)
                return
            # If an error occured during validation, try again
            # Failed to validate sourcedocument doesn't mean the document is valid/invalid
            # It means something went wrong during validation (e.g BRO server error)
            # Even if a document is invalid, the validation process has succeeded and won't be reattempted

            if (
                registration.process_status == "failed_to_validate_sourcedocument"
            ):  ## CHECKED STATEMENT DID NOT CORRESPOND TO
                # If we failed to validate the sourcedocument, try again
                # TODO maybe limit amount of retries? Do not expect validation to fail multiple times..
                print("3rd if statement")
                self.validate_gld_startregistration_request(registration)
                return
            # If validation is succesful and the document is valid, try a delivery
            if registration.process_status == "source_document_validation_succesful":
                if registration_is_valid(registration):
                    print("4th if statement")
                    self.deliver_startregistration_sourcedocuments(registration)
                    return
                else:
                    print("5th if statement")
                    registration.delete()
                    return

            # If delivery is succesful, check the status of the delivery
            if (
                registration.process_status == "succesfully_delivered_sourcedocuments"
                and registration.delivery_status != "OPGENOMEN_LVBRO"
                and registration.delivery_id is not None
            ):
                print("6th if statement")
                # The registration has been delivered, but not yet approved
                self.check_delivery_status_levering(registration)
                return

            # If the delivery failed previously, we can retry
            if registration.process_status == "failed_to_deliver_sourcedocuments":
                # This will not be the case on the first try
                if registration.delivery_status == "failed_thrice":
                    # TODO report with mail?
                    print("7th if statement")
                    return
                else:
                    print("8th if statement")
                    self.deliver_startregistration_sourcedocuments(registration)
                    return

        logger.info(
            "None of the if statements are called, existing start registration is not edited."
        )

    ### ADDITIONS ###
    def generate_gld_addition_sourcedoc_data(
        self,
        observation: models.Observation,
    ):
        """
        Generate all additions for this observation instance
        Write to files in the additions folder
        These will later be delivered
        """

        observation_source_document_data, addition_type = (
            get_observation_gld_source_document_data(observation)
        )

        measurement_timeseries_tvp = get_timeseries_tvp_for_observation_id(observation)

        gld_bro_id, quality_regime = get_gld_registration_data_for_observation(
            observation
        )

        # try to create source document
        try:
            first_timestamp_datetime = observation.timestamp_first_measurement
            final_timestamp_datetime = observation.timestamp_last_measurement

            # Add the timeseries to the sourcedocument
            gld_addition_sourcedocument = deepcopy(observation_source_document_data)
            gld_addition_sourcedocument["observationId"] = f"_{uuid.uuid4()}"
            gld_addition_sourcedocument["metadata"]["dateStamp"] = (
                observation.date_stamp.strftime("%Y-%m-%d")
            )
            gld_addition_sourcedocument["result"] = list(measurement_timeseries_tvp)

            # filename should be unique
            filename = f"GLD_Addition_Observation_{observation.observation_id}_{gld_bro_id}.xml"

            # Create addition source document
            gld_addition_registration_request = brx.gld_registration_request(
                srcdoc="GLD_Addition",
                requestReference=filename,
                deliveryAccountableParty=str(
                    retrieve_responsible_kvk_from_observation(observation)
                ),  # investigator_identification (NENS voor TEST)
                qualityRegime=quality_regime,
                broId=gld_bro_id,
                srcdocdata=gld_addition_sourcedocument,
            )

            gld_addition_registration_request.generate()

            observation_id = self.read_observation_id_from_xml(
                gld_addition_registration_request.request
            )
            print(observation_id)

            gld_addition_registration_request.write_request(
                output_dir=ADDITION_DIR, filename=filename
            )

            record, created = models.gld_addition_log.objects.update_or_create(
                observation=observation,
                addition_type=form_addition_type(observation),
                defaults=dict(
                    observation_identifier=observation_id,
                    date_modified=datetime.datetime.now(),
                    start_date=first_timestamp_datetime,
                    end_date=final_timestamp_datetime,
                    broid_registration=gld_bro_id,
                    comments="Succesfully generated XML sourcedocument",
                    file=filename,
                    validation_status="TO_BE_VALIDATED",
                    addition_type=addition_type,
                    process_status="source_document_created",
                ),
            )

        # Failure to create the source document for this observation
        except Exception as e:
            # all_records_created = False
            record, created = models.gld_addition_log.objects.update_or_create(
                observation_id=observation.observation_id,
                defaults=dict(
                    date_modified=datetime.datetime.now(),
                    broid_registration=gld_bro_id,
                    comments="Failed to generate XML source document, {}".format(e),
                    process_status="failed_to_create_source_document",
                ),
            )

        return (record, created)

    def create_addition_sourcedocuments_for_observation(
        self, observation: models.Observation
    ):
        """
        Check the database for new observations and create new source documents
        """
        # If there is not a GLD registration present in the database we can't create sourcedocs
        gld = observation.groundwater_level_dossier
        if not gld:
            logger.error(
                "No GLD is available. An addition sourcedocument can't be created in this case."
            )
            return (None, False)

        # An addition sourcedocument shouldn't be created if the BroId of the GLD registration is not available
        if not gld.gld_bro_id:
            logger.error(
                "No BroID of the GLD registration is available. An addition sourcedocument shouldn't be created in this case."
            )
            return (None, False)

        observation_tvps = models.MeasurementTvp.objects.filter(
            observation_id=observation.observation_id
        )
        if not observation_tvps:  # if there are no tvps in the observation
            logger.error(
                "No observation time value pairs available in the observation. An addition source document cant be created in this case."
            )
            return (None, False)  # then do nothing

        print("getting sourcedoc")
        (
            observation_source_document_data,
            addition_type,
        ) = get_observation_gld_source_document_data(observation)

        print("generating addition sourcedoc")
        (gld_addition, created) = self.generate_gld_addition_sourcedoc_data(
            observation,
            observation_source_document_data,
            addition_type,
        )

        return (gld_addition, created)

    def validate_gld_addition_source_document(
        self,
        addition: models.gld_addition_log,
    ):
        """
        Validate the generated GLD addition sourcedoc
        """
        source_doc_file = os.path.join(ADDITION_DIR, addition.file)
        payload = open(source_doc_file)
        try:
            validation_info = brx.validate_sourcedoc(
                payload, bro_info=self.bro_info, demo=self.demo, api="v2"
            )
            validation_status = validation_info["status"]

            if "errors" in validation_info:
                comments = f"Validated sourcedocument, found errors: {validation_info['errors']}"
                addition.process_status = "source_document_validation_failed"

            else:
                comments = "Succesfully validated sourcedocument, no errors"

            addition.date_modified = datetime.datetime.now()
            addition.comments = comments[0:20000]
            addition.validation_status = validation_status
            addition.process_status = "source_document_validation_succeeded"

        except Exception as e:
            addition.date_modified = datetime.datetime.now()
            addition.comments = f"Failed to validate source document: {e}"
            addition.process_status = "source_document_validation_failed"

        addition.save()
        return validation_status

    def deliver_gld_addition_source_document(
        self,
        gld_addition: models.gld_addition_log,
        filename: str,
    ):
        """
        Deliver GLD addition sourcedocument to the BRO
        """
        source_doc_file = os.path.join(ADDITION_DIR, filename)
        payload = open(source_doc_file)
        request = {filename: payload}

        # If the delivery fails, use the this to indicate how many attempts were made
        delivery_status = gld_addition.delivery_status
        if delivery_status is None:
            delivery_status_update = "failed_once"
        else:
            position = bisect.bisect_left(failed_update_strings, delivery_status)
            delivery_status_update = failed_update_strings[position + 1]

        try:
            upload_info = brx.upload_sourcedocs_from_dict(
                request,
                token=self.bro_info["token"],
                demo=self.demo,
                api="v2",
                project_id=self.bro_info["projectnummer"],
            )

            if upload_info == "Error":
                comments = "Error occured during delivery of sourcedocument"

                gld_addition.date_modified = datetime.datetime.now()
                gld_addition.comments = comments
                gld_addition.delivery_status = delivery_status_update

            else:
                gld_addition.date_modified = datetime.datetime.now()
                gld_addition.comments = "Succesfully delivered sourcedocument"
                gld_addition.delivery_status = upload_info.json()["status"]
                gld_addition.last_changed = upload_info.json()["lastChanged"]
                gld_addition.delivery_id = upload_info.json()["identifier"]
                gld_addition.process_status = "source_document_delivered"

        except Exception as e:
            comments = (
                "Error occured in attempting to deliver sourcedocument, {}".format(e)
            )

            gld_addition.date_modified = datetime.datetime.now()
            gld_addition.comments = comments
            gld_addition.delivery_status = delivery_status_update

        gld_addition.save()

        return delivery_status_update

    def check_status_gld_addition(
        self,
        gld_addition: models.gld_addition_log,
    ):
        """
        Check the status of a delivery and log to the database what the status is
        """
        print("Delivery ID: ", gld_addition.delivery_id)
        try:
            upload_info = brx.check_delivery_status(
                gld_addition.delivery_id,
                token=self.bro_info["token"],
                demo=self.demo,
                api="v2",
                project_id=self.bro_info["projectnummer"],
            )
            delivery_status = upload_info.json()["status"]
        except Exception as e:
            comments = "Status check failed, {}".format(e)
            gld_addition.comments = comments
            gld_addition.save()
            return

        if delivery_status == "DOORGELEVERD":
            comments = "GLD addition is approved"
            gld_addition.date_modified = datetime.datetime.now()
            gld_addition.comments = comments
            gld_addition.delivery_status = delivery_status
            gld_addition.process_status = "delivery_approved"
            gld_addition.last_changed = upload_info.json()["lastChanged"]

        else:
            comments = "Status check succesful, not yet approved"
            gld_addition.date_modified = datetime.datetime.now()
            gld_addition.comments = comments
            gld_addition.delivery_status = delivery_status

        print("Upload info: ", upload_info.json())
        gld_addition.save()

        return delivery_status

    def validate_addition(
        self,
        gld_addition: models.gld_addition_log,
    ):
        """
        Validate the sourcedocuments, register the results in the database
        """
        # Validate the sourcedocument for this observation
        validation_status = self.validate_gld_addition_source_document(gld_addition)

        return validation_status

    def deliver_addition(
        self,
        gld_addition: models.gld_addition_log,
    ):
        """
        If there is a valid source document, deliver to the BRO
        If delivery has failed three times prior, no more attempts will be made
        """
        validation_status = gld_addition.validation_status
        filename = gld_addition.file

        print("Validation status: ", validation_status)

        if validation_status == "VALIDE" and gld_addition.delivery_id is None:
            delivery_status = self.deliver_gld_addition_source_document(
                gld_addition, filename
            )

            if delivery_status == "failed_thrice":
                # If delivery fails three times, we flag the observation as delivery failed
                gld_addition.process_status = "source_document_delivery_failed"
                gld_addition.save()

    def check_status_addition(
        self,
        gld_addition: models.gld_addition_log,
    ):
        """
        Check the status of a delivery
        If the delivery has been approved, remove the source document
        """
        file_name = gld_addition.file
        if gld_addition.delivery_id is None:
            print("Delivery ID is None")
            gld_addition.comments = (
                "Could not check delivery, as there is no delivery id."
            )
            gld_addition.process_status = "source_document_validation_failed"
            gld_addition.save()
            return "404"

        print("Checking new delivery status")
        new_delivery_status = self.check_status_gld_addition(gld_addition)

        try:
            if new_delivery_status == "DOORGELEVERD":  # "OPGENOMEN_LVBRO":
                sourcedoc_filepath = os.path.join(ADDITION_DIR, file_name)
                os.remove(sourcedoc_filepath)
        except Exception as e:
            logger.exception(e)
            logger.info(
                f"File {file_name} could not be removed from {ADDITION_DIR}. Likely manually removed or renamed."
            )
            pass  # no file to remove

        return new_delivery_status

    def gld_validate_and_deliver(
        self,
        gld_addition: models.gld_addition_log,
    ):
        """
        Main algorithm that checks the observations and performs actions based on the status
        """
        validated = False
        print("Process status: ", gld_addition.process_status)
        # For all the observations in the database, check the status and continue with the BRO delivery process
        if gld_addition.process_status == "source_document_created":
            # TODO check if procedure is same as other observations, use the same procedure uuid
            self.validate_addition(gld_addition)
            validated = True

        if (
            gld_addition.process_status == "source_document_validation_succeeded"
            and gld_addition.validation_status == "VALIDE"
        ):
            # This observation source document has been validated before
            # If result was NIET_VALIDE try again, otherwise try delivery
            # In total three attempts will be made for the delivery.
            self.deliver_addition(gld_addition)

        elif (
            gld_addition.process_status == "source_document_validation_failed"
            and validated is False
        ):
            # Something went wrong during document validation, try again
            self.validate_addition(gld_addition)

            validated = True
        else:
            logging.error(
                f"Validation status = {gld_addition.validation_status}. If this is not VALIDE, then the delivery is not initiated."
            )

        if gld_addition.process_status == "source_document_delivered":
            self.check_status_addition(gld_addition)

        elif gld_addition.process_status == "delivery_approved":
            logger.info(f"Delivery already approved (DOORGELEVERD): {gld_addition}")

        elif gld_addition.process_status == "flagged_for_deletion":
            # TODO Delete request
            return

        if gld_addition.process_status == "failed_to_create_source_document":
            logger.info(
                "Failed to create source document. check_status_addition is therefore not called and leads to a delivery ID error later on."
            )

        else:
            return

    def create_replace_sourcedocuments(
        self, observation: models.Observation
    ) -> models.gld_addition_log:
        # In development
        ...


class Command(BaseCommand):
    def handle(self, *args, **options):
        gld = GldSyncHandler()
        # Check the database for new wells/tubes and start a GLD registration for these objects if its it needed
        gld.handle_all_start_registrations()

        # Get all the current registrations, check and deliver
        gld_registrations = models.gld_registration_log.objects.all()
        for registration in gld_registrations:
            gld.check_existing_startregistrations(registration)

        # Create the addition sourcedocuments
        observation_set = models.Observation.objects.all()
        for observation in observation_set:
            addition_log = models.gld_addition_log.objects.filter(
                observation_id=observation.observation_id
            ).first()

            if not addition_log:
                (addition_log, created) = (
                    gld.create_addition_sourcedocuments_for_observation(observation)
                )

            if not addition_log:
                continue

            well = observation.groundwater_level_dossier.groundwater_monitoring_tube.groundwater_monitoring_well_static
            gld._set_bro_info(well)
            gld.gld_validate_and_deliver(addition_log)
