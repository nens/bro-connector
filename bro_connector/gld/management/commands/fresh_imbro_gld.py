from typing import Literal
from main.settings.base import KVK_USER
from django.core.management.base import BaseCommand
from gld.models import GroundwaterLevelDossier, Observation, ObservationMetadata, ObservationProcess, Organisation

def get_organisation() -> Organisation:
    return Organisation.objects.get_or_create(
        company_number = KVK_USER
    )[0]

def setup_observation_metadata(type: Literal["volledigBeoordeeld", "voorlopig", "controle"]):
    user_org = get_organisation()
    match type:
        case "volledigBeoordeeld":
            return ObservationMetadata.objects.get_or_create(
                observation_type = "reguliereMeting",
                status = "volledigBeoordeeld",
                responsible_party = user_org,
            )
        case "voorlopig":
            return ObservationMetadata.objects.get_or_create(
                observation_type = "reguliereMeting",
                status = "voorlopig",
                responsible_party = user_org,
            )
        case "controle":
            return ObservationMetadata.objects.get_or_create(
                observation_type = "controlemeting",
                responsible_party = user_org,
            )

def setup_observation_proces(type: Literal["sensor", "manual"]):
    if type == "sensor":
        return ObservationProcess.objects.get_or_create(
            process_reference = "STOWAgwst",
            measurement_instrument_type = "druksensor",
            air_pressure_compensation_type = "capillair",
            evaluation_procedure = "oordeelDeskundig",
        )[0]
    return ObservationProcess.objects.get_or_create(
        process_reference = "STOWAgwst",
        measurement_instrument_type = "analoogPeilklokje",
        evaluation_procedure = "oordeelDeskundig",
    )[0]

class Command(BaseCommand):
    def handle(self, *args, **options):
        user_organisation = get_organisation()
        print(GroundwaterLevelDossier.objects.filter(
            quality_regime = "IMBRO",
            groundwater_monitoring_tube__groundwater_monitoring_well_static__delivery_accountable_party = user_organisation
        ).count())
        for gld in GroundwaterLevelDossier.objects.filter(
            quality_regime = "IMBRO",
            groundwater_monitoring_tube__groundwater_monitoring_well_static__delivery_accountable_party = user_organisation
        ):
            # Create controle / handpeiling reeks
            observation_metadata_c = setup_observation_metadata(type="controle")
            observation_proces_c = setup_observation_proces(type="manual")

            Observation.objects.get_or_create(
                groundwater_level_dossier = gld,
                observation_metadata = observation_metadata_c,
                observation_process = observation_proces_c,
            )

            # Create voorlopige sensor reeks
            observation_metadata_v = setup_observation_metadata(type="voorlopig")
            observation_proces_v = setup_observation_proces(type="sensor")
            Observation.objects.get_or_create(
                groundwater_level_dossier = gld,
                observation_metadata = observation_metadata_v,
                observation_process = observation_proces_v,
            )