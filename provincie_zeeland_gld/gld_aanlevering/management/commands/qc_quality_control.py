
# This script monitors the measurements of each observation
# Measurements that are not checked yet, will be checked for quality
# Measurements are checked only checked within their own observation

# Checks to be included are
# - Min/max value specific for the observation filter/location
# - Max changes in values between values 
# - 'Flatline' check

# After an observation is checked the following will happen
# - Indivual mesaurements will get type_status_quality_control 'goedgekeurd', 'afgekeurd' , they enter the database with type 'nogNietBeoordeeld'
# - The observation will get metadata 'voorlopigBeoordeeld
# - The observation status will change to 'observation_qc_completed'

# After this the observation is picked up by the create_sourcedocs module

# If values are corrected these will be flagged in the observation 
# A new delivery will have to be made to deliver the corrected values
# If values are flagged for deletion, this will also have to flagged in the observation

# Censor values outside measuring range, include parameters for this in 'aanlevering' schema?

from django.core.management.base import BaseCommand

import gwmpy as gwm
import os
import datetime
import bisect
import logging
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

from provincie_zeeland_gld.settings import GLD_AANLEVERING_SETTINGS
from provincie_zeeland_gld import settings
from gld_aanlevering import models

from create_addition_sourcedocs import get_measurement_point_metadata_for_measurement, get_timeseries_tvp_for_measurement_time_series_id

field_value_division_dict = {'cm':100, 'mm':1000}

status_quality_control_values = {1:'afgekeurd', 
                                 2:'goedgekeurd',
                                 3:'nogNietBeoordeeld',
                                 4:'onbeslist',
                                 9:'obekend'}


def get_previous_valid_observation(observation):
    # Get the previous valid observation for this 
    pass    

def min_max_check(measurement_list, min_value, max_value):
    # Op basis van historische gegevens
    # Op basis van put kenmerken
    # Onderkant buis 
    # Niet hoger dan 10m NAP
    pass

def liveliness_check(measurement_list, observation, liveliness_limit):
    
    
    for measurement in measurement_list: 
        
    
    # Niet meer dan 1 meter binnen observatie
    # Voorgaande week alles dezelfde waarde 
    pass

def long_term_measurement_change_check(measurement_list, observation, max_change):
    # Verschillen over langere tijd
    # Vergelijken met eerste vorige goedgekeurde observatie reeks
    pass


def QC_check_main(observation, qc_settings):
    
    measurement_time_serie = models.MeasurementTimeSeries.objects.get(observation_id=observation.observation_id)
    measurement_time_series_id = measurement_time_serie.measurement_time_series_id

    # Get the observation measurements
    measurements_list = get_timeseries_tvp_for_measurement_time_series_id(measurement_time_series_id)
    
    # Run the invididual checks for the measurememnts
    checks = {}
    
    min_max_check = min_max_check(measurement_list, min_value)
    
    
    
    
    # If one of the checks fails set the measurement metadata type_status_quality_control to 1 (afgekeurd) 
    # Otherwise 2 (goedgekeurd)
    
    # Set the observation type_status_code to 2 (voorlopig)
    
    pass


class Command(BaseCommand):       
     
    def handle(self, *args, **options):
        
        qc_settings = settings.QUICK_SCAN_SETTINGS
        observation_set = models.Observation.objects.all()
        # Is the observation 
    
        for observation in observation_set:
            
            # Get the observation metadata
            observation_metadata_id = observation.observation_metadata_id
            observation_metadata = models.ObservationMetadata.objects.get(id=observation_metadata_id)
            observation_type = models.TypeObservationType.objects.get(id=observation_metadata.parameter_measurement_serie_type)
        
            if observation.status is None and observation_type == 'reguliereMeting':        
                _ = QC_check_main(observation, qc_settings)
