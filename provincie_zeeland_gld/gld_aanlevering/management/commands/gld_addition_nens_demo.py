# -*- coding: utf-8 -*-
"""
NOTE: INITIALISES THE GLD REGISTER IN DE CSV DATABASE AND IN LIZARD
"""
from django.core.management.base import BaseCommand
from django.db import transaction


#%%

import pandas as pd
import LizardTools as lt
import TacticTools as tt
import requests
import gwmpy as gwm
import json
import os
import sys
import traceback
import datetime
import math
from pathlib import Path
import pytz
import time
import xmltodict
from copy import deepcopy
import logging

logger = logging.getLogger(__name__)


#%%

# cd C:\Users\karl.schutt\Documents\Projecten\Brabant_BRO_koppeling\dev_herzien\gld_aanlevering


#%%

from bro_converter.settings import NENS_DEMO_SETTINGS
from _nens_demo.models import gld_addition_log_voorlopig, gld_addition_log_controle, gld_addition_log_volledig, aanleverinfo_filters

model_translation = {'WNS9040':gld_addition_log_voorlopig,'WNS9040.hand':gld_addition_log_controle, 'WNS9040.val':gld_addition_log_volledig}

#%% Functions

# =============================================================================
# 1. Queries
# =============================================================================

def get_broid_gmw(extra_metadata,env,organisation):
    try: 
        extra_metadata_bro_df = pd.DataFrame(extra_metadata['bro'][env])
        bro_id_gmw = extra_metadata_bro_df[extra_metadata_bro_df['organisation']==organisation]['gmw'].values[0]['bro_id']
        return(bro_id_gmw)
    except:
        return(None)

def get_broid_gld(extra_metadata,env,organisation):
    try: 
        extra_metadata_bro_df = pd.DataFrame(extra_metadata['bro'][env])
        bro_id_gld = extra_metadata_bro_df[extra_metadata_bro_df['organisation']==organisation]['gld'].values[0]['bro_id']
        return(bro_id_gld)
    except:
        return(None)
    
def get_qualityregime_gld(extra_metadata,env,organisation):
    try: 
        extra_metadata_bro_df = pd.DataFrame(extra_metadata['bro'][env])
        qualityregime = extra_metadata_bro_df[extra_metadata_bro_df['organisation']==organisation]['gld'].values[0]['qualityRegime']
        return(qualityregime)
    except:
        return(None)

def get_deliveryaccountableparty_gld(extra_metadata,env,organisation):
    try: 
        extra_metadata_bro_df = pd.DataFrame(extra_metadata['bro'][env])
        deliveryaccountableparty = extra_metadata_bro_df[extra_metadata_bro_df['organisation']==organisation]['gld'].values[0]['deliveryAccountableParty']
        return(deliveryaccountableparty)
    except:
        return(None)

def select_extra_bro_metadata_org_env(metadata,organisation,environment):
    for item in metadata[environment]:
        if item['organisation']==organisation:
            return(item)

# =============================================================================
# Data Processing
# =============================================================================

def purge(directory):

    _, _, filenames = next(os.walk(directory))
    
    # for file in filenames:
    #     filepath = os.path.join(directory,file)
    #     os.remove(filepath)
    def rmdir(directory):
        directory = Path(directory)
        for item in directory.iterdir():
            print(item)
            if item.is_dir():
                for subitem in item.iterdir():
                    subitem.unlink()
                item.rmdir()
            else:
                item.unlink()
        #directory.rmdir()
    
    rmdir(Path(directory))

def format_timeseries_metadata(timeseries, locations, organisation, environment):
    
    timeseries['location_uuid']=timeseries['location'].apply(lambda x: x['uuid'])    
    timeseries['location_code']=timeseries['location'].apply(lambda x: x['code'])   
    timeseries['groundwaterstation']=timeseries['location_code'].apply(lambda x: x.split('-')[0])
    timeseries['gld_registration_broid']=timeseries['location_code'].apply(lambda x: locations['broid-gld'][locations['code']==x].values[0])
    timeseries['qualityregime']=timeseries['location_code'].apply(lambda x: locations['qualityregime'][locations['code']==x].values[0])
    timeseries['deliveryaccountableparty']=timeseries['location_code'].apply(lambda x: locations['deliveryaccountableparty'][locations['code']==x].values[0])
    timeseries['procedure'] = timeseries['extra_metadata'].apply(lambda x:  select_extra_bro_metadata_org_env(x['bro'],organisation,environment)['procedure'])
    timeseries['metadata'] = timeseries['extra_metadata'].apply(lambda x:  select_extra_bro_metadata_org_env(x['bro'],organisation,environment)['metadata'])

    return(timeseries)

def format_timeseries_data(tsdata, param, validation_mapping_table, timezone_lizard, timezone_bro, first=False):

    tsdata = tsdata
    tsdata['id']=range(1,len(tsdata)+1)
    tsdata['chunk']=tsdata['id'].apply(lambda x: math.ceil(x/10000))
    tsdata['metadata']=tsdata['flag'].apply(lambda x: {'StatusQualityControl':str(determine_validation_flag_nens(x,validation_mapping_table,param)),
                                                       'interpolationType':'Discontinuous'})
    tsdata['time']=tsdata.index
    tsdata = tsdata[['time','value','metadata']]
    tsdata = tsdata.dropna()            
    #tsdata.index = range(len(tsdata))
    if first == True:
        tsdata = tsdata[tsdata.index==tsdata.index[0]]
    tsdata['time'] = tsdata['time'].apply(lambda x: timezone_lizard.localize(x).astimezone(timezone_bro))
    tsdata[['time','value']] = tsdata[['time','value']].astype(str)
    tsdata['time'] = tsdata['time'].apply(lambda x: str(x).replace(' ','T'))
    return(tsdata)

def edit_records(model, location, start, end, broid_registration, procedure_uuid=None, procedure_initialized=None, validation_status=None, levering_id=None, levering_status=None, comments = None):
    
    defaults = dict(
        date_modified = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
        procedure_uuid = procedure_uuid,
        procedure_initialized = procedure_initialized,
        validation_status = validation_status,
        levering_id = levering_id,
        levering_status = levering_status,
        comments = comments
    )
    
    # I.v.m. het niet onbedoeld overschrijven van al ingevulde attributen.
    if procedure_uuid==None:
        del(defaults['procedure_uuid'])
    if procedure_initialized==None:
        del(defaults['procedure_initialized'])
    if validation_status==None:
        del(defaults['validation_status'])
    if levering_id==None:
        del(defaults['levering_id'])
    if levering_status==None:
        del(defaults['levering_status'])
    if comments==None:
        del(defaults['comments'])
        
    record, created = \
        model.objects.update_or_create(
            location=location,
            start = start,
            end = end,
            broid_registration = broid_registration,
            defaults=defaults
        )


def prepare_sourcedocdata_delivery(model,timeseries, timeseries_id, environment, organisation, lizard_headers, filtercode, param, validation_mapping_table,
                                   timezone_lizard, timezone_bro, sourcedoc_input, procedure, tempdir):
    
    location = timeseries['location_code'][timeseries_id]
    broid = timeseries['gld_registration_broid'][timeseries_id]
            
    sourcedocdata = sourcedoc_input
    sourcedocdata['procedure']=procedure   
    
    abort = False
    
    # Get timeseriesdata
    try:
        tsdata = get_new_timeseriesdata(model, filtercode,timeseries, timeseries_id, environment, organisation, lizard_headers)
    except:
        tsdata = None
        abort = True
        return(timeseries, location, broid, sourcedocdata, tsdata, abort)
    
    # Format timeseriesdata to bro standard
    try:
        tsdata = format_timeseries_data(tsdata, param, validation_mapping_table, timezone_lizard, timezone_bro)
    except Exception as inst:

        info = str(inst)
        abort = True
        return(timeseries, location, broid, sourcedocdata, tsdata, abort)                
    
    return(timeseries, location, broid, sourcedocdata, tsdata, abort)

# =============================================================================
# Conversions / mapping
# =============================================================================

def determine_validation_flag_nens(flag,validation_mapping_table,parameter):
    """
    Parameters
    ----------
    flag : String
        Validation flag from datasource
        
    validation_mapping_table: dict
        Validation mapping table

    parameter : String
        Parameter code from the datasource. 

    Returns
    -------
    The BRO validation status of an observation from the datasource

    """
    
    try:
            
        validation_mapping_table_reg_par = validation_mapping_table[parameter]
        
        if len(validation_mapping_table_reg_par.keys()) == 1:
            validation_status = validation_mapping_table_reg_par[str(list(validation_mapping_table_reg_par.keys())[0])]
        else:
            for flag_id in range(len(validation_mapping_table_reg_par.keys())):
                print(flag_id)
                if flag_id == 0:
                    validation_status = validation_mapping_table_reg_par[str(list(validation_mapping_table_reg_par.keys())[0])]
                
                if int(flag) > int(list(validation_mapping_table_reg_par.keys())[flag_id]):
                    validation_status = validation_mapping_table_reg_par[str(list(validation_mapping_table_reg_par.keys())[flag_id])]
    except:
        
        validation_status = 'onbekend'
    return(validation_status)    

def generate_gld_addition_with_procedure_initialization(model, param, parameters, sourcedoc_input, timeseries, timeseries_id,validation_mapping_table, timezone_lizard, timezone_bro, deliveryAccountableParty,qualityRegime, lizard_headers, obsproc_init=False):
    
    
    sourcedocdata = sourcedoc_input
                           
    ts_uuid = timeseries['uuid'][timeseries_id]
    download = lt.lizard_timeseries_downloader(ts_uuid, lizard_headers)
    print(download.count)
    if download.count == None or download.count== 0:
        # Hier kan niks gedocumenteerd worden in de db. Als het hier fout gaat, heeft de tijdreeks geen events
        payload = 'SKIP'
        filename = 'SKIP'
        tsdata = 'SKIP'
        record_info = 'SKIP'
        return(payload,filename,tsdata,record_info)   
        
    download.execute(10)
    print(download.results)

        
    print(download.results)
        
    
    tsdata = format_timeseries_data(download.results, param, validation_mapping_table, timezone_lizard, timezone_bro, first=True)

    parameter = parameters[param]['status']
    
    broid = timeseries['gld_registration_broid'][timeseries_id]
    location = timeseries['location_code'][timeseries_id]
    tmin = min(tsdata['time']).replace(' ','').replace(':','').replace('-','')
    tmax = max(tsdata['time']).replace(' ','').replace(':','').replace('-','')
    filename = 'GLD_Addition_{}_{}_{}-{}'.format(location.replace('-',''),parameter,tmin.split('+')[0],tmax.split('+')[0])
    
    tsdata_dict = tsdata[['time','value','metadata']].to_dict('records')
    
    sourcedocdata['metadata']['dateStamp']=str(max(tsdata['time']).split('T')[0])
    sourcedocdata['result'] = tsdata_dict
        

        # Hier kan niks gedocumenteerd worden in de db. Als het hier fout gaat, heeft de tijdreeks geen events
        #payload = 'SKIP'
        #filename = 'SKIP'
        #tsdata = 'SKIP'
        #record_info = 'SKIP'
        #return(payload,filename,tsdata,record_info)
    
    start = min(tsdata.index).strftime('%Y-%m-%dT%H:%M:%SZ')
    end = max(tsdata.index).strftime('%Y-%m-%dT%H:%M:%SZ')       
    record_info = {'model':model,'location':location,'start':start,'end':end,'broid':broid}


    sourcedocdata['resultTime']=end
    
    try:
        reg = gwm.gld_registration_request(srcdoc='GLD_Addition', requestReference = filename, deliveryAccountableParty = deliveryAccountableParty, qualityRegime = qualityRegime, broId=broid, srcdocdata=sourcedocdata)
        reg.generate()     
        payload = reg.request
        return(payload, filename, tsdata, record_info)

    except:
  
        edit_records(model, location, start, end, broid, procedure_initialized=True,
                     comments = 'Addition with observation process initialization cannot be generated')
        payload = 'SKIP'
        filename = 'SKIP'
        tsdata = 'SKIP'
        record_info = 'SKIP'
        return(payload, filename, tsdata, record_info)

# =============================================================================
# Lizard api
# =============================================================================
def get_timeseries_extraparameters(timeseries,timeseries_id,environment,organisation):
    for item in timeseries['extra_metadata'][timeseries_id]['bro'][environment]:
        if item['organisation']==organisation:
            metadata_parameters = item['metadata']
            procedure_parameters = item['procedure']['parameters']
    return(metadata_parameters, procedure_parameters)

@transaction.atomic
def get_selected_locations_lizard(lizard_headers):
    
    url = 'https://brabant.lizard.net/api/v4/locations/?organisation__uuid=c152eb2647d74444956c15da0dcf5464'
    download = lt.lizard_api_downloader(url = url, headers = lizard_headers, page_size = 50)
    download.execute(10)
    locations = download.results
        
    # Select locations with gmw bro-id in Lizard:
    locations['broid-gmw'] = locations['extra_metadata'].apply(lambda x: get_broid_gmw(x,'demo','nens'))
    locations['broid-gld'] = locations['extra_metadata'].apply(lambda x: get_broid_gld(x,'demo','nens'))
    locations['qualityregime'] = locations['extra_metadata'].apply(lambda x: get_qualityregime_gld(x,'demo','nens'))
    locations['deliveryaccountableparty'] = locations['extra_metadata'].apply(lambda x: get_deliveryaccountableparty_gld(x,'demo','nens'))
    
    return(locations)

@transaction.atomic
def get_selected_timeseries_lizard(param,locations,organisation,environment, lizard_headers):
    url = 'https://brabant.lizard.net/api/v4/timeseries/?location__organisation__uuid=c152eb2647d74444956c15da0dcf5464&observation_type__code={}'.format(param)
    download = lt.lizard_api_downloader(url = url, headers = lizard_headers, page_size = 50)
    download.execute(10)
    timeseries = download.results
    timeseries = format_timeseries_metadata(timeseries, locations, organisation, environment)

    # Alleen voor tijdreeksen met een BRO GLD ID kan aanlevering plaatsvinden    
    timeseries = timeseries[timeseries['gld_registration_broid'].isnull()==False]

    timeseries.index = range(len(timeseries))
    return(timeseries)

def patch_timeseries_extra_metadata_lizard(procedure_id,timeseries,timeseries_id,environment,organisation,lizard_headers):
            
    for item in  timeseries['extra_metadata'][timeseries_id]['bro'][environment]:
        if item['organisation']==organisation:

            item['procedure']['id'] = procedure_id

            req = requests.patch(url = 'https://brabant.lizard.net/api/v4/timeseries/{}/'.format(timeseries['uuid'][timeseries_id]),data=json.dumps({'extra_metadata':
                                    timeseries['extra_metadata'][timeseries_id]}), headers = lizard_headers) 

            req.json()
            return(timeseries)

def get_new_timeseriesdata(model, filtercode, timeseries, timeseries_id, environment, organisation, lizard_headers):
    
    startdate = None
    enddates = []
    for item in model.objects.filter(location=filtercode):
        enddates.append(getattr(item,'end'))
    if len(enddates) > 0:
        startdate=max(enddates)     
    
    ts_uuid = timeseries['uuid'][timeseries_id]
    
    if startdate == None:
         lt.lizard_timeseries_downloader(ts_uuid, lizard_headers)
         download = lt.lizard_timeseries_downloader(ts_uuid, lizard_headers)
         download.execute(10)
    else:
 
         real_startdate = datetime.datetime.strftime(datetime.datetime.strptime(startdate,'%Y-%m-%dT%H:%M:%SZ')+datetime.timedelta(0, 1),'%Y-%m-%dT%H:%M:%SZ')
         download = lt.lizard_timeseries_downloader(ts_uuid, lizard_headers, startdate=real_startdate)
         download.execute(10)    
     
    return(download.results)

# =============================================================================
# Bronhouderportaal api exchange
# =============================================================================

def initialize_procedure(timeseries,timeseries_id,param,parameters,sourcedoc_input,validation_mapping_table, timezone_lizard, timezone_bro, deliveryAccountableParty, qualityRegime, lizard_headers, acces_token_bro_portal, environment, organisation, model):

    
    payload, filename, tsdata, record_info = generate_gld_addition_with_procedure_initialization(model, param, parameters, sourcedoc_input, timeseries, timeseries_id,validation_mapping_table, timezone_lizard, timezone_bro, deliveryAccountableParty,qualityRegime, lizard_headers, obsproc_init=True) 
    print(filename)
    if filename == 'SKIP':    
       
        return(timeseries, {'Error':{'message':'Error: Something went wrong in generating sourcedocument GLD addition with observation process initialization',
                          'errors':[]}},record_info)                
    try:
        # Haal het procedure id op alvast
        procedure_id = xmltodict.parse(payload)['registrationRequest']['sourceDocument']['GLD_Addition']['observation']['om:OM_Observation']['om:procedure']['wml2:ObservationProcess']['@gml:id']        
    except:
        edit_records(model, record_info['location'], record_info['start'],
                     record_info['end'], record_info['broid'],
                     procedure_initialized=True,
                     comments= 'An error occured while trying to obtain the procedure id from xml document, addition with observation process initialisation')  
          
        return(timeseries, {'Error':{'message':'Error: problems while retrieving request info of GLD addition with observation process initialization',
                          'errors':[filename]}},record_info)   
        
    # VALIDATE REQUEST
    try:
        validation_info = gwm.validate_sourcedoc(payload, acces_token_bro_portal, demo=True)
        check = validation_info['status']
    except:
        edit_records(model, record_info['location'], record_info['start'],
                     record_info['end'], record_info['broid'],
                     procedure_initialized=True,
                     comments = 'Validation proces of addition request with observation process initialization crashed')
        return(timeseries, {'Error':{'message':'Error: Something went wrong while validating sourcedocument GLD addition with observation process initialization',
                         'errors':[filename]}},record_info)           
    
    if validation_info['status']!='VALIDE':
        edit_records(model, record_info['location'], record_info['start'],
                     record_info['end'], record_info['broid'],validation_status=validation_info['status'],
                     procedure_initialized=True,
                     comments = 'Generated addition request with observation process initialization is not valid')
        return(timeseries, {'Error':{'message':'Error: GLD addition document with observation process initialization is not valid',
                          'errors':[filename,validation_info]}},record_info)


    else:
        
        try:
        
            # UPLOAD REQUEST
            req = {filename.split('.')[0]:payload}
            
            if environment == 'demo':
                demo = True
            else:
                demo = False
    
            upload_info_1 = gwm.upload_sourcedocs_from_dict(req, acces_token_bro_portal, demo=demo)
        
        except:
            edit_records(model, record_info['location'], record_info['start'],
                         record_info['end'], record_info['broid'],validation_status=validation_info['status'],
                         procedure_initialized=True,
                         comments = 'Error raised during uploading of addition request with observation process initialization')            
            return(timeseries, {'Error':{'message':'Error: GLD addition document with observation process initialization, upload crashed',
                              'errors':[filename,validation_info['status']]}},record_info)                 
        
        # Register current record info
        edit_records(model, record_info['location'], record_info['start'],
                     record_info['end'], record_info['broid'],validation_status=validation_info['status'],
                     procedure_initialized=True,
                     levering_id=upload_info_1.json()['identifier'],                    
                     comments = None)  

        # Aangezien nu een levering gepost is, moet het procedure_id naar Lizard
        timeseries['procedure'][timeseries_id]['id']=procedure_id 
        
        # WAIT
        time.sleep(10)
        
        try:
            upload_info_2 = gwm.check_delivery_status(upload_info_1.json()['identifier'], acces_token_bro_portal, demo=demo)
        except:
            timeseries['procedure'][timeseries_id]['id']=procedure_id+'_failed'            
            edit_records(model, record_info['location'], record_info['start'],
                         record_info['end'], record_info['broid'],validation_status=validation_info['status'],
                         levering_id=upload_info_1.json()['identifier'],
                         procedure_uuid=procedure_id+'_failed',
                         procedure_initialized=True,
                         comments = 'Error raised during status request of already delivered upload')             
            return(timeseries, {'Error':{'message':'Error raised during status request of already delivered upload (GLD addition observation process initialisation)',
                              'errors':[filename,validation_info['status']]}},record_info)   
             
        
        if upload_info_2.json()['status']=='DOORGELEVERD' and upload_info_2.json()['brondocuments'][0]['status']=='OPGENOMEN_LVBRO':
            edit_records(model, record_info['location'], record_info['start'],
                         record_info['end'], record_info['broid'],validation_status=validation_info['status'],
                         levering_id=upload_info_2.json()['identifier'],
                         levering_status=upload_info_2.json()['status'],
                         procedure_uuid=procedure_id,
                         procedure_initialized=True)                   
            timeseries['procedure'][timeseries_id]['id']=procedure_id
            return(timeseries, {'Pass':True},record_info)
                    
                    
        else:
            timeseries['procedure'][timeseries_id]['id']=procedure_id+'_failed'                        
            edit_records(model, record_info['location'], record_info['start'],
                         record_info['end'], record_info['broid'],validation_status=validation_info['status'],
                         levering_id=upload_info_2.json()['identifier'],
                         procedure_uuid=procedure_id+'_failed',
                         levering_status=upload_info_2.json()['status'],
                         procedure_initialized=True)                     
                
            return(timeseries, {'Error':{'message':'GLD addition document with observation process initialization failed',
                              'errors':[filename,upload_info_2.json()['status'],upload_info_2.json()['brondocuments'][0]['status']]}}, record_info)                    
 
                         


def retrieve_procedure(timeseries,timeseries_id, param,parameters,sourcedoc_input,validation_mapping_table, timezone_lizard,
                       timezone_bro, deliveryAccountableParty, qualityRegime, lizard_headers, acces_token_bro_portal,
                       environment, organisation,model):
    
    procedure_id = timeseries['procedure'][timeseries_id]['id']
    skip = False
    
    if procedure_id == None:
        print('No procedure id found yet, generating gld addition with procedure initialisation ...')
    
        timeseries, errors, record_info = initialize_procedure(timeseries,timeseries_id,param,parameters,sourcedoc_input,validation_mapping_table, timezone_lizard, timezone_bro, deliveryAccountableParty, qualityRegime, lizard_headers, acces_token_bro_portal,environment, organisation, model)
        if 'Error' in errors.keys():
            print(errors)
            procedure = None
            skip = True
            return(timeseries, procedure, skip)

        try:
            procedure_id = timeseries['procedure'][timeseries_id]['id']
            patch_timeseries_extra_metadata_lizard(procedure_id,timeseries,timeseries_id,environment,organisation,lizard_headers)
        
        except:
            skip = True
            procedure=None
            edit_records(model, record_info['location'], record_info['start'],
                         record_info['end'], record_info['broid'], comments = 'Procedure id cannot be patched to Lizard') 
            return(timeseries, procedure, skip)  
    
    # Detecteren of de addition met observation_proces_initialization wel goed is gegaan (in het geval van failed niet), direct overslaan:
    # Je kan nu niet verder met het aanleveren van opvolgende chunks in deze reeks
    if '_failed' in procedure_id:
        logging['procedure_initialization_errors']+=[{'parameter':param, 'error':'unsolved procedure initialization error from previous run is still unsolved', 'info':None}]
        skip = True
        procedure = None
        return(timeseries, procedure, skip)      
    
    else:
        print('Procedure retrieved: {}'.format(procedure_id))
        return(timeseries, procedure_id, skip)

#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
def deliver_sourcedoc_addition(model, tsdata_chunk, timeseries, timeseries_id, location, param,parameters,deliveryAccountableParty,qualityRegime, broid,sourcedocdata ,tempdir, acces_token_bro_portal, lizard_headers, procedure, environment, organisation):
    
    start = min(tsdata_chunk.index).strftime('%Y-%m-%dT%H:%M:%SZ')
    end = max(tsdata_chunk.index).strftime('%Y-%m-%dT%H:%M:%SZ')  

    try:
        # GENERATE REQUEST
        parameter = parameters[param]['status']
    
        #frame = pd.DataFrame(tsdata_chunk)
        tmin = min(tsdata_chunk['time']).split('+')[0].replace(' ','').replace(':','').replace('-','')
        tmax = max(tsdata_chunk['time']).split('+')[0].replace(' ','').replace(':','').replace('-','')
        filename = '{}_{}_{}-{}'.format(location.replace('-',''),parameter,tmin,tmax)
        
        sourcedocdata['result'] = tsdata_chunk.to_dict('records')
        sourcedocdata['metadata']['dateStamp']=str(max(tsdata_chunk['time']).split('T')[0])
        sourcedocdata['resultTime']=str(max(tsdata_chunk['time']))
        
        reg = gwm.gld_registration_request(srcdoc='GLD_Addition', requestReference = filename, deliveryAccountableParty = deliveryAccountableParty, qualityRegime = qualityRegime, broId=broid, srcdocdata=sourcedocdata)
        reg.generate()
    
        payload = reg.request
    
    except:
        edit_records(model, location, start, end, broid, procedure_initialized=False,procedure_uuid=procedure,
                     comments = 'Addition request cannot be generated')                
        return(timeseries, {'Error':{'message':'Error: something went wrong in generating sourcedocument GLD addition',
                         'errors':[]}})
           
    # VALIDATE REQUEST
    try:
        validation_info = gwm.validate_sourcedoc(payload, acces_token_bro_portal, demo=True)
        check = validation_info['status']
        print(check)

    except:
        edit_records(model, location, start, end, broid, procedure_initialized=False,procedure_uuid=procedure,
                     comments = 'Validation proces of addition request crashed')           
        return(timeseries, {'Error':{'message':'Error: Something went wrong in validating sourcedocument GLD addition',
                         'errors':[filename]}})           
    
    if validation_info['status']!='VALIDE':
        edit_records(model, location, start, end, broid, procedure_initialized=False,procedure_uuid=procedure,
                     validation_status=validation_info['status'],
                     comments = 'Generated addition request is not valid')   
 
        return(timeseries, {'Error':{'message':'Error: GLD addition document is not valid',
                         'errors':[filename,validation_info]}})
    
    else:
        
        try:
        
            # UPLOAD REQUEST
            req = {filename.split('.')[0]:payload}
            
            if environment == 'demo':
                demo = True
            else:
                demo = False
    
            upload_info_1 = gwm.upload_sourcedocs_from_dict(req, acces_token_bro_portal, demo=demo)
            identifier = upload_info_1.json()['identifier']
            
            # Alvast bijwerken dat het document wel valide is
            edit_records(model, location, start, end, broid, procedure_initialized=False,procedure_uuid=procedure,
                         validation_status=validation_info['status'],
                         levering_id=identifier
                         )      
        except:
            edit_records(model, location, start, end, broid, procedure_initialized=False,procedure_uuid=procedure,
                         validation_status=validation_info['status'],
                         comments = 'Error raised during uploading of addition request'
                         )   
            return(timeseries, {'Error':{'message':'Error: GLD addition document, upload crashed',
                              'errors':[filename,validation_info['status']]}})                 
                
        return(timeseries, {'Pass':True})


def status_check_addition_delivery(model, location, start, end, broid, identifier, acces_token_bro_portal, environment):
    
    if environment == 'demo':
        demo = True
    else:
        demo = False        

    try:    
        # CHECK AND STORE
        upload_info = gwm.check_delivery_status(identifier, acces_token_bro_portal, demo=demo)  
    except:
        edit_records(model, location, start, end, broid,
                     comments = 'Error raised during retrieving status of addition request (downloading)'
                     )
        return('Failed')         
        
    try:
        if upload_info.json()['status']=='DOORGELEVERD' and upload_info.json()['brondocuments'][0]['status']=='OPGENOMEN_LVBRO':   
            edit_records(model, location, start, end, broid,levering_status=upload_info.json()['status']
                         )            
            return('Delivered')
    
        else:
            edit_records(model, location, start, end, broid,levering_status=upload_info.json()['status'] )           
            return(upload_info.json()['status'])

    except:
        edit_records(model, location, start, end, broid,
                     comments = 'Error raised during retrieving status of addition request (expanding text)'
                     )
        return('Pending')   
    

def upload_new_timeseries_data(timeseries, environment, organisation, lizard_headers, timezone_lizard, timezone_bro, param, 
                               validation_mapping_table, tempdir, parameters, 
                               acces_token_bro_portal,model):
    
    notifications = {}
    
    groundwaterstations = list(timeseries['groundwaterstation'].unique())

    for groundwaterstation in groundwaterstations:
        #if groundwaterstation == 'B43D0017':
        #print(groundwaterstation)
        records = {}
        filters = list(timeseries['location_code'][timeseries['groundwaterstation']==groundwaterstation].values)
        
        for filtercode in filters:
            #if filtercode == 'B44C0113-006':
            if filtercode not in list(timeseries['location_code'].values):
                continue
            timeseries_id = timeseries[timeseries['location_code']==filtercode].index[0]
            print(filtercode, timeseries_id)
            records[filtercode]=pd.DataFrame()
            
            metadata_parameters, procedure_parameters = get_timeseries_extraparameters(timeseries,timeseries_id,environment,organisation)
            
            sourcedoc_input ={'metadata':metadata_parameters,
                                    'procedure':{'parameters':procedure_parameters}, 
                                    'result':None, 
                                    }
            
            qualityRegime=timeseries['qualityregime'][timeseries_id]
            deliveryAccountableParty=timeseries['deliveryaccountableparty'][timeseries_id]
            
            # Get or initialize observation process (procedure) if needed
            timeseries, procedure, skip =retrieve_procedure(timeseries,timeseries_id, param,parameters,deepcopy(sourcedoc_input),validation_mapping_table, 
                                                                              timezone_lizard, timezone_bro, deliveryAccountableParty, qualityRegime, 
                                                                              lizard_headers, acces_token_bro_portal, 
                                                                              environment, organisation,model)                 
            print(skip)
            # Problemen bij aanmaken of ophalen observationprocess? -> skip de additions voor deze filter
            if skip == True:   
                notifications[filtercode]=['Procedure not obtained or initialisation failed']
                continue

            # Prepare required sourcedocdata
            timeseries, location, broid, sourcedocdata, tsdata, abort= prepare_sourcedocdata_delivery(model,timeseries, 
                                            timeseries_id, environment, organisation, lizard_headers, 
                                            filtercode, param, validation_mapping_table,
                                            timezone_lizard, timezone_bro, deepcopy(sourcedoc_input), procedure, tempdir)
            # If something went wrong, abort sourcedoc creation
            if abort == True:
                notifications[filtercode]=['Formatting of timeseriesdata to upload failed']
                continue
        
            #Create and validate and upload sourcedocument(s)
            nr_chunks = math.ceil(len(tsdata)/1000)
            for i in range(nr_chunks):
                print(i)
                tsdata_chunk = tsdata[i*1000:((i+1)*1000)-1]
                timeseries, errors = deliver_sourcedoc_addition(model, tsdata_chunk, timeseries, timeseries_id, location, param,parameters,deliveryAccountableParty,qualityRegime, broid,sourcedocdata ,tempdir, acces_token_bro_portal, lizard_headers, procedure, environment, organisation)
                
                if 'Error' not in errors.keys():
                    print('Upload succesful')
                else:
                    print('Upload failed')
            print('finished uploading for gmw {}'.format(groundwaterstation) )
            
            
        time.sleep(10)
        # Statuscheck subsequently
        for filtercode in filters:
            timeseries_id = timeseries[timeseries['location_code']==filtercode].index[0]
            metadata_parameters, procedure_parameters = get_timeseries_extraparameters(timeseries,timeseries_id,environment,organisation)
            sourcedoc_input ={'metadata':metadata_parameters,
                        'procedure':{'parameters':procedure_parameters}, 
                        'result':None, 
                        }
                
            qualityRegime=timeseries['qualityregime'][timeseries_id]
            deliveryAccountableParty=timeseries['deliveryaccountableparty'][timeseries_id]
            broid = timeseries['gld_registration_broid'][timeseries_id]
            ts_uuid = timeseries['uuid'][timeseries_id]
            location = timeseries['location_code'][timeseries_id]

            
            for item in model.objects.filter(location=filtercode,broid_registration=broid).exclude(levering_status='DOORGELEVERD'):
                identifier = getattr(item,'levering_id')
                start = getattr(item,'start')
                end = getattr(item,'end')
                procedure_initialized = getattr(item, 'procedure_initialized')            
                procedure = getattr(item, 'procedure_uuid')
                print(type(procedure_initialized))
                status = status_check_addition_delivery(model, filtercode, start, end, broid, identifier,acces_token_bro_portal,environment)
                print('status {}: {}'.format(identifier,status))
                
                #1) Mislukte gevalideerde bestanden er uithalen en opnieuw leveren
                validatiestatus = getattr(item,'validation_status')
                #if validatiestatus != 'VALIDE' and procedure_initialized=='False':
                if identifier==None:

                    sourcedocdata = sourcedoc_input
                    sourcedocdata['procedure']=procedure  
                    download = lt.lizard_timeseries_downloader(ts_uuid, lizard_headers, startdate=start, enddate=end)
                    download.execute(10)  
                    tsdata = download.results
                    tsdata_chunk = format_timeseries_data(tsdata, param, validation_mapping_table, timezone_lizard, timezone_bro)
                    timeseries, errors = deliver_sourcedoc_addition(model, tsdata_chunk, timeseries, timeseries_id, location, param,parameters,deliveryAccountableParty,qualityRegime, broid,sourcedocdata ,tempdir, acces_token_bro_portal, lizard_headers, procedure, environment, organisation)
                    
                    if 'Error' not in errors.keys():
                        print('Upload succesful')
                    else:
                        print('Upload failed')
                    
                    #time.sleep(10)
                    #status = status_check_addition_delivery(model, filtercode, start, end, broid, identifier,acces_token_bro_portal,environment)


        print('finished retrieveing statuses for gmw {}'.format(groundwaterstation) )

    return(timeseries, logging)


#%%

def run_gld_add_rec(organisation, environment, tempdir,validation_mapping_table, lizard_headers, acces_token_bro_portal):

#%%
    
    # Timezone standards
    timezone_lizard = pytz.timezone("UTC")
    timezone_bro = pytz.timezone("Europe/Amsterdam")
        
    # Get selected locations from Lizard
    print('Download location metadata from Lizard ...')
    locations = get_selected_locations_lizard(lizard_headers)
    print(locations['broid-gld'].unique())

    # Define parameters
    parameters = {'WNS9040':{'status':'voorlopig','observationtype':'reguliereMeting'},'WNS9040.hand':{'status':None,'observationtype':'controlemeting'}}

    #%% Itterate over parameters:
       
    for param in parameters.keys():
                
        purge(tempdir)
        
        #%% Get model
        model = model_translation[param]
        print(model)
        
        #%% Get all timeseries for organisation and selected parameter
        print('Download timeseries metadata from Lizard (parameter = {}) ...'.format(param))
        timeseries = get_selected_timeseries_lizard(param,locations,organisation,environment, lizard_headers)
        print(timeseries)
        #%% Nieuwe tijdreeksdata in Lizard naar BRO verzenden, statusrequest ophalen
        
        upload_new_timeseries_data(timeseries, environment, organisation, lizard_headers, timezone_lizard, timezone_bro, param, 
                                         validation_mapping_table, tempdir, parameters, 
                                         acces_token_bro_portal,model)        
        
        
        
        # timeseries, logging = upload_new_timeseries_data(timeseries, environment, organisation, lizard_headers, timezone_lizard, timezone_bro, param, 
        #                                 validation_mapping_table, tempdir, parameters, 
        #                                 acces_token_bro_portal)
        

        
        #%% Status controleren van aangeleverde data
        

class Command(BaseCommand):       
     
    def handle(self, *args, **options):
        #print(NENS_DEMO_SETTINGS)
        
        organisation = NENS_DEMO_SETTINGS['organisation']
        environment = NENS_DEMO_SETTINGS['env']
        tempdir = NENS_DEMO_SETTINGS['failed_dir_gld_addition']
        lizard_headers = NENS_DEMO_SETTINGS['lizard_headers']
        acces_token_bro_portal = NENS_DEMO_SETTINGS['acces_token_bro_portal']
        validation_mapping_table = NENS_DEMO_SETTINGS['validation_mapping_table']
        
        #try:
        run_gld_add_rec(organisation, environment, tempdir, validation_mapping_table, lizard_headers, acces_token_bro_portal)
        #except:
        #    sys.exit('FAILED')
        
        
        
        
