from django.core.management.base import BaseCommand
from main.settings.base import GMN_AANLEVERING_SETTINGS
from gmn_aanlevering.models import GroundwaterMonitoringNet, MeasuringPoint, gmn_registration_log
from datetime import datetime

import bro_exchange as brx

class Command(BaseCommand):
    """
    Command to registrate a GMN command. Demo variable is used througout the command to determine other variables.
    """

    def handle(self, *args, **options):
        """
        This is the main function for the registration of all monitoringnetworks that havent been registered yet.
        It loops over all networks and checks whether it should be registered or not.
        """

        monitoring_networks = GroundwaterMonitoringNet.objects.all()

        for monitoring_network in monitoring_networks:

            # Check if the network has a registrationlog with status succes. If so, skip registration, otherwise create one.
            gmn_registration_log_obj = gmn_registration_log.objects.filter(
                gmn_bro_id = monitoring_network.gmn_bro_id,
                object_id_accountable_party = monitoring_network.object_id_accountable_party,
            )

            if gmn_registration_log_obj.exists() and gmn_registration_log_obj.process_status == 'succesfully_generated_startregistration_request':
                print(f"Succesvolle registratie log gevonden voor {monitoring_network}. De registratie hiervoor wordt overgeslagen.")
                continue
            else:
                self.create_startregistration_sourcedocs(
                    monitoring_network = monitoring_network,
                )
            
    def create_startregistration_sourcedocs(
        self,
        monitoring_network
    ): 
        """
        This function handles the start registration of a single monitoringnetwork.
        It logs its results in a gmn_registration_log instance, with the monitoringnetwork_name as name.
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
                "startDateMonitoring": [monitoring_network.start_date_monitoring, "date"],
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
            gmn_registration_log.objects.update_or_create(
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
            
        except Exception as e:
            gmn_registration_log.objects.update_or_create(
                gmn_bro_id=monitoring_network.gmn_bro_id,
                quality_regime=monitoring_network.quality_regime,
                defaults=dict(
                    comments=f"Failed to create startregistration source document: {e}",
                    date_modified=datetime.now(),
                    process_status="failed_to_generate_source_documents",
                ),
            )

        
            
