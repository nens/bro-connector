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
import logging

from provincie_zeeland_gld.settings import GLD_AANLEVERING_SETTINGS
from gld_aanlevering.models import GroundwaterMonitoringWells, GroundwaterMonitoringTubes, gld_registration_log, aanleverinfo_filters, GroundwaterLevelDossier


def validate_request(payload,env,acces_token_bro_portal):
    
    if env == 'demo':
        demo = True
    else:
        demo = False
    
    validation_info = gwm.validate_sourcedoc(payload, acces_token_bro_portal, demo=demo)

    print(validation_info['status']+'\n')
    try:
        
        print('ERRORS:')
        for error in validation_info['errors']:
            print(error+'\n')
    except:
        None
    
    return(validation_info)

def gld_start_registration(qualityregime, 
                           deliveryaccountableparty,
                           broidgmw, 
                           filtrnr, 
                           failed_dir, 
                           acces_token_bro_portal,
                           organisation,
                           env, 
                           locationcode,
                           date_modified, 
                           monitoringnetworks=None):

    """
    Start a GLD registration
    """
    
    if qualityregime==None or deliveryaccountableparty==None:
        record, created = \
            gld_registration_log.objects.update_or_create(
                gwm_bro_id=broidgmw,
                filter_id=filtrnr,
                date_modified = date_modified,
                defaults=dict(
                    validation_status = None,
                    levering_id = None,
                    levering_status = None,
                    comments = 'Registratierequest kan niet worden aangemaakt, qualityregime en / of deliveryaccountableparty niet opgegeven'
                )
            )
            
        return
            
    try:
        monitoringpoints = [{'broId':broidgmw,
                       'tubeNumber':filtrnr}]
        
        if monitoringnetworks == None:
            
            srcdocdata =  {'objectIdAccountableParty':'Meetpunt1',
                'monitoringPoints':monitoringpoints,        
                } 
        else:
            srcdocdata =  {'objectIdAccountableParty':'Meetpunt1',
                'groundwaterMonitoringNets':monitoringnetworks, #
                'monitoringPoints':monitoringpoints,        
                } 
            
        reg = gwm.gld_registration_request(srcdoc='GLD_StartRegistration', 
                                           requestReference = 'GLD_StartRegistration_{}_tube_{}'.format(broidgmw,str(filtrnr)), 
                                           deliveryAccountableParty = deliveryaccountableparty, 
                                           qualityRegime = qualityregime, 
                                           srcdocdata=srcdocdata)
        
        reg.generate()
        payload = reg.request
        
        validation_info = validate_request(payload,env,acces_token_bro_portal)  
                
    except:
    
        record, created = \
            gld_registration_log.objects.update_or_create(
                gwm_bro_id=broidgmw,
                filter_id=filtrnr,
                date_modified = date_modified,
                defaults=dict(
                    validation_status = None,
                    levering_id = None,
                    levering_status = None,
                    comments = 'Genereren / valideren registratierequest gefaald'
                )
            )
            
        return

    if validation_info['status']=='VALIDE':
        
        try:
            req = {'{}.xml'.format('GLD_StartRegistration_{}_tube_{}'.format(broidgmw,str(filtrnr)).format(broidgmw)):payload}
            
            if env == 'demo':
                demo = True
            else:
                demo = False
    
            upload_info = gwm.upload_sourcedocs_from_dict(req, acces_token_bro_portal, demo=demo)
            
                                
            record, created = \
                gld_registration_log.objects.update_or_create(
                    gwm_bro_id=broidgmw,
                    filter_id=filtrnr,
                    date_modified = date_modified,
                    defaults=dict(
                        validation_status=validation_info['status'],
                        levering_id = upload_info.json()['identifier'],
                        levering_status = upload_info.json()['status'],
                        comments = 'Valideren registratierequest geslaagd'
                    )
                )
                

            return

        except:
        
            record, created = \
                gld_registration_log.objects.update_or_create(
                    gwm_bro_id=broidgmw,
                    filter_id=filtrnr,
                    date_modified = date_modified,
                    defaults=dict(
                        validation_status = validation_info['status'],
                        levering_id = None,
                        levering_status = None,
                        comments = 'Leveren startregistratierequest mislukt'
                    )
                )
    
    else:
    
        if os.path.exists(failed_dir) == False:
            os.makedirs(failed_dir)        
        reg.write_xml(output_dir = failed_dir, filename = '{}.xml'.format('GLD_StartRegistration_{}_tube_{}'.format(broidgmw,str(filtrnr)).format(broidgmw)))
        
        record, created = \
            gld_registration_log.objects.update_or_create(
                gwm_bro_id=broidgmw,
                filter_id=filtrnr,
                date_modified = date_modified,
                defaults=dict(
                    validation_status = validation_info['status'],
                    levering_id = None,
                    levering_status = None,
                    comments = 'Startregistratierequest niet valide'
                )
            )
                 

def check_delivery_status_levering(gld_registration):

    if GLD_AANLEVERING_SETTINGS['env'] == 'demo':
        demo=True
    else:
        demo=False
        
    upload_info = gwm.check_delivery_status(gld_registration.levering_id, 
                                            GLD_AANLEVERING_SETTINGS['acces_token_bro_portal'], 
                                            demo)       
    try:
    
        if upload_info.json()['status']=='DOORGELEVERD' and upload_info.json()['brondocuments'][0]['status']=='OPGENOMEN_LVBRO':
            
            record, created = \
                gld_registration_log.objects.update_or_create(
                    id=gld_registration.id,
                    defaults=dict(
                        gld_bro_id=upload_info.json()['brondocuments'][0]['broId'],
                        levering_status = upload_info.json()['brondocuments'][0]['status'],
                        last_changed = upload_info.json()['lastChanged'],
                        comments = 'Startregistratierequest succesvol doorgeleverd'
                    )
                )
                
        else:
        
            record, created = \
                gld_registration_log.objects.update_or_create(
                    id=gld_registration.id,
                    defaults=dict(
                        levering_status = upload_info.json()['status'],
                        last_changed = upload_info.json()['lastChanged'],
                        comments = 'Startregistratierequest nog niet doorgeleverd'
                    )
                )

    except Exception as e:    
        record, created = \
                gld_registration_log.objects.update_or_create(
                    id=gld_registration.id,
                    defaults=dict(
                        comments = 'Fout bij ophalen status levering: {}'.format(e)
                    )
                )                   


def run_gld_initial_registration(acces_token_bro_portal,
                                 organisation,
                                 env,
                                 monitoringnetworks, 
                                 failed_dir, 
                                 expiration_log_messages):
    
    """
    Run GLD registration for all monitoring wells in the database   
    Registrations are validated first
    """
    
    gmw_tubes = GroundwaterMonitoringTubes.objects.all()
    gmw_tubes_df = pd.DataFrame(list(gmw_tubes.values()))            
    date_modified = datetime.datetime.now()
        
    # Register the monitoring wells
    # Loop over all GMW objects in the database
    for i, tube in gmw_tubes_df.iterrows():
                
        # Get corresponding well ID 
        registration_object_id = tube['registration_object_id']
        gmw_well = GroundwaterMonitoringWells.objects.get(registration_object_id=registration_object_id)
        
        # Check if well/tube already has a registration from this day?
        location_metadata_bro_gld = gld_start_registration(gmw_well.quality_regime, 
                                                           str(gmw_well.delivery_accountable_party), 
                                                           gmw_well.bro_id, 
                                                           int(tube['tube_number']), 
                                                           failed_dir, 
                                                           acces_token_bro_portal,
                                                           organisation,
                                                           env, 
                                                           gmw_well.nitg_code, 
                                                           date_modified, 
                                                           monitoringnetworks)
        
        break
        
            
                    
        
def check_delivery_status_initial_gld_registrations():
    
    """
    Check the delivery status of all currently deliverd gld registrations
    Update the registration if the status has changed
    """
    # 2) GLD STARTREGISTRATION DELIVERY CHECK
    # Loop over all gld registrations
    gld_registrations = gld_registration_log.objects.all()
    
    for gld_registration in gld_registrations:
        
        gld_bro_id = gld_registration.gld_bro_id
        validation_status = gld_registration.validation_status
        levering_id = gld_registration.levering_id
                
        if gld_bro_id is None and validation_status == 'VALIDE' and levering_id is not None:
            print(f'Checking levering with ID: {gld_registration.levering_id}')
            check_delivery_status_levering(gld_registration)
        elif gld_bro_id is not None and gld_registration.levering_status == 'OPGENOMEN_LVBRO':
            
            print(f'Checking if GLD research is added to database: {gld_bro_id}')
            # Check if the GLD id is in the GLD schema database            
            if GroundwaterLevelDossier.objects.filter(gld_bro_id=gld_bro_id).count() == 0:
                
                # If validation is succesfull and GLD id not present in database yet, also start GLD registration in GLD schema
                research_start_date = datetime.datetime.now().date()
                            
                record = GroundwaterLevelDossier.objects.create(
                    gmw_bro_id=gld_registration.gwm_bro_id,
                    groundwater_monitoring_tube_id=gld_registration.filter_id,
                    gld_bro_id=gld_bro_id,
                    research_start_date=research_start_date.isoformat())  
            
    
class Command(BaseCommand):
    help = """Custom command for import of GIS data."""
            
    def handle(self, *args, **options):
       
        acces_token_bro_portal = GLD_AANLEVERING_SETTINGS['acces_token_bro_portal']
        organisation = GLD_AANLEVERING_SETTINGS['organisation']
        env = GLD_AANLEVERING_SETTINGS['env']
        monitoringnetworks = GLD_AANLEVERING_SETTINGS['monitoringnetworks']
        failed_dir = GLD_AANLEVERING_SETTINGS['failed_dir_gld_registration']
        expiration_log_messages = GLD_AANLEVERING_SETTINGS['expiration_log_messages']
           
        # Run the initial registration of all GMW objects in the database
        # run_gld_initial_registration(acces_token_bro_portal,
        #                   organisation,
        #                   env,
        #                   monitoringnetworks,
        #                   failed_dir, 
        #                   expiration_log_messages)
        
        # Check the status of deliveries
        check_delivery_status_initial_gld_registrations()