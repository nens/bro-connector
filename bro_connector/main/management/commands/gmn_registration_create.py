from django.core.management.base import BaseCommand
from main.settings.base import GMN_AANLEVERING_SETTINGS
from gmn_aanlevering.models import GroundwaterMonitoringNet, MeasuringPoint, gmn_registration_log
from datetime import datetime

import bro_exchange as brx
import os

class Command(BaseCommand):
    """
    Command to registrate a GMN command. Demo variable is used througout the command to determine other variables.
    """

    def handle(self, *args, **options):
        """
        This is the main function for the registration of all monitoringnetworks that havent been registered yet.
        It loops over all networks and checks whether it should be registered or not.
        """
        demo = GMN_AANLEVERING_SETTINGS["demo"]
        if demo:
            acces_token_bro_portal = GMN_AANLEVERING_SETTINGS[
                "acces_token_bro_portal_demo"
            ]
        else:
            acces_token_bro_portal = GMN_AANLEVERING_SETTINGS[
                "acces_token_bro_portal_bro_connector"
            ]

        monitoring_networks = GroundwaterMonitoringNet.objects.all()

        for monitoring_network in monitoring_networks:
            
            # Check if the network should be delivered to the bro. If not, skip this network
            if monitoring_network.deliver_to_bro == False:
                print(f"Het {monitoring_network} moet niet aangeleverd worden, dus wordt overgeslagen")
                continue

            # Check if the network has a registration log. If not, create one.
            # If it has one, but has a failed to generate status: try to create new one
            gmn_registration_log_qs = gmn_registration_log.objects.filter(
                gmn_bro_id = monitoring_network.gmn_bro_id,
                object_id_accountable_party = monitoring_network.object_id_accountable_party,
            )
            
            if not gmn_registration_log_qs.exists() or gmn_registration_log_qs[0].process_status == 'failed_to_generate_source_documents':
                print(f'Geen registratie gevonden voor {monitoring_network}. Er wordt nu een registratie bestand aangemaakt.')
                gmn_registration_log_obj = self.create_register_xml(
                    monitoring_network,
                )
            else:
                gmn_registration_log_obj = gmn_registration_log_qs[0]
                print(f"Succesvolle registratie log gevonden voor {monitoring_network}. De registratie hiervoor wordt overgeslagen.")

            # Validate registration if required
            if gmn_registration_log_obj.process_status in ['succesfully_generated_startregistration_request', 'failed_to_validate_sourcedocument']:
                print(f"{monitoring_network} word gevalideerd.")
                self.validate_registration(
                    gmn_registration_log_obj,
                    acces_token_bro_portal
                )
            
    def create_register_xml(
        self,
        monitoring_network
    ): 
        """
        This function handles the start registration of a single monitoringnetwork.
        It logs its results in a gmn_registration_log instance, with the monitoringnetwork_name as name.
        Saves the xml file in gmn_aanlevering/registrations
        """
        try:
            # Set default quality regime IMBRO if value is not filled in in GMN instance
            if monitoring_network.quality_regime == None:
                quality_regime = 'IMBRO'
            else:
                quality_regime = monitoring_network.quality_regime

            # Creating measuringpoints list
            measuringpoint_objs = MeasuringPoint.objects.filter(gmn=monitoring_network)
            measuringpoints = []

            for measuringpoint_obj in measuringpoint_objs:
                well_code = measuringpoint_obj.groundwater_monitoring_tube.groundwater_monitoring_well.bro_id
                measuringpoint = {
                    "measuringPointCode":measuringpoint_obj.code,
                    "monitoringTube":{
                        "broId":well_code,
                        "tubeNumber":measuringpoint_obj.groundwater_monitoring_tube.tube_number,
                    },
                }
                measuringpoints.append(measuringpoint)


            # Create source docs
            srcdocdata = {
                "objectIdAccountableParty": monitoring_network.object_id_accountable_party,
                "name": monitoring_network.name,
                "deliveryContext": monitoring_network.delivery_context,
                "monitoringPurpose": monitoring_network.monitoring_purpose,
                "groundwaterAspect": monitoring_network.groundwater_aspect,
                "startDateMonitoring": [str(monitoring_network.start_date_monitoring), "date"],
                "measuringPoints": measuringpoints,
            }

            
            # Initialize the gmn_registration_request instance 
            gmn_startregistration_request = brx.gmn_registration_request(
                srcdoc = "GMN_StartRegistration",
                requestReference = f"register {monitoring_network.name}",
                deliveryAccountableParty = monitoring_network.delivery_accountable_party,
                qualityRegime = quality_regime,
                srcdocdata = srcdocdata,
            )


            # Generate the startregistration request
            gmn_startregistration_request.generate()

            
            # Write the request
            xml_filename = f"register {monitoring_network.name}.xml"
            gmn_startregistration_request.write_request(
                output_dir=GMN_AANLEVERING_SETTINGS["registrations_dir"], filename=xml_filename
            )

            # Create a log instance for the request
            log_obj = gmn_registration_log.objects.update_or_create(
                object_id_accountable_party = monitoring_network.object_id_accountable_party,
                gmn_bro_id=monitoring_network.gmn_bro_id,
                quality_regime=monitoring_network.quality_regime,
                defaults=dict(
                    comments="Succesfully generated startregistration request",
                    date_modified=datetime.now(),
                    validation_status=None,
                    process_status="succesfully_generated_startregistration_request",
                    file=xml_filename,
                ),
            )
            return log_obj
            
        except Exception as e:
            log_obj = gmn_registration_log.objects.update_or_create(
                object_id_accountable_party = monitoring_network.object_id_accountable_party,
                gmn_bro_id=monitoring_network.gmn_bro_id,
                quality_regime=monitoring_network.quality_regime,
                defaults=dict(
                    comments=f"Failed to create startregistration source document: {e}",
                    date_modified=datetime.now(),
                    process_status="failed_to_generate_source_documents",
                ),
            )

            return log_obj

    def validate_registration(
            self,
            gmn_registration_log_obj,
            acces_token_bro_portal
        ):
        """
        This function validates new registrations, and registers its process in the log instance.
        """
        try:
            filename = gmn_registration_log_obj.file
            filepath = os.path.join(GMN_AANLEVERING_SETTINGS["registrations_dir"], filename)
            payload = open(filepath)
            validation_info = brx.validate_sourcedoc(payload, acces_token_bro_portal, GMN_AANLEVERING_SETTINGS["demo"])

        except Exception as e:
            gmn_registration_log.objects.update_or_create(
                id = gmn_registration_log_obj.id,
                defaults=dict(
                    comments=f'Exception occured during validation of sourcedocuments: {e}',
                    process_status='failed_to_validate_sourcedocument',
                    ),
            )
        

        
            
