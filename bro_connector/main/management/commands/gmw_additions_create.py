# -*- coding: utf-8 -*-
"""
NOTE: INITIALISES THE GMW REGISTER IN DE CSV DATABASE AND IN LIZARD
CURRENTLY A COPY OF GLD WITH MINOR TWEAKS
"""
from django.core.management.base import BaseCommand
from django.db import transaction

import pandas as pd
import requests
import bro_exchange as brx
import json
import os
import sys
import traceback
import datetime
import math
import xmltodict
import itertools
from pathlib import Path
import pytz
import time
from copy import deepcopy
import logging

logger = logging.getLogger(__name__)

from bro_connector_gld.settings.base import GMW_AANLEVERING_SETTINGS
from gmw_aanlevering import models

field_value_division_dict = {"cm": 100, "mm": 1000, "m":1}


def grouper(n, iterable):
    it = iter(iterable)
    while True:
        chunk = tuple(itertools.islice(it, n))
        if not chunk:
            return
        yield chunk


def get_measurement_point_metadata_for_measurement(measurement_point_metadata_id):

    measurement_point_metadata = models.MeasurementPointMetadata.objects.get(
        measurement_point_metadata_id=measurement_point_metadata_id
    )

    if models.TypeStatusQualityControl.objects.filter(
        id=measurement_point_metadata.qualifier_by_category_id
    ).exists():
        status_qualitycontrol_data = models.TypeStatusQualityControl.objects.get(
            id=measurement_point_metadata.qualifier_by_category_id
        )
        status_qualitycontrol = status_qualitycontrol_data.value
    else:
        status_qualitycontrol = None

    if models.TypeInterpolationCode.objects.filter(
        id=measurement_point_metadata.interpolation_code_id
    ).exists():
        interpolation_type_data = models.TypeInterpolationCode.objects.get(
            id=measurement_point_metadata.interpolation_code_id
        )
        interpolation_type = interpolation_type_data.value
    else:
        interpolation_type = None

    if models.TypeCensoredReasonCode.objects.filter(
        id=measurement_point_metadata.censored_reason_id
    ).exists():
        censored_reason_data = models.TypeCensoredReasonCode.objects.get(
            id=measurement_point_metadata.censored_reason_id
        )
        censored_reason = censored_reason_data.value
    else:
        censored_reason = None

    if censored_reason is not None:

        metadata = {
            "StatusQualityControl": status_qualitycontrol,
            "interpolationType": interpolation_type,
            "censoredReason": censored_reason,
        }
    else:
        metadata = {
            "StatusQualityControl": status_qualitycontrol,
            "interpolationType": interpolation_type,
        }

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
        measurement_point_metadata_id = measurement.measurement_point_metadata_id
        metadata = get_measurement_point_metadata_for_measurement(
            measurement_point_metadata_id
        )

        # discard a measurement with quality control type 1 (afgekeurd)
        if metadata["StatusQualityControl"] == 1:
            continue
        # If the measurement value is None, this value must have been censored
        if measurement.calculated_value is None:

            if metadata["censoredReason"] is None:
                # We can't include a missing value without a censoring reason
                continue
            else:
                waterstand_waarde = None
        else:
            waterstand_waarde = float(measurement.calculated_value)
            waterstand_waarde_converted = (
                waterstand_waarde
                / field_value_division_dict[measurement.field_value_unit]
            )

        measurement_data = {
            "time": measurement.measurement_time.isoformat(),
            "value": waterstand_waarde_converted,
            "metadata": metadata,
        }

        measurements_list += [measurement_data]

    measurements_list_ordered = order_measurements_list(measurements_list)
    # print(measurements_list_ordered)
    return measurements_list_ordered


def get_observation_with_measurement_time_series_id(measurement_time_series_id):
    observation = models.Observations.objects.get(
        measurement_time_series_id=measurement_time_series_id
    )
    return observation


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

    type_status_data = models.TypeStatusCode.objects.get(id=observation_metadata.status_id)
    status = type_status_data.value  # value = onbekend, voorlopig or volledigBeoordeeld

    date_stamp = observation_metadata.date_stamp.isoformat()

    observation_metadata = {"observationType": observation_type_value, 'principalInvestigator':investigator_identification}

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


def get_observation_gmw_source_document_data(observation):

    """
    Generate the gmw addition sourcedocs, without result data
    """
    gmw_id_database = observation.groundwater_level_dossier_id
    gmw_data = models.GroundwaterLevelDossier.objects.get(
        groundwater_level_dossier_id=gmw_id_database
    )
    gmw_bro_id = gmw_data.gmw_bro_id

    # Get the quality regime for the well
    gmw_well = models.GroundwaterMonitoringWells.objects.get(bro_id=gmw_bro_id)
    quality_regime = gmw_well.quality_regime

    # Get the gmw registration id for this measurement timeseries
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


def get_gmw_registration_data(observation):

    """
    Each observation has a GWM id
    When delivering the observations we get the gmw id from the observation
    We use the GWM id to get the quality regime for the well in which the measurement was taken
    """

    # Get the GMW bro id
    gmw_id_database = observation.groundwater_level_dossier_id
    gmw_data = models.GroundwaterLevelDossier.objects.get(
        groundwater_level_dossier_id=gmw_id_database
    )
    gmw_bro_id = gmw_data.gmw_bro_id

    # Get the quality regime for the well
    # TODO quality regime changes, new well in database?
    gmw_well = models.GroundwaterMonitoringWellsStatic.objects.get(bro_id=gmw_bro_id)
    quality_regime = 'IMBRO' #gmw_well.quality_regime

    return gmw_bro_id, quality_regime


def generate_gmw_addition_sourcedoc_data(
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

    gmw_bro_id, quality_regime = get_gmw_registration_data(observation)

    # try to create source document
    try:
        first_timestamp = measurement_timeseries_tvp[0]["time"]
        final_timestamp = measurement_timeseries_tvp[-1]["time"]
        final_timestamp_date = datetime.datetime.fromisoformat(final_timestamp).date()

        # Add the timeseries to the sourcedocument
        gmw_addition_sourcedocument = deepcopy(observation_source_document_data)
        gmw_addition_sourcedocument["metadata"][
            "dateStamp"
        ] = final_timestamp_date.isoformat()
        gmw_addition_sourcedocument["result"] = list(measurement_timeseries_tvp)

        # filename should be unique
        filename = "gmw_Addition_Observation_{}_gmw_{}.xml".format(
            observation.observation_id, gmw_bro_id
        )

        # Create addition source document
        gmw_addition_registration_request = brx.gmw_registration_request(
            srcdoc="gmw_Addition",
            requestReference=filename,
            deliveryAccountableParty="27376655",  # investigator_identification (NENS voor TEST)
            qualityRegime=quality_regime,
            broId=gmw_bro_id,
            srcdocdata=gmw_addition_sourcedocument,
        )

        gmw_addition_registration_request.generate()

        gmw_addition_registration_request.write_request(
            output_dir=additions_dir, filename=filename
        )

        record, created = models.gmw_addition_log.objects.update_or_create(
            observation_id=observation.observation_id,
            defaults=dict(
                date_modified=datetime.datetime.now(),
                start=first_timestamp,
                end=final_timestamp,
                broid_registration=gmw_bro_id,
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
        record, created = models.gmw_addition_log.objects.update_or_create(
            observation_id=observation.observation_id,
            date_modified=datetime.datetime.now(),
            broid_registration=gmw_bro_id,
            comments="Failed to generate XML source document, {}".format(e),
        )

        record, created = models.Observation.objects.update_or_create(
            observation_id=observation.observation_id,
            defaults={"status": "failed_to_create_source_document"},
        )


def create_new_observations():
    """
    Add a new observation for every gmw that has no open observation
    An observation is open if it has no status. Once it has a status, it is
    (being) delivered to BRO and no new time-value pairs can be added.

    This function does not create the first observation of a gmw, this
    should be done manually because of connections with the metadata.
    """

    gmws = models.GroundwaterLevelDossier.objects.all()
    for gmw in gmws:
        gmw_id = gmw.groundwater_level_dossier_id
        observations_per_gmw = models.Observation.objects.filter(
            groundwater_level_dossier_id=gmw_id
        )
        observation_status_per_gmw = observations_per_gmw.filter(status=None)

        # if there is no empty observation status, a new observation is needed
        if not observation_status_per_gmw:
            # gather information about the previous observation
            try:
                previous_gmw_observation = observations_per_gmw.last()
                previous_observation_metadata_id = (
                    previous_gmw_observation.observation_metadata_id
                )
                previous_observation_process_id = (
                    previous_gmw_observation.observation_process_id
                )
            except:
                print(
                    "No observations exist yet for gmw {}, please create an observation".format(
                        gmw_id
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
                groundwater_level_dossier_id=gmw_id,
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
        # If there is not a gmw registration present in the database we can't create sourcedocs
        gmw_id_database = observation.groundwater_level_dossier_id
        if not models.GroundwaterLevelDossier.objects.filter(
            groundwater_level_dossier_id=gmw_id_database
        ).exists():
            continue



        # An addition sourcedocument shouldn't be created if the BroId of the gmw registration is not available
        if not models.GroundwaterLevelDossier.objects.get(
            groundwater_level_dossier_id=gmw_id_database
        ).gmw_bro_id:
            continue

        observation_tvps = models.MeasurementTvp.objects.filter(
            observation_id=observation.observation_id
        )
        if not observation_tvps:  # if there are no tvps in the observation
            continue  # then do nothing

        
        # observation contains tvps, check observation status and type
        # Get the observation metadata
        observation_metadata_id = observation.observation_metadata_id
        observation_metadata = models.ObservationMetadata.objects.get(
            observation_metadata_id=observation_metadata_id
        )
        observation_type = models.TypeObservationType.objects.get(
            id=observation_metadata.parameter_measurement_serie_type_id
        ).value
        if observation.status is None and observation_type == "controlemeting":
            # No QC check is performed on controlemeting
            (
                observation_source_document_data,
                addition_type,
            ) = get_observation_gmw_source_document_data(observation)

            generate_gmw_addition_sourcedoc_data(
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
            ) = get_observation_gmw_source_document_data(observation)

            generate_gmw_addition_sourcedoc_data(
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
            ) = get_observation_gmw_source_document_data(observation)

            generate_gmw_addition_sourcedoc_data(
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
            # We can recreate the same delivery sourcedocs with corrected values and deliver to the same gmw research
            pass


class Command(BaseCommand):
    def handle(self, *args, **options):
        # print(NENS_DEMO_SETTINGS)

        demo = GMW_AANLEVERING_SETTINGS["demo"]
        if demo:
            acces_token_bro_portal = GMW_AANLEVERING_SETTINGS[
                "acces_token_bro_portal_demo"
            ]
        else:
            acces_token_bro_portal = GMW_AANLEVERING_SETTINGS[
                "acces_token_bro_portal_bro_connector"
            ]

        additions_dir = GMW_AANLEVERING_SETTINGS["additions_dir"]

        create_addition_sourcedocuments_for_observations(
            additions_dir, acces_token_bro_portal
        )

        create_new_observations()