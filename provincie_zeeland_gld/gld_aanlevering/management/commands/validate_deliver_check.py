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

failed_update_strings = ['failed_once', 'failed_twice', 'failed_thrice']

def validate_gld_addition_source_document(observation_id, filename, acces_token_bro_portal):
    
    """
    Validate the generated GLD addition sourcedoc
    """
    source_doc_file = os.path.join(GLD_AANLEVERING_SETTINGS['additions_dir'], filename)
    payload = open(source_doc_file)
    
    try:    
        validation_info = gwm.validate_sourcedoc(payload, acces_token_bro_portal, demo=True)
        validation_status = validation_info['status']
        
        if 'errors' in validation_info:
            validation_errors = validation_info['errors']
            comments = 'Validated sourcedocument, found errors: {}'.format(validation_errors)

            record, created = \
                models.Observation.objects.update_or_create(
                    observation_id=observation_id,
                    defaults={'status':'source_document_validation_failed'})
            
        else:
            comments = 'Succesfully validated sourcedocument, no errors'
        
        models.gld_addition_log.objects.update_or_create(
                observation_id=observation_id,
                defaults={'date_modified': datetime.datetime.now(),
                          'comments': comments[0:20000],
                          'validation_status': validation_status})

        record, created = \
            models.Observation.objects.update_or_create(
                observation_id=observation_id,
                defaults={'status':'source_document_validation_succeeded'})


    except Exception as e:    
        models.gld_addition_log.objects.update_or_create(
                observation_id=observation_id,
                defaults={'date_modified': datetime.datetime.now(),
                          'comments': 'Failed to validate source document: {}'.format(e)})

        record, created = \
            models.Observation.objects.update_or_create(
                observation_id=observation_id,
                defaults={'status':'source_document_validation_failed'})
        
    return validation_status
        
    
def deliver_gld_addition_source_document(observation_id, filename, acces_token_bro_portal, demo=True):
    
    """
    Deliver GLD addition sourcedocument to the BRO
    """

    gld_addition = models.gld_addition_log.objects.get(observation_id=observation_id)
    source_doc_file = os.path.join(GLD_AANLEVERING_SETTINGS['additions_dir'], filename)
    payload = open(source_doc_file)
    request = {filename: payload}
    
    # If the delivery fails, use the this to indicate how many attempts were made
    delivery_status = gld_addition.levering_status
    if delivery_status is None:
        delivery_status_update = 'failed_once'
    else:
        position = bisect.bisect_left(failed_update_strings, delivery_status)
        delivery_status_update = failed_update_strings[position+1]
    
    try:
        upload_info = gwm.upload_sourcedocs_from_dict(request, acces_token_bro_portal, demo=demo)
        
        if upload_info == 'Error':
            
            comments = 'Error occured during delivery of sourcedocument'
            
            models.gld_addition_log.objects.update_or_create(
                    observation_id=observation_id,
                    defaults={'date_modified': datetime.datetime.now(),
                              'comments': comments,
                              'levering_status':delivery_status_update})
        else:            
            levering_id = upload_info.json()['identifier']
            delivery_status = upload_info.json()['status']
            lastchanged = upload_info.json()['lastChanged']
            comments = 'Succesfully delivered sourcedocument'
            
            models.gld_addition_log.objects.update_or_create(
                    observation_id=observation_id,
                    defaults={'date_modified': datetime.datetime.now(),
                              'comments': comments,
                              'levering_status': delivery_status,
                              'lastchanged':lastchanged,
                              'levering_id':levering_id})
            
            record, created = \
                models.Observation.objects.update_or_create(
                    observation_id=observation_id,
                    defaults={'status':'source_document_delivered'})


    except Exception as e:
        
        comments = 'Error occured in attempting to deliver sourcedocument, {}'.format(e)
        
        models.gld_addition_log.objects.update_or_create(
                observation_id=observation_id,
                defaults={'date_modified': datetime.datetime.now(),
                          'comments': comments,
                          'levering_status':delivery_status_update})
        
    return delivery_status_update
    
def check_status_gld_addition(observation_id, levering_id, acces_token_bro_portal, demo=True):
    """ 
    Check the status of a delivery and log to the database what the status is
    """

    try:
        upload_info = gwm.check_delivery_status(levering_id, acces_token_bro_portal, demo=demo)  
        delivery_status = upload_info.json()['status']

        if delivery_status == 'DOORGELEVERD':

            comments = 'GLD addition is approved'
            models.gld_addition_log.objects.update_or_create(
                observation_id=observation_id,
                defaults={'date_modified': datetime.datetime.now(),
                          'comments': comments,
                          'levering_status':delivery_status})
            
            # Update the observation status to approved
            record, created = \
                models.Observation.objects.update_or_create(
                    observation_id=observation_id,
                    defaults={'status':'delivery_approved'})
                        
        else:
            comments = 'Status check succesful, not yet approved'
            models.gld_addition_log.objects.update_or_create(
                observation_id=observation_id,
                defaults={'date_modified': datetime.datetime.now(),
                          'comments': comments,
                          'levering_status':delivery_status})

    except Exception as e:
        comments = 'Status check failed, {}'.format(e)
        models.gld_addition_log.objects.update_or_create(
            observation_id=observation_id,
            defaults={'date_modified': datetime.datetime.now(),
                      'comments': comments,
                      'levering_status':delivery_status})
        
    return delivery_status
        
def validate_addition(observation, acces_token_bro_portal):
    
    """
    Validate the sourcedocuments, register the results in the database 
    """
    
    # Get the GLD addition for this observation 
    gld_addition = models.gld_addition_log.objects.get(observation_id=observation.observation_id)
    filename = gld_addition.file
    validation_status = gld_addition.validation_status
    
    # Validate the sourcedocument for this observation
    validation_status = validate_gld_addition_source_document(observation.observation_id, filename, acces_token_bro_portal)
      
    return validation_status
        
  
def deliver_addition(observation, access_token_bro_portal):
    
    """
    If there is a valid source document, deliver to the BRO
    If delivery has failed three times prior, no more attempts will be made    
    """

    # Get the GLD addition for this observation 
    gld_addition = models.gld_addition_log.objects.get(observation_id=observation.observation_id)
    validation_status = gld_addition.validation_status
    filename = gld_addition.file
    
    if validation_status == 'VALIDE' and gld_addition.levering_id is None: 
        delivery_status = deliver_gld_addition_source_document(observation.observation_id, filename, access_token_bro_portal)
        
        if delivery_status == 'failed_thrice':
            # If delivery fails three times, we flag the observation as delivery failed
            record, created = \
                models.Observation.objects.update_or_create(
                    observation_id=observation.observation_id,
                    defaults={'status':'source_document_delivery_failed'})
                
            
            # Remove the source document that failed
            sourcedoc_filepath = os.path.join(GLD_AANLEVERING_SETTINGS['additions_dir'], filename) 
            os.remove(sourcedoc_filepath)

def check_status_addition(observation, acces_token_bro_portal):
    
    """
    Check the status of a delivery
    If the delivery has been approved, remove the source document
    """
    
    # Get the GLD addition for this observation 
    gld_addition = models.gld_addition_log.objects.get(observation_id=observation.observation_id)
    file_name = gld_addition.file
    levering_id = gld_addition.levering_id      
    delivery_status = gld_addition.levering_status
    
    if delivery_status != 'OPGENOMEN_LVBRO':
        new_delivery_status = check_status_gld_addition(observation.observation_id, levering_id, acces_token_bro_portal)
    
    if new_delivery_status == 'OPGENOMEN_LVBRO':
        sourcedoc_filepath = os.path.join(GLD_AANLEVERING_SETTINGS['additions_dir'], file_name) 
        os.remove(sourcedoc_filepath)
    
    return new_delivery_status


def gld_validate_and_deliver(additions_dir, acces_token_bro_portal):
    
    """
    Main algorithm that check the observations and performs actions based on the status
    """
    
    observation_set = models.Observation.objects.all()
    
    for observation in observation_set:
        
        # For all the observations in the database, check the status and continue with the BRO process

        if observation.status == 'source_document_created':
            # TODO check if procedure is same as other observations, use the same procedure uuid 
            validation_status = validate_addition(observation, acces_token_bro_portal)
            
            # If the validation succeeded, try an initial delivery
            if validation_status == 'VALIDE': 
                delivery_status = deliver_addition(observation, acces_token_bro_portal)


        elif observation.status == 'source_document_validation_succeeded':
            # If a source document has been validated succesfully but failed to deliver, try to deliver again
            # after three tries no more attempts will be made
            delivery_status = deliver_addition(observation, acces_token_bro_portal)
            
            # If the delivery is succesful on first try, try to check status 
            if delivery_status == ' AANGELEVERD':
                delivery_status = check_status_addition(observation, acces_token_bro_portal)
                        
        elif observation.status == 'source_document_delivered':
           delivery_status = check_status_addition(observation, acces_token_bro_portal)

        elif observation.status == 'approval_status_changed':
            # This will come from the QC protocol
            # Deliver the corrections
            # Can get the original delivery back with gwmpy.get_sourcedocument
            continue
        
        else:
            pass
                        
        
    # Start with batch of deliveries
    
    # If procedure of first is None, try to validate the document and wait for procedure id
    # Write procedure id to all the deliveries and continue the process 
    
    # We deliver the first document and wait for the procedure ID to come back
    
    # Where can the process fail?
    #   - Failure to validate a document, log the errors stop the delivery
    #   - Invalid document, log why it is invalid and stop delivery
    #   - Failure to deliver a document, we log to retry on later attempt, log amount of retries 
    #   - If maximum of delivery retries 
    
    # What if delivery succeeds?
    # - Status check of deliveries
    # - If deliveries are succesful, files are deleted, logs are kept

class Command(BaseCommand):       
     
    def handle(self, *args, **options):
        #print(NENS_DEMO_SETTINGS)
        acces_token_bro_portal = GLD_AANLEVERING_SETTINGS['acces_token_bro_portal']
        additions_dir = GLD_AANLEVERING_SETTINGS['additions_dir']
        
        gld_validate_and_deliver(additions_dir, acces_token_bro_portal)
