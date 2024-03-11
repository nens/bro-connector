# -*- coding: utf-8 -*-
"""
NOTE: INITIALISES THE GLD REGISTER IN DE CSV DATABASE AND IN LIZARD
"""
from django.core.management.base import BaseCommand

import bro_exchange as brx
import datetime
import itertools
from copy import deepcopy
import logging
import reversion

logger = logging.getLogger(__name__)

from main.settings.base import gld_SETTINGS
from gld import models
from gmw import models as gmw_models

field_value_division_dict = {"cm": 100, "mm": 1000, "m": 1}


def grouper(n, iterable):
    it = iter(iterable)
    while True:
        chunk = tuple(itertools.islice(it, n))
        if not chunk:
            return
        yield chunk


def get_measurement_point_metadata_for_measurement(measurement_point_metadata: models.MeasurementPointMetadata):
    metadata = {
        "StatusQualityControl": measurement_point_metadata.status_quality_control,
        "interpolationType": measurement_point_metadata.interpolation_code,
    }
    if measurement_point_metadata.censor_reason:
        metadata["censoredReason"] = measurement_point_metadata.censor_reason

    return metadata


def order_measurements_list(measurement_list):
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

def get_timeseries_tvp_for_observation_id(observation_id):
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

def get_observation_metadata(observation_metadata_id):
    observation_metadata = models.ObservationMetadata.objects.get(
        observation_metadata_id=observation_metadata_id
    )

    responsible_party_id = observation_metadata.responsible_party_id
    principal_investigator_data = models.ResponsibleParty.objects.get(
        responsible_party_id=responsible_party_id
    )
    investigator_identification = (
        principal_investigator_data.identification
    )  # kvk number

    observation_type_id = observation_metadata.parameter_measurement_serie_type_id
    observation_type_data = models.TypeObservationType.objects.get(
        id=observation_type_id
    )
    observation_type_value = (
        observation_type_data.value
    )  # value = reguliereMeting or controlemeting

    type_status_data = models.TypeStatusCode.objects.get(
        id=observation_metadata.status_id
    )
    status = type_status_data.value  # value = onbekend, voorlopig or volledigBeoordeeld

    date_stamp = observation_metadata.date_stamp.isoformat()

    observation_metadata = {
        "observationType": observation_type_value,
        "principalInvestigator": investigator_identification,
    }

    return observation_metadata, status, date_stamp, investigator_identification


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
    (
        observation_metadata,
        observation_status,
        observation_metadata_date_stamp,
        investigator_identification,
    ) = get_observation_metadata(observation.observation_metadata_id)
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


def generate_gld_addition_sourcedoc_data(
    observation,
    observation_source_document_data,
    additions_dir,
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
        final_timestamp = measurement_timeseries_tvp[-1]["time"]
        final_timestamp_date = datetime.datetime.fromisoformat(final_timestamp).date()

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
            output_dir=additions_dir, filename=filename
        )

        record, created = models.gld_addition_log.objects.update_or_create(
            observation_id=observation.observation_id,
            defaults=dict(
                date_modified=datetime.datetime.now(),
                start=first_timestamp,
                end=final_timestamp,
                broid_registration=gld_bro_id,
                comments="Succesfully generated XML sourcedocument",
                file=filename,
                validation_status=None,
                addition_type=addition_type,
            ),
        )
        record, created = models.Observation.objects.update_or_create(
            observation_id=observation.observation_id,
            defaults={"status": "source_document_created"},
        )

    # Failure to create the source document for this observation
    except Exception as e:
        # all_records_created = False
        record, created = models.gld_addition_log.objects.update_or_create(
            observation_id=observation.observation_id,
            date_modified=datetime.datetime.now(),
            broid_registration=gld_bro_id,
            comments="Failed to generate XML source document, {}".format(e),
        )

        record, created = models.Observation.objects.update_or_create(
            observation_id=observation.observation_id,
            defaults={"status": "failed_to_create_source_document"},
        )


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


def create_addition_sourcedocuments_for_observations(
    additions_dir, acces_token_bro_portal
):
    """
    Check the database for new observations and create new source documents
    """

    observation_set = models.Observation.objects.all()

    for observation in observation_set:
        # If there is not a GLD registration present in the database we can't create sourcedocs
        gld = observation.groundwater_level_dossier
        if not gld:
            continue

        # An addition sourcedocument shouldn't be created if the BroId of the GLD registration is not available
        if not gld.gld_bro_id:
            continue

        observation_tvps = models.MeasurementTvp.objects.filter(
            observation_id=observation.observation_id
        )
        if not observation_tvps:  # if there are no tvps in the observation
            continue  # then do nothing

        # observation contains tvps, check observation status and type
        # Get the observation metadata
        observation_metadata = observation.observation_metadata
        observation_type = observation_metadata.observation_type
        if observation_type == "controlemeting":
            # No QC check is performed on controlemeting
            (
                observation_source_document_data,
                addition_type,
            ) = get_observation_gld_source_document_data(observation)

            generate_gld_addition_sourcedoc_data(
                observation,
                observation_source_document_data,
                additions_dir,
                addition_type,
            )

        elif observation.status is None and observation_type == "reguliereMeting":
            # no sourcedoc created for reguliere meting without status
            continue

        elif (
            observation.status == "observation_qc_completed"
            and observation_type == "reguliereMeting"
        ):
            # If the QC check has been succesfully completed
            (
                observation_source_document_data,
                addition_type,
            ) = get_observation_gld_source_document_data(observation)

            generate_gld_addition_sourcedoc_data(
                observation,
                observation_source_document_data,
                additions_dir,
                addition_type,
            )

        elif observation.status == "failed_to_create_source_document":
            # if the sourcedoc creation has failed, try again
            # this will probably keep failing until changes are made to the database
            (
                observation_source_document_data,
                addition_type,
            ) = get_observation_gld_source_document_data(observation)

            generate_gld_addition_sourcedoc_data(
                observation,
                observation_source_document_data,
                additions_dir,
                addition_type,
            )

        elif observation.status == "observation_volledig_beoordeeld":
            # TODO if observations are volledig beoordeeld, deliver to the BRO
            # An observation with this status has to be added by the Provincie including this status flag!
            pass

        elif observation.status == "observation_corrected":
            # TODO Change request
            # This is basically the same as an addition with corrected values and corrected reason
            # We can recreate the same delivery sourcedocs with corrected values and deliver to the same GLD research
            pass


class Command(BaseCommand):
    def handle(self, *args, **options):
        # print(NENS_DEMO_SETTINGS)

        demo = gld_SETTINGS["demo"]
        if demo:
            acces_token_bro_portal = gld_SETTINGS["acces_token_bro_portal_demo"]
        else:
            acces_token_bro_portal = gld_SETTINGS[
                "acces_token_bro_portal_bro_connector"
            ]

        additions_dir = gld_SETTINGS["additions_dir"]

        create_addition_sourcedocuments_for_observations(
            additions_dir, acces_token_bro_portal
        )

        create_new_observations()
