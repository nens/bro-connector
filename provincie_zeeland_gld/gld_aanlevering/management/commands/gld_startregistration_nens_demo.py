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
from gld_aanlevering.models import GroundwaterMonitoringWells, GroundwaterMonitoringTubes, gld_registration_log, aanleverinfo_filters


#%% Functions

# =============================================================================
# 2. BRO
# =============================================================================

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

def gld_start_registration(qualityregime, deliveryaccountableparty,broidgmw, filtrnr, failed_dir, acces_token_bro_portal,organisation,env, locationcode,date_modified, monitoringnetworks=None):

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
            
        reg = gwm.gld_registration_request(srcdoc='GLD_StartRegistration', requestReference = 'GLD_StartRegistration_{}_tube_{}'.format(broidgmw,str(filtrnr)), deliveryAccountableParty = deliveryaccountableparty, qualityRegime = qualityregime, srcdocdata=srcdocdata)
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
                    location=locationcode,
                    date_modified = date_modified,
                    defaults=dict(
                        validation_status = upload_info.json()['validatiestatus'],
                        levering_id = upload_info.json()['identifier'],
                        levering_status = validation_info['status'],
                        comments = 'Valideren registratierequest geslaagd'
                    )
                )

            return
            #location_metadata_bro_gld['levering_id']=upload_info.json()['identifier']

            # Als het goed gaat, geen update nodig
            #TODO location metadata naar database
            #return(location_metadata_bro_gld)    

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
            # Todo location metadata naar database
            #return(location_metadata_bro_gld)    
    
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
         
        #TODO metadata naar database
        #return(location_metadata_bro_gld)  
        
        
        

def run_gld_reg_init(acces_token_bro_portal,
                     organisation,
                     env,
                     monitoringnetworks, 
                     failed_dir, 
                     expiration_log_messages):
    
    """
    Run GLD registration for all monitoring wells in the database    
    """
    
    gmw_tubes = GroundwaterMonitoringTubes.objects.all()
    gmw_tubes_df = pd.DataFrame(list(gmw_tubes.values()))            
    date_modified = datetime.datetime.now().date()
        
    # 1) GLD STARTREGISTRATION CREATION
    for i, tube in gmw_tubes_df.iterrows():
        
        # Get corresponding well ID 
        registration_object_id = tube['registration_object_id']
        gmw_well = GroundwaterMonitoringWells.objects.get(registration_object_id=registration_object_id)
        
        # Check if well/tube already has a registration
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
            
                    
        
        
    # 2) GLD STARTREGISTRATION DELIVERY CHECK
    
    for i, tube in gmw_tubes_df.iterrows():
        
        registration_object_id = tube['registration_object_id']
        gmw_well = GroundwaterMonitoringWells.objects.get(registration_object_id=registration_object_id)
        
        # Get the registration logging
        gld_registration = gld_registration_log.get(gwm_bro_id=gmw_well.bro_id, filter_id=tube['tube_number'], date_modified=date_modified)
        
        if gld_registration.gld_bro_id is None and gld_registration.validation_status == 'VALIDE' and gld_registration.levering_id is None:
            
                print('Checking delivery status of gld registration {}'.format(gmw_well.bro_id))

                if env == 'demo':
                    demo = True
                else:
                    demo = False
                
                identifier = gld_registration.levering_id
                upload_info = gwm.check_delivery_status(identifier, acces_token_bro_portal, demo=demo)   
                
                
                try:
                
                    if upload_info.json()['status']=='DOORGELEVERD' and upload_info.json()['brondocuments'][0]['status']=='OPGENOMEN_LVBRO':
                        
                        record, created = \
                            gld_registration_log.objects.update_or_create(
                                gwm_bro_id=gmw_well.bro_id,
                                filter_id=tube['tube_number'],
                                date_modified = date_modified,
                                defaults=dict(
                                    gld_bro_id=upload_info.json()['brondocuments'][0]['broId'],
                                    levering_status = upload_info.json()['brondocuments'][0]['status'],
                                    comments = 'Startregistratierequest niet valide'
                                )
                            )
                            
                        
                                                
                        # Geen registratie, proces is goedgegaan, broid geregistreerd

                    else:
                    
                        location_metadata_bro_gld['opnamestatus']= upload_info.json()['brondocuments'][0]['status']

                        record, created = \
                            gld_registration_log.objects.update_or_create(
                                gwm_bro_id=gmw_well.bro_id,
                                filter_id=tube['tube_number'],
                                date_modified = date_modified,
                                defaults=dict(
                                    validation_status = 'VALIDE',
                                    levering_id = identifier,
                                    levering_status = upload_info.json()['status'],
                                    comments = 'Foutieve levering startregistratierequest'
                                )
                            )
                except:
                
                    record, created = \
                            gld_registration_log.objects.update_or_create(
                                gwm_bro_id=gmw_well.bro_id,
                                filter_id=tube['tube_number'],
                                date_modified = date_modified,
                                defaults=dict(
                                    validation_status = 'VALIDE',
                                    levering_id = identifier,
                                    levering_status = None,
                                    comments = 'Fout bij ophalen status levering'
                                )
                            )                   


        
    
class Command(BaseCommand):
    help = """Custom command for import of GIS data."""
            
    def handle(self, *args, **options):
       
        acces_token_bro_portal = GLD_AANLEVERING_SETTINGS['acces_token_bro_portal']
        organisation = GLD_AANLEVERING_SETTINGS['organisation']
        env = GLD_AANLEVERING_SETTINGS['env']
        monitoringnetworks = GLD_AANLEVERING_SETTINGS['monitoringnetworks']
        failed_dir = GLD_AANLEVERING_SETTINGS['failed_dir_gld_registration']
        expiration_log_messages = GLD_AANLEVERING_SETTINGS['expiration_log_messages']
           
        run_gld_reg_init(acces_token_bro_portal,
                         organisation,
                         env,
                         monitoringnetworks,
                         failed_dir, 
                         expiration_log_messages)