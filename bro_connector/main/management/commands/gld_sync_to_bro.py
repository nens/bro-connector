from django.core.management.base import BaseCommand
import bro_exchange as brx
import os
import datetime
import bisect
import reversion
from copy import deepcopy
from main.settings.base import gld_SETTINGS
from gld import models
from gmw import models as gmw_models

import logging

logger = logging.getLogger(__name__)

failed_update_strings = ["failed_once", "failed_twice", "failed_thrice"]

field_value_division_dict = {"cm": 100, "mm": 1000, "m": 1}

def get_registration_process_status(registration_id: int) -> str:
    registration = models.gld_registration_log.objects.get(id=registration_id)
    process_status = registration.process_status
    return process_status


def get_registration_validation_status(registration_id: int) -> str:
    registration = models.gld_registration_log.objects.get(id=registration_id)
    validation_status = registration.validation_status
    return validation_status

def convert_value_to_meter(measurement: models.MeasurementTvp) -> models.MeasurementTvp:
    waterstand_waarde = float(measurement.field_value)
    waterstand_waarde_converted = (
        waterstand_waarde
        / field_value_division_dict[measurement.field_value_unit]
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

def get_measurement_point_metadata_for_measurement(measurement_point_metadata: models.MeasurementPointMetadata):
    metadata = {
        "StatusQualityControl": measurement_point_metadata.status_quality_control,
        "interpolationType": measurement_point_metadata.interpolation_code,
    }
    if measurement_point_metadata.censor_reason:
        metadata["censoredReason"] = measurement_point_metadata.censor_reason

    return metadata

def get_timeseries_tvp_for_observation_id(observation_id: int):
    """
    Get all timeseries values between start and stop datetime, including metadata
    """
    # TODO checken of toegepaste filter/check werkt (of de measurement_list alleen de goedgekeurde waardes heeft)

    measurement_tvp = models.MeasurementTvp.objects.filter(
        observation_id=observation_id
    )
    measurements_list = []
    for measurement in measurement_tvp:
        metadata = get_measurement_point_metadata_for_measurement(
            measurement.measurement_point_metadata
        )

        # discard a measurement with quality control type 1 (afgekeurd)
        if metadata["StatusQualityControl"] == "afgekeurd":
            continue
        
        # If the measurement value is None, this value must have been censored
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

def get_observation_procedure_data(observation_process_id, quality_regime):
    """
    Get the procedure data for the observation
    This is unique for each observation
    """

    observation_process_data = models.ObservationProcess.objects.get(
        observation_process_id=observation_process_id
    )

    parameter_air_pressure_compensation_type_id = (
        observation_process_data.parameter_air_pressure_compensation_type_id
    )
    air_pressure_compensation_data = models.TypeAirPressureCompensation.objects.get(
        id=parameter_air_pressure_compensation_type_id
    )
    air_pressure_compensation_type = air_pressure_compensation_data.value

    parameter_measurement_instrument_type_id = (
        observation_process_data.parameter_measurement_instrument_type_id
    )
    measurement_instrument_type_data = models.TypeMeasurementInstrumentType.objects.get(
        id=parameter_measurement_instrument_type_id
    )
    measurement_instrument_type = measurement_instrument_type_data.value

    parameter_evaluation_procedure_id = (
        observation_process_data.parameter_evaluation_procedure_id
    )
    evaluation_procedure_data = models.TypeEvaluationProcedure.objects.get(
        id=parameter_evaluation_procedure_id
    )
    evaluation_procedure = evaluation_procedure_data.value

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
    gmw_well = gmw_models.GroundwaterMonitoringWellStatic.objects.get(bro_id=gmw_bro_id)
    quality_regime = gmw_well.quality_regime

    # Get the GLD registration id for this measurement timeseries
    # Check which parts of the observation have already been succesfully delivered

    # Get the observation metadata and procedure data
    observation_metadata_instance = observation.observation_metadata
    observation_status = observation_metadata_instance.status

    observation_metadata = {
        "observationType": observation_metadata_instance.observation_type,
        "principalInvestigator": observation_metadata_instance.responsible_party.identification,
    }   
    
    observation_procedure = get_observation_procedure_data(
        observation.observation_process_id, quality_regime
    )

    # Result time is the observation endtime
    observation_result_time = observation.result_time.isoformat()

    # dateStamp becomes the date of the last observation in a chunk
    # Generate the addition type for the logging
    # Can be either 'controlemeting, 'regulier_voorlopig_beoordeeld' or 'regulier_volledig_beoordeeld'

    if observation_metadata["observationType"] == "controlemeting":
        addition_type = "controlemeting"

        # Create the sourcedocs for the addition, results will later be added in chunks
        source_document_data = {
            "metadata": {"parameters": observation_metadata, "dateStamp": None},
            "procedure": {"parameters": observation_procedure},
            "resultTime": observation_result_time,
            "result": None,
        }

    else:
        # Create the sourcedocs for the addition, results will later be added in chunks
        source_document_data = {
            "metadata": {
                "status": observation_status,
                "parameters": observation_metadata,
                "dateStamp": None,
            },
            "resultTime": observation_result_time,
            "procedure": {"parameters": observation_procedure},
            "result": None,
        }

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
    gmw_well = gmw_models.GroundwaterMonitoringWellStatic.objects.get(bro_id=gmw_bro_id)
    quality_regime = gmw_well.quality_regime

    return gld_bro_id, quality_regime


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
            except:
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


class GldSyncHandler:
    def __init__(self, gld_settings):
        self.registrations_dir = gld_settings["startregistrations_dir"]
        self.demo = gld_settings["demo"]
        
        if self.demo:
            self.access_info = gld_settings["bro_info_demo"]
        else:
            self.access_info = gld_settings["bro_info_bro_connector"]
        
        self.additions_dir = gld_settings["additions_dir"]
        self.monitoringnetworks = gld_settings["monitoringnetworks"]

    def create_start_registration_sourcedocs(
        self,
        well: gmw_models.GroundwaterMonitoringWellStatic,
        filtrnr,
    ):
        """
        Try to create startregistration sourcedocuments for a well/tube/quality regime
        Startregistration requests are saved to .xml file in startregistrations folder
        """
        bro_id_gmw = well.bro_id
        location_code = well.nitg_code
        quality_regime = well.quality_regime
        delivery_accountable_party = well.delivery_accountable_party

        try:
            monitoringpoints = [{"broId": bro_id_gmw, "tubeNumber": filtrnr}]

            if self.monitoringnetworks == None:
                srcdocdata = {
                    "objectIdAccountableParty": location_code + str(filtrnr),
                    "monitoringPoints": monitoringpoints,
                }
            else:
                srcdocdata = {
                    "objectIdAccountableParty": location_code + str(filtrnr),
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
                output_dir=self.registrations_dir, filename=filename
            )

            process_status = "succesfully_generated_startregistration_request"
            record, created = models.gld_registration_log.objects.update_or_create(
                gwm_bro_id=bro_id_gmw,
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
                gwm_bro_id=bro_id_gmw,
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

    def create_sourcedocs_start_registrations(self):
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
                        well,
                        tube_id,
                    )

    def check_existing_startregistrations(
        self,
        registration_log: models.gld_registration_log,
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
        # We check the status of the registration and either validate/deliver/check status/do nothing
        registration_id = registration_log.id

        if (
            get_registration_process_status(registration_id)
            == "succesfully_delivered_sourcedocuments"
            and registration_log.levering_status != "OPGENOMEN_LVBRO"
            and registration_log.levering_id is not None
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
                and registration_log.levering_status != "OPGENOMEN_LVBRO"
                and registration_log.levering_id is not None
            ):
                # The registration has been delivered, but not yet approved
                self.check_delivery_status_levering(registration_id)

            # If the delivery failed previously, we can retry
            if (
                get_registration_process_status(registration_id)
                == "failed_to_deliver_sourcedocuments"
            ):
                # This will not be the case on the first try
                if registration_log.levering_status == "failed_thrice":
                    # TODO report with mail?
                    return
                else:
                    self.deliver_startregistration_sourcedocuments(registration_log.id)

### ADDITIONS ###
    def generate_gld_addition_sourcedoc_data(
            self,
            observation,
            observation_source_document_data,
            addition_type,
        ):
        """
        Generate all additions for this observation instance
        Write to files in the additions folder
        These will later be delivered
        """

        measurement_timeseries_tvp = get_timeseries_tvp_for_observation_id(
            observation.observation_id
        )

        gld_bro_id, quality_regime = get_gld_registration_data_for_observation(observation)

        # try to create source document
        try:
            first_timestamp = measurement_timeseries_tvp[0]["time"]
            first_timestamp_datetime = datetime.datetime.fromisoformat(first_timestamp)
            first_timestamp_date = first_timestamp_datetime.date()

            final_timestamp = measurement_timeseries_tvp[-1]["time"]
            final_timestamp_datetime = datetime.datetime.fromisoformat(final_timestamp)
            final_timestamp_date = final_timestamp_datetime.date()

            # Add the timeseries to the sourcedocument
            gld_addition_sourcedocument = deepcopy(observation_source_document_data)
            gld_addition_sourcedocument["metadata"][
                "dateStamp"
            ] = final_timestamp_date.isoformat()
            gld_addition_sourcedocument["result"] = list(measurement_timeseries_tvp)

            # filename should be unique
            filename = "GLD_Addition_Observation_{}_GLD_{}.xml".format(
                observation.observation_id, gld_bro_id
            )

            # Create addition source document
            gld_addition_registration_request = brx.gld_registration_request(
                srcdoc="GLD_Addition",
                requestReference=filename,
                deliveryAccountableParty="27376655",  # investigator_identification (NENS voor TEST)
                qualityRegime=quality_regime,
                broId=gld_bro_id,
                srcdocdata=gld_addition_sourcedocument,
            )

            gld_addition_registration_request.generate()

            gld_addition_registration_request.write_request(
                output_dir=self.additions_dir, filename=filename
            )

            record, created = models.gld_addition_log.objects.update_or_create(
                observation_id=observation.observation_id,
                defaults=dict(
                    date_modified=datetime.datetime.now(),
                    start_date = first_timestamp_datetime,
                    end_date = final_timestamp_datetime,
                    broid_registration=gld_bro_id,
                    comments="Succesfully generated XML sourcedocument",
                    file=filename,
                    validation_status=None,
                    addition_type=addition_type,
                    process_status = "source_document_created",
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
                    process_status = "failed_to_create_source_document",
                ),
            )
        
        return (record, created)

    def create_addition_sourcedocuments_for_observation(
        self,
        observation: models.Observation
    ):
        """
        Check the database for new observations and create new source documents
        """
        # If there is not a GLD registration present in the database we can't create sourcedocs
        gld = observation.groundwater_level_dossier
        if not gld:
            return

        # An addition sourcedocument shouldn't be created if the BroId of the GLD registration is not available
        if not gld.gld_bro_id:
            return

        observation_tvps = models.MeasurementTvp.objects.filter(
            observation_id=observation.observation_id
        )
        if not observation_tvps:  # if there are no tvps in the observation
            return  # then do nothing

        (
            observation_source_document_data,
            addition_type,
        ) = get_observation_gld_source_document_data(observation)

        (gld_addition, created) = self.generate_gld_addition_sourcedoc_data(
            observation,
            observation_source_document_data,
            addition_type,
        )

        return (gld_addition, created)

    def validate_gld_addition_source_document(
            self,
            addition: models.gld_addition_log, 
            filename: str,
        ):
        """
        Validate the generated GLD addition sourcedoc
        """
        source_doc_file = os.path.join(self.additions_dir, filename)
        payload = open(source_doc_file)

        try:
            validation_info = brx.validate_sourcedoc(
                payload, self.access_info, demo=self.demo
            )
            
            validation_status = validation_info["status"]

            if "errors" in validation_info:
                comments = f"Validated sourcedocument, found errors: {validation_info['errors']}"
                addition.process_status = "source_document_validation_failed"

            else:
                comments = "Succesfully validated sourcedocument, no errors"

            
            addition.date_modified =  datetime.datetime.now()
            addition.comments = comments[0:20000]
            addition.validation_status =  validation_status
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
        source_doc_file = os.path.join(gld_SETTINGS["additions_dir"], filename)
        payload = open(source_doc_file)
        request = {filename: payload}

        # If the delivery fails, use the this to indicate how many attempts were made
        delivery_status = gld_addition.levering_status
        if delivery_status is None:
            delivery_status_update = "failed_once"
        else:
            position = bisect.bisect_left(failed_update_strings, delivery_status)
            delivery_status_update = failed_update_strings[position + 1]

        try:
            upload_info = brx.upload_sourcedocs_from_dict(
                request, self.access_info, demo=self.demo
            )

            if upload_info == "Error":
                comments = "Error occured during delivery of sourcedocument"

                gld_addition.date_modified = datetime.datetime.now()
                gld_addition.comments = comments
                gld_addition.levering_status = delivery_status_update

            else:
                gld_addition.date_modified = datetime.datetime.now()
                gld_addition.comments = "Succesfully delivered sourcedocument"
                gld_addition.levering_status = upload_info.json()["status"]
                gld_addition.last_changed = upload_info.json()["lastChanged"]
                gld_addition.levering_id = upload_info.json()["identifier"]
                gld_addition.process_status = "source_document_delivered"

        except Exception as e:
            comments = "Error occured in attempting to deliver sourcedocument, {}".format(e)

            gld_addition.date_modified = datetime.datetime.now()
            gld_addition.comments = comments
            gld_addition.levering_status = delivery_status_update
        
        gld_addition.save()

        return delivery_status_update


    def check_status_gld_addition(
            self,
            gld_addition: models.gld_addition_log,
        ):
        """
        Check the status of a delivery and log to the database what the status is
        """
        try:
            upload_info = brx.check_delivery_status(
                gld_addition.levering_id, self.access_info, demo=self.demo
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
            gld_addition.levering_status = delivery_status
            gld_addition.process_status = "delivery_approved"
            gld_addition.last_changed=upload_info.json()["lastChanged"]

        else:
            comments = "Status check succesful, not yet approved"
            gld_addition.date_modified = datetime.datetime.now()
            gld_addition.comments = comments
            gld_addition.levering_status = delivery_status

        gld_addition.save()

        return delivery_status


    def validate_addition(
            self,
            gld_addition: models.gld_addition_log,
        ):
        """
        Validate the sourcedocuments, register the results in the database
        """
        filename = gld_addition.file
        validation_status = gld_addition.validation_status

        # Validate the sourcedocument for this observation
        validation_status = self.validate_gld_addition_source_document(
            gld_addition, filename
        )

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

        if validation_status == "VALIDE" and gld_addition.levering_id is None:
            delivery_status = self.deliver_gld_addition_source_document(
                gld_addition, filename
            )

            if delivery_status == "failed_thrice":
                # If delivery fails three times, we flag the observation as delivery failed
                gld_addition.process_status =  "source_document_delivery_failed"
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

        new_delivery_status = self.check_status_gld_addition(
            gld_addition
        )

        try:
            if new_delivery_status == "DOORGELEVERD":  # "OPGENOMEN_LVBRO":
                sourcedoc_filepath = os.path.join(gld_SETTINGS["additions_dir"], file_name)
                os.remove(sourcedoc_filepath)
        except:
            logger.info(f"File {file_name} could not be removed from {gld_SETTINGS['additions_dir']}. Likely manually removed or renamed.")
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
        # For all the observations in the database, check the status and continue with the BRO delivery process
        if gld_addition.process_status == "source_document_created":
            # TODO check if procedure is same as other observations, use the same procedure uuid
            validation_status = self.validate_addition(
                gld_addition
            )

            validated = True

        elif (
            gld_addition.process_status == "source_document_validation_succeeded"
            and gld_addition.validation_status == "VALIDE"
            ):
            # This observation source document has been validated before
            # If result was NIET_VALIDE try again, otherwise try delivery
            # In total three attempts will be made for the delivery.
            delivery_status = self.deliver_addition(
                gld_addition
            )

        elif gld_addition.process_status == "source_document_validation_failed" and validated == False:
            # Something went wrong during document validation, try again
            validation_status = self.validate_addition(
                gld_addition
            )

            validated = True


        if gld_addition.process_status == "source_document_delivered":
            delivery_status = self.check_status_addition(
                gld_addition
            )

        elif gld_addition.process_status == "delivery_approved":
            logger.info(f"Delivery already approved (DOORGELEVERD): {gld_addition}")

        elif gld_addition.process_status == "flagged_for_deletion":
            # TODO Delete request
            return

        else:
            return
        

    def create_replace_sourcedocuments(self, observation: models.Observation) -> models.gld_addition_log:
        # In development
        ...

class Command(BaseCommand):
    def handle(self, *args, **options):
        gld = GldSyncHandler(gld_SETTINGS)

        # Check the database for new wells/tubes and start a GLD registration for these objects if its it needed
        gld.create_sourcedocs_start_registrations()

        # Get all the current registrations, check and deliver
        gld_registrations = models.gld_registration_log.objects.all()
        for registration in gld_registrations:
            gld.check_existing_startregistrations(registration)

        # Create the addition sourcedocuments
        observation_set = models.Observation.objects.all()
        for observation in observation_set:
            addition_log = models.gld_addition_log.objects.filter(
                observation_id = observation.observation_id
            ).first()

            if not addition_log:
                (addition_log, created) = gld.create_addition_sourcedocuments_for_observation(observation)

            gld.gld_validate_and_deliver(addition_log)