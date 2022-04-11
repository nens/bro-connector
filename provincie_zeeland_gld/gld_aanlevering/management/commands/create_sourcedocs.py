# -*- coding: utf-8 -*-
"""
NOTE: INITIALISES THE GLD REGISTER IN DE CSV DATABASE AND IN LIZARD
"""
from django.core.management.base import BaseCommand
from django.db import transaction

import pandas as pd
import requests
import gwmpy as gwm
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

from provincie_zeeland_gld.settings import GLD_AANLEVERING_SETTINGS
from gld_aanlevering import models

field_value_division_dict = {'cm':100, 'mm':1000}



def grouper(n, iterable):
    it = iter(iterable)
    while True:
        chunk = tuple(itertools.islice(it, n))
        if not chunk:
            return
        yield chunk

def get_measurement_point_metadata_for_measurement(measurement_point_metadata_id):
    
    measurement_point_metadata = models.MeasurementPointMetadata.objects.get(measurement_point_metadata_id=measurement_point_metadata_id)

    if models.TypeStatusQualityControl.objects.filter(id=measurement_point_metadata.qualifier_by_category).exists():
        status_qualitycontrol_data = models.TypeStatusQualityControl.objects.get(id=measurement_point_metadata.qualifier_by_category)
        status_qualitycontrol = status_qualitycontrol_data.value
    else:
        status_qualitycontrol = None
        
    if models.TypeInterpolationCode.objects.filter(id=measurement_point_metadata.interpolation_code).exists():
        interpolation_type_data = models.TypeInterpolationCode.objects.get(id=measurement_point_metadata.interpolation_code)
        interpolation_type = interpolation_type_data.value
    else:
        interpolation_type = None
    
    if models.TypeCensoredReasonCode.objects.filter(id=measurement_point_metadata.censored_reason).exists():
        censored_reason_data = models.TypeCensoredReasonCode.objects.get(id=measurement_point_metadata.censored_reason)
        censored_reason = censored_reason_data.value
    else:
        censored_reason = None
    
    #TODO censored reason alleen als er geen waarde vorkomt
    #TODO status quality control moet komen uit de QC quick check module, waardes in type_status_quality_control
    metadata = {'StatusQualityControl':status_qualitycontrol,
                'interpolationType': interpolation_type,
                'censoredReason': censored_reason}
    
    return metadata
    

def get_timeseries_tvp_for_measurement_time_series_id(measurement_time_series_id):
    
    """
    Get all timeseries values between start and stop datetime, including metadata
    """
    
    measurement_tvp = models.MeasurementTvp.objects.filter(measurement_time_series_id=measurement_time_series_id)
    measurements_list = []
    for measurement in measurement_tvp:        
        measurement_point_metadata_id = measurement.measurement_metadata_id
        metadata = get_measurement_point_metadata_for_measurement(measurement_point_metadata_id)
        
        # If the measurement value is None, this value must have been censored
        # TODO calculated value should be delivered
        if measurement.field_value is None:
            
            if metadata['censoredReason'] is None:                
                # We can't include a missing value without a censoring reason
                continue
            else:
                waterstand_waarde = None
        else:
            waterstand_waarde = float(measurement.field_value)
            waterstand_waarde_converted = waterstand_waarde / field_value_division_dict[measurement.field_value_unit]
        
        measurement_data = {'time':measurement.measurement_time.isoformat(),
                            'value': waterstand_waarde_converted,
                            'metadata':metadata}

        measurements_list += [measurement_data]

    return measurements_list      
    
def get_observation_with_measurement_time_series_id(measurement_time_series_id):
    observation = models.Observations.objects.get(measurement_time_series_id=measurement_time_series_id)
    return observation

def get_observation_metadata(observation_metadata_id):
    
    observation_metadata = models.ObservationMetadata.objects.get(observation_metadata_id=observation_metadata_id)
    
    responsible_party_id = observation_metadata.responsible_party_id
    principal_investigator_data = models.ResponsibleParty.objects.get(responsible_party_id=responsible_party_id)
    investigator_identification = principal_investigator_data.identification
   
    observation_type_id = observation_metadata.parameter_measurement_serie_type    
    observation_type_data = models.TypeObservationType.objects.get(id=observation_type_id)
    observation_type_value = observation_type_data.value

    type_status_data = models.TypeStatusCode.objects.get(id=observation_metadata.status)
    status = type_status_data.value

    date_stamp = observation_metadata.date_stamp.isoformat()
    
    observation_metadata = {'observationType': observation_type_value}
    
    return observation_metadata, status, date_stamp, investigator_identification

def get_observation_procedure_data(observation_process_id):
    
    
    """
    Get the procedure data for the observation
    This is unique for each observation
    """
    
    observation_process_data = models.ObservationProcess.objects.get(observation_process_id=observation_process_id)
    
    parameter_air_pressure_compensation_type_id = observation_process_data.parameter_air_pressure_compensation_type
    air_pressure_compensation_data = models.TypeAirPressureCompensation.objects.get(id=parameter_air_pressure_compensation_type_id)
    air_pressure_compensation_type = air_pressure_compensation_data.value
    
    parameter_measurement_instrument_type_id = observation_process_data.parameter_measurement_instrument_type
    measurement_instrument_type_data = models.TypeMeasementInstrumentType.objects.get(id=parameter_measurement_instrument_type_id)
    measurement_instrument_type = measurement_instrument_type_data.value
    
    parameter_evaluation_procedure_id = observation_process_data.parameter_evaluation_procedure
    evaluation_procedure_data = models.TypeEvaluationProcedure.objects.get(id=parameter_evaluation_procedure_id)
    evaluation_procedure = evaluation_procedure_data.value
    

    observation_procedure_data = {'airPressureCompensationType': air_pressure_compensation_type,
                                'evaluationProcedure': evaluation_procedure,
                                'measurementInstrumentType': measurement_instrument_type}

    return observation_procedure_data


def get_observation_gld_source_document_data(observation):
    
    """
    Generate the GLD addition sourcedocs, without result data
    """
    # Get the GLD registration id for this measurement timeseries
    # Check which parts of the observation have already been succesfully delivered
    
    # Get the measurement series id with observation id (1 to 1 relation)
    measurement_time_serie = models.MeasurementTimeSeries.objects.get(observation_id=observation.observation_id)
    measurement_time_series_id = measurement_time_serie.measurement_time_series_id
    
    # Get the observation metadata and procedure data
    observation_metadata, observation_status, observation_metadata_date_stamp, investigator_identification = get_observation_metadata(observation.observation_metadata_id)
    observation_procedure = get_observation_procedure_data(observation.observation_process_id)

    # Result time wordt de observation endtime 
    observation_result_time = observation.result_time.isoformat()
    
    # dateStamp word the date van de laatste observatie in een chunk
    
    if observation_metadata['observationType'] == 'controlemeting':

        # Create the sourcedocs for the addition, results will later be added in chunks
        source_document_data =  {'metadata':{'parameters': observation_metadata, 'dateStamp':None},
                                'procedure':{'parameters': observation_procedure}, 
                                'result': None}
        
    else:
        # Create the sourcedocs for the addition, results will later be added in chunks
        source_document_data =  {'metadata':{'status': observation_status,'parameters': observation_metadata, 'dateStamp':None},
                                'procedure':{'parameters': observation_procedure}, 
                                'result': None}

    return source_document_data, measurement_time_series_id

def get_gld_registration_data_for_observation(observation):
    
    """
    Each observation has a GLD id and GWM id
    When delivering the observations we get the GLD id from the observation
    We use the GWM id to get the quality regime for the well in which the measurement was taken
    """
    
    # Get the GLD bro id 
    gld_id_database = observation.groundwater_level_dossier_id
    gld_data = models.GroundwaterLevelDossier.objects.get(groundwater_level_dossier_id=gld_id_database)
    gld_bro_id = gld_data.gld_bro_id
    gmw_bro_id = gld_data.gmw_bro_id
    
    # Get the quality regime for the well
    # TODO quality regime changes, new well in database?
    gmw_well = models.GroundwaterMonitoringWells.objects.get(bro_id=gmw_bro_id)
    quality_regime = gmw_well.quality_regime
    
    return gld_bro_id, quality_regime
    

def generate_gld_addition_sourcedoc_data(observation, 
                                         observation_source_document_data, 
                                         measurement_time_series_id,
                                         additions_dir, 
                                         chunk_size=100):
    
    """
    Generate all additions for this observation instance
    Write to files in the additions folder
    These will later be delivered
    """

    # TODO check if the measurement timeseries contains values 

    measurement_timeseries_tvp = get_timeseries_tvp_for_measurement_time_series_id(measurement_time_series_id)
    measurements_length = len(measurement_timeseries_tvp)
    
    # TODO if there is no GLD registration for this observation, log
    # can be that measurements are loaded into database before registration is made
    # measurements should be delivered later 
    gld_bro_id, quality_regime = get_gld_registration_data_for_observation(observation)

    # Create a new directory for the observation additions 
    try: 
        first_timestamp = measurement_timeseries_tvp[0]['time']
        final_timestamp = measurement_timeseries_tvp[-1]['time']
        final_timestamp_date = datetime.datetime.fromisoformat(final_timestamp).date()

        # Add the timeseries to the sourcedocument
        gld_addition_sourcedocument = deepcopy(observation_source_document_data)
        gld_addition_sourcedocument['metadata']['dateStamp'] = final_timestamp_date.isoformat()
        gld_addition_sourcedocument['result'] = list(measurement_timeseries_tvp)

        filename = 'GLD_Addition_Observation_{}.xml'.format(observation.observation_id)
        
        # Create addition source document
        gld_addition_registration_request = gwm.gld_registration_request(srcdoc='GLD_Addition', 
                                                                         requestReference = filename, 
                                                                         deliveryAccountableParty = '20168636', #investigator_identification  
                                                                         qualityRegime = quality_regime,
                                                                         broId=gld_bro_id, 
                                                                         srcdocdata=gld_addition_sourcedocument)

        gld_addition_registration_request.generate()                        
        gld_addition_registration_request.write_xml(output_dir = additions_dir, filename = filename)
            
        record, created = \
            models.gld_addition_log_voorlopig.objects.update_or_create(
                observation_id=observation.observation_id,
                date_modified=datetime.datetime.now(),
                start = first_timestamp,
                end = final_timestamp,
                broid_registration = gld_bro_id,
                comments='Succesfully generated XML sourcedocument',
                file=filename)
            
        record, created = \
            models.Observation.objects.update_or_create(
                observation_id=observation.observation_id,
                defaults={'status':'source_document_created'})

    
    # Failure to create the source document for this observation 
    except Exception as e:
        all_records_created = False
        record, created = \
            models.gld_addition_log_voorlopig.objects.update_or_create(
                observation_id=observation.observation_id,
                date_modified=datetime.datetime.now(),
                start = first_timestamp,
                end = final_timestamp,
                broid_registration = gld_bro_id,
                comments='Failed to generate XML source document, {}'.format(e),
                file=filename)

        record, created = \
            models.Observation.objects.update_or_create(
                observation_id=observation.observation_id,
                defaults={'status':'failed_to_create_source_document'})


def gld_addition(organisation, environment, tempdir, additions_dir, acces_token_bro_portal):
    
    """
    Check the database for new observations and create new source documents
    """
        
    observation_set = models.Observation.objects.all()
    
    for observation in observation_set:
        
        if observation.status == 'observation_status_changed':
            
            # Comes from validation module
            # If status goes from 'voorlopig_beoordeeld' to 'volledig_beoordeeld', new delivery is made
            # If there are corrected values include these as well
            # Create source documents for delivery 
            
            # Is the observation fully delivered? 
            # Have corrections been made to the observation?
            # Has the observation been flagged for deletion?
            # Has the observation been quality checked with validation module -- > wait with delivery? 
            
            observation_source_document_data, measurement_time_series_id = get_observation_gld_source_document_data(observation)
            generate_gld_addition_sourcedoc_data(observation, observation_source_document_data, measurement_time_series_id, additions_dir)
            
        
        if observation.status == 'source_document_validation_failed':
            pass
            # TODO try to regenerate source documents if something is changed about the observation
        
                
        elif observation.status == 'source_document_delivery_failed':
            # This will 
            pass
    
        elif observation.status == 'observation_status_changed':
            # Comes from validation module
            # If status goes from 'voorlopig_beoordeeld' to 'volledig_beoordeeld', new delivery is made
            # If there are corrected values include these as well
            # Create source documents for delivery 
            pass
        
        elif observation.status == 'flagged_for_deletion':
            pass
                        
        # payload_as_dict = xmltodict.parse(payload)
        # procedure_id = payload_as_dict['registrationRequest']['sourceDocument']['GLD_Addition']['observation']['om:OM_Observation']['om:procedure']['wml2:ObservationProcess']['@gml:id']        
        # #          
        
        # # Log the procedure ID in the database
        
        # # Deliver the soruce docs 
        # deliver_gld_addition_sourcedocs(payload, acces_token_bro_portal)

        break
            

class Command(BaseCommand):       
     
    def handle(self, *args, **options):
        #print(NENS_DEMO_SETTINGS)
        
        organisation = GLD_AANLEVERING_SETTINGS['organisation']
        environment = GLD_AANLEVERING_SETTINGS['env']
        tempdir = GLD_AANLEVERING_SETTINGS['failed_dir_gld_addition']
        acces_token_bro_portal = GLD_AANLEVERING_SETTINGS['acces_token_bro_portal']
        additions_dir = GLD_AANLEVERING_SETTINGS['additions_dir']
        
        gld_addition(organisation, environment, tempdir,additions_dir, acces_token_bro_portal)
        
        
        