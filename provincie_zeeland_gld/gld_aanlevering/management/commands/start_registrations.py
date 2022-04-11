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
import bisect

from provincie_zeeland_gld.settings import GLD_AANLEVERING_SETTINGS
from gld_aanlevering import models

failed_update_strings = ['failed_once', 'failed_twice', 'failed_thrice']

def create_start_registration_sourcedocs(quality_regime, 
                                        deliveryaccountableparty,
                                        broidgmw, 
                                        filtrnr, 
                                        acces_token_bro_portal,
                                        locationcode,
                                        startregistrations_dir,
                                        monitoringnetworks=None):

    """
    Try to create startregistration sourcedocuments for a well/tube/quality regime
    Startregistration requests are saved to .xml file in startregistrations folder
    """
    
    if quality_regime==None or deliveryaccountableparty==None:
        record, created = \
            models.gld_registration_log.objects.update_or_create(
                gwm_bro_id=broidgmw,
                filter_id=filtrnr,
                quality_regime=quality_regime,
                defaults=dict(
                    validation_status = None,
                    levering_id = None,
                    process_status = 'failed_to_generate_source_documents',
                    comments = "Can't generate startregistration sourcedocuments without 'qualityRegime' and 'deliveryAccountableParty'",
                    date_modified = datetime.datetime.now(),
                )
            )
            
        return
            
    try:
        monitoringpoints = [{'broId':broidgmw,
                       'tubeNumber':filtrnr}]
        
        if monitoringnetworks == None:
            
            srcdocdata =  {'objectIdAccountableParty':locationcode+str(filtrnr),
                'monitoringPoints':monitoringpoints,        
                } 
        else:
            srcdocdata =  {'objectIdAccountableParty':locationcode+str(filtrnr),
                'groundwaterMonitoringNets':monitoringnetworks, #
                'monitoringPoints':monitoringpoints,        
                } 
            
        request_reference = 'GLD_StartRegistration_{}_tube_{}'.format(broidgmw,str(filtrnr))
        gld_startregistration_request = gwm.gld_registration_request(srcdoc='GLD_StartRegistration', 
                                           requestReference = request_reference, 
                                           deliveryAccountableParty = deliveryaccountableparty, 
                                           qualityRegime = quality_regime, 
                                           srcdocdata=srcdocdata)
        
        filename = request_reference + '.xml'
        gld_startregistration_request.generate()
        gld_startregistration_request.write_xml(output_dir=startregistrations_dir, filename=filename)
        
        
        record, created = \
            models.gld_registration_log.objects.update_or_create(
                gwm_bro_id=broidgmw,
                filter_id=filtrnr,
                quality_regime=quality_regime,
                defaults=dict(
                    comments = 'Succesfully generated startregistration request',
                    date_modified = datetime.datetime.now(),
                    process_status = 'succesfully_generated_startregistration_request',
                    file=filename
                )
            )

    except Exception as e:
    
        record, created = \
            models.gld_registration_log.objects.update_or_create(
                gwm_bro_id=broidgmw,
                filter_id=filtrnr,
                quality_regime=quality_regime,
                defaults=dict(
                    comments = 'Failed to create startregistration source document: {}'.format(e),
                    date_modified = datetime.datetime.now(),
                    process_status = 'failed_to_generate_source_documents'
                )
            )
            


def validate_gld_startregistration_request(start_registration_id, file, startregistrations_dir, acces_token_bro_portal):
    
    """
    Validate generated startregistration sourcedocuments
    """
    
    source_doc_file = os.path.join(startregistrations_dir, file)
    payload = open(source_doc_file)
    
    try: 
        validation_info = gwm.validate_sourcedoc(payload, acces_token_bro_portal, demo=True)
        validation_status = validation_info['status']
                
        if 'errors' in validation_info:
            validation_errors = validation_info['errors']
            comments = 'Validated startregistration document, found errors: {}'.format(validation_errors)

            record, created = \
                models.gld_registration_log.objects.update_or_create(
                    id=start_registration_id,
                    defaults=dict(
                        comments = 'Startregistration document is invalid, {}'.format(validation_errors),
                        validation_status=validation_status,
                        process_status='source_document_validation_succesful'
                    )
                )

        else:
            comments = 'Succesfully validated sourcedocument, no errors'
            record, created = \
                models.gld_registration_log.objects.update_or_create(
                    id=start_registration_id,
                    defaults=dict(
                        comments = comments,
                        validation_status=validation_status,
                        process_status='source_document_validation_succesful'
                    )
                )
                
    except Exception as e:
        process_status = 'failed_to_validate_sourcedocument'
        comments = 'Exception occured during validation of sourcedocuments: {}'.format(e)
        record, created = \
            models.gld_registration_log.objects.update_or_create(
                id=start_registration_id,
                defaults=dict(
                    comments = comments,
                    process_status=process_status
                )
            )
                
        
        
def deliver_startregistration_sourcedocuments(start_registration_id, file, startregistrations_dir, acces_token_bro_portal, demo=True):
    
    """
    Deliver generated startregistration sourcedoc to the BRO
    """

    source_doc_file = os.path.join(startregistrations_dir, file)
    payload = open(source_doc_file)
    request = {file: payload}
    
    # Get the registration
    gld_registration = models.gld_registration_log.objects.get(id=start_registration_id)
    
    # If the delivery fails, use the this to indicate how many attempts were made
    delivery_status = gld_registration.levering_status
    if delivery_status is None:
        delivery_status_update = 'failed_once'
    else:
        position = bisect.bisect_left(failed_update_strings, delivery_status)
        delivery_status_update = failed_update_strings[position+1]

    try:
                
        upload_info = gwm.upload_sourcedocs_from_dict(request, acces_token_bro_portal, demo)
        
        if upload_info == 'Error':
            comments = 'Error occured during delivery of sourcedocument'
            models.gld_registration_log.objects.update_or_create(
                    id=start_registration_id,
                    defaults={'date_modified': datetime.datetime.now(),
                              'comments': comments,
                              'process_status': delivery_status_update})
        else:            
            levering_id = upload_info.json()['identifier']
            delivery_status = upload_info.json()['status']
            lastchanged = upload_info.json()['lastChanged']
            comments = 'Succesfully delivered startregistration sourcedocument'
            
            models.gld_registration_log.objects.update_or_create(
                    id=start_registration_id,
                    defaults={'date_modified': datetime.datetime.now(),
                              'comments': comments,
                              'levering_status': delivery_status,
                              'lastchanged':lastchanged,
                              'levering_id':levering_id,
                              'process_status':'succesfully_delivered_sourcedocuments'})
            
    except Exception as e:
        comments = 'Exception occured during delivery of startregistration sourcedocument: {}'.format(e)
        
        models.gld_registration_log.objects.update_or_create(
                id=start_registration_id,
                defaults={'date_modified': datetime.datetime.now(),
                          'comments': comments,
                          'process_status':delivery_status_update})
    
                 
def check_delivery_status_levering(registration_id, 
                                    acces_token_bro_portal,
                                    demo=True):
        
    registration = models.gld_registration_log.objects.get(id=registration_id)
    levering_id = registration.levering_id

    try:
        upload_info = gwm.check_delivery_status(levering_id, 
                                                acces_token_bro_portal, 
                                                demo)      
        
        if upload_info.json()['status']=='DOORGELEVERD' and upload_info.json()['brondocuments'][0]['status']=='OPGENOMEN_LVBRO':
            
            record, created = \
                models.gld_registration_log.objects.update_or_create(
                    id=registration_id,
                    defaults=dict(
                        gld_bro_id=upload_info.json()['brondocuments'][0]['broId'],
                        levering_status = upload_info.json()['brondocuments'][0]['status'],
                        last_changed = upload_info.json()['lastChanged'],
                        comments = 'Startregistration request approved',
                        process_status = 'delivery_approved'
                    )
                )
                
        else:
        
            record, created = \
                models.gld_registration_log.objects.update_or_create(
                    id=registration_id,
                    defaults=dict(
                        levering_status = upload_info.json()['status'],
                        last_changed = upload_info.json()['lastChanged'],
                        comments = 'Startregistration request not yet approved',
                    )
                )

    except Exception as e:    
        record, created = \
                models.gld_registration_log.objects.update_or_create(
                    id=registration_id,
                    defaults=dict(
                        comments = 'Error occured during status check of delivery: {}'.format(e)
                    )
                )                   


def gld_start_registration_main(acces_token_bro_portal,
                                organisation,
                                monitoringnetworks, 
                                startregistrations_dir, 
                                expiration_log_messages):
    
    """
    Run GLD registration for all monitoring wells in the database 
    For new wells a startregistration request is attempted
    Previous startregistrations are validated and delivered
    Status of previous deliveries are checked 
    If a well changes in quality regime, a new registration is started 
    """
    
    gwm_wells = models.GroundwaterMonitoringWells.objects.all()
    
    # Loop over all GMW objects in the database
    for well in gwm_wells:
        registration_object_id_well = well.registration_object_id
        quality_regime = well.quality_regime
        gwm_bro_id = well.bro_id
        gmw_tubes_well = models.GroundwaterMonitoringTubes.objects.filter(registration_object_id=registration_object_id_well)

        # Loop over all tubes within the well
        for tube in gmw_tubes_well:
            tube_id = tube.tube_number
            if models.gld_registration_log.objects.filter(gwm_bro_id=gwm_bro_id, 
                                                          filter_id=tube_id, 
                                                          quality_regime=quality_regime).exists():
                # A registration already exists for this well/tube/quality regime
                # We check the status of the registration and either validate/deliver/check status/do nothing
                registration = models.gld_registration_log.objects.get(gwm_bro_id=gwm_bro_id, filter_nr=tube_id, quality_regime=quality_regime)
                
                if registration.levering_status != 'OPGENOMEN_LVRO' and registration.levering_id is not None:
                    # The registration has been delivered, but not yet approved
                    levering_id = registration.levering_id
                    status = check_delivery_status_levering(registration.id, acces_token_bro_portal)
                elif registration.levering_status == 'failed_to_generate_source_documents':
                    # Failed to register source documents for this well/tube/quality_regime
                    # TODO report back if this fails? 
                    continue
                elif registration.levering_status == 'succesfully_generated_startregistration_request':
                    registration_sourcedoc_file = registration.file
                    validation_status = validate_gld_startregistration_request(registration.id, 
                                                                             registration_sourcedoc_file,
                                                                             startregistrations_dir,
                                                                             acces_token_bro_portal)
                elif registration.validation_satus    
                
                    
            else:        
                #TODO database delivery accoutnable party moet string zijn!
                delivery_accountable_party = str(well.delivery_accountable_party)
                well_bro_id = well.bro_id
                location_code_internal = well.nitg_code
                location_metadata_bro_gld = create_start_registration_sourcedocs(quality_regime, 
                                                                   delivery_accountable_party, 
                                                                   well_bro_id, 
                                                                   tube_id, 
                                                                   acces_token_bro_portal,
                                                                   location_code_internal, 
                                                                   monitoringnetworks)
        
        break
        
            

    
class Command(BaseCommand):
    help = """Custom command for import of GIS data."""
            
    def handle(self, *args, **options): 
       
        acces_token_bro_portal = GLD_AANLEVERING_SETTINGS['acces_token_bro_portal']
        organisation = GLD_AANLEVERING_SETTINGS['organisation']
        monitoringnetworks = GLD_AANLEVERING_SETTINGS['monitoringnetworks']
        startregistrations_dir = GLD_AANLEVERING_SETTINGS['startregistrations_dir']
        expiration_log_messages = GLD_AANLEVERING_SETTINGS['expiration_log_messages']
           
        _ = gld_start_registration_main(acces_token_bro_portal,
                                        organisation,
                                        monitoringnetworks, 
                                        startregistrations_dir, 
                                        expiration_log_messages)