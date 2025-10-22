from django.db import transaction
from django.core.management.base import BaseCommand
from django.db.models import Count
from gld.models import Observation, ObservationProcess, ObservationMetadata, MeasurementTvp, MeasurementPointMetadata, GroundwaterLevelDossier
from gmw.models import GroundwaterMonitoringTubeStatic
from bro.models import Organisation

from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def get_imbroa_glds(tube):
    glds_imbroa = GroundwaterLevelDossier.objects.filter(
        groundwater_monitoring_tube=tube,
        quality_regime="IMBRO/A"
    )
    return glds_imbroa

def get_imbroa_measurements_after_2020(glds: list[GroundwaterLevelDossier]) -> dict:
    if not glds:
        return {}
    
    measurements = {}
    for gld in glds:
        observations_imbroa_regular = Observation.objects.filter(
            groundwater_level_dossier=gld, 
            observation_metadata__observation_type="reguliereMeting"
        )
        measurements_imbroa_regular = MeasurementTvp.objects.filter(observation__in=observations_imbroa_regular)
        measurements_imbroa_post_2020_regular  = measurements_imbroa_regular.filter(measurement_time__gte=datetime(2021,1,1))
        
        observations_imbroa_control = Observation.objects.filter(
            groundwater_level_dossier=gld, 
            observation_metadata__observation_type="controlemeting"
        )
        measurements_imbroa_control = MeasurementTvp.objects.filter(observation__in=observations_imbroa_control)
        measurements_imbroa_post_2020_control  = measurements_imbroa_control.filter(measurement_time__gte=datetime(2021,1,1))

        if measurements_imbroa_post_2020_regular or measurements_imbroa_post_2020_control:      
            measurements[gld] = [measurements_imbroa_post_2020_regular, measurements_imbroa_post_2020_control]
        
    return measurements   

def create_imbro_dossiers(tube: GroundwaterMonitoringTubeStatic, measurements: dict, summary):
    if not measurements:
        return [], summary
    
    glds_imbro = []
    for gld_imbroa, (measurements_regular, measurements_control) in measurements.items():
        if measurements_regular or measurements_control:
            gld_imbro, created = GroundwaterLevelDossier.objects.get_or_create(
                groundwater_monitoring_tube=tube, quality_regime="IMBRO"
            )
            glds_imbro.append(gld_imbro)
            if created:
                summary["total_glds_created"] += 1

    return glds_imbro, summary

def create_regular_observations(glds, summary):
    if not glds:
        return {}, summary
    
    observation_process_regular, created = ObservationProcess.objects.get_or_create(
        process_reference = "STOWAgwst",
        measurement_instrument_type = "druksensor",
        air_pressure_compensation_type = "gecorrigeerdLokaleMeting",
        process_type = "algoritme",
        evaluation_procedure = "oordeelDeskundige",
    )
    observation_metadata_regular, created = ObservationMetadata.objects.get_or_create(
        observation_type = "reguliereMeting",
        status = "voorlopig",
        responsible_party = Organisation.objects.get(company_number="20168636"),
    )
    
    observations = {}
    for gld in glds:
        observation, created = Observation.objects.get_or_create(
            groundwater_level_dossier = gld,
            observation_process = observation_process_regular,
            observation_metadata = observation_metadata_regular,
        )
        observations[gld]= observation
        if created:
            summary["total_imbro_regular_observations_created"] += 1

    return observations, summary

def create_control_observations(glds, summary):
    if not glds:
        return {}, summary
    
    observation_process_control, created = ObservationProcess.objects.get_or_create(
        process_reference = "STOWAgwst",
        measurement_instrument_type = "elektronischPeilklokje",
        process_type = "algoritme",
        evaluation_procedure = "oordeelDeskundige",
    )
    observation_metadata_control, created = ObservationMetadata.objects.get_or_create(
        observation_type = "controlemeting",
        status = "voorlopig",
        responsible_party = Organisation.objects.get(company_number="20168636"),
    )
    
    observations = {}
    for gld in glds:
        observation, created = Observation.objects.get_or_create(
            groundwater_level_dossier = gld,
            observation_process = observation_process_control,
            observation_metadata = observation_metadata_control,
        )
        observations[gld] = observation
        if created:
            summary["total_imbro_control_observations_created"] += 1

    return observations, summary

def create_imbro_measurements(
        measurements, observation_type, observations_regular, observations_control, summary
    ):
    if not measurements:
        return summary

    measurements_imbro = []
    measurement_metadatas_imbro = []
    for gld_imbroa, (measurements_regular, measurements_control) in measurements.items():
        if observation_type == "reguliereMeting":
            measurements_imbroa = measurements_regular
            dummy_observation = observations_regular[gld_imbroa]
        elif observation_type == "controlemeting":
            measurements_imbroa = measurements_control
            dummy_observation = observations_control[gld_imbroa]
        else:
            measurements_imbroa = []
            dummy_observation = None
        if not measurements_imbroa or not dummy_observation:
            logger.info("No measurements or observation in data")
            return summary
        
        measurements_imbroa: list[MeasurementTvp]      
        measurement_metadatas_imbroa: list[MeasurementPointMetadata] = [
            mtvp.measurement_point_metadata for mtvp in measurements_imbroa
        ]
        measurement_metadatas_imbro.extend([
            MeasurementPointMetadata(
                status_quality_control = mm.status_quality_control,
                censor_reason = mm.censor_reason,
                censor_reason_datalens = mm.censor_reason_datalens,
                value_limit = mm.value_limit,
            ) for mm in measurement_metadatas_imbroa
        ])
        measurements_imbro.extend([
            MeasurementTvp(
                observation = dummy_observation,
                measurement_time = mtvp.measurement_time,
                field_value = mtvp.field_value,
                field_value_unit = mtvp.field_value_unit,
                calculated_value = mtvp.calculated_value,
                value_to_be_corrected = mtvp.value_to_be_corrected,
                correction_time = mtvp.correction_time,
                correction_reason = mtvp.correction_reason,
                measurement_point_metadata = mm,
                comment = mtvp.comment,
            ) for mtvp, mm in zip(measurements_imbroa, measurement_metadatas_imbro)
        ])
        if observation_type == "reguliereMeting":
            summary["total_regular_measurements_moved_to_imbro"] += 1
        elif observation_type == "controlemeting":
            summary["total_control_measurements_moved_to_imbro"] += 1

    logger.info(summary)

    with transaction.atomic():
        try:
            MeasurementPointMetadata.objects.bulk_create(
                measurement_metadatas_imbro,
                update_conflicts=False,
                batch_size=5000,
            )
            MeasurementTvp.objects.bulk_create(
                measurements_imbro,
                update_conflicts=False,
                batch_size=5000,
            )
        except Exception as e:
            print(f"Bulk updating/creating failed.")


def create_imbro_glds():
    """
    Creates IMBRO GLDs by taking data post 2021-01-01 from existing IMBRO/A GLDs.
    Args:
        -
    Returns:
        dict: Summary of split operations
    """
    
    summary = {
        "total_imbro_glds_created": 0,
        "total_imbro_regular_observations_created": 0,
        "total_imbro_control_observations_created": 0,
        "total_imbro_regular_measurements_created": 0,
        "total_imbro_control_measurements_created": 0,
    }

    tubes = GroundwaterMonitoringTubeStatic.objects.filter(
        groundwater_monitoring_well_static__delivery_accountable_party=Organisation.objects.get(company_number="20168636")
    )
    logger.info(f"Number of tubes: {len(tubes)}")

    for tube in tubes:
        logger.info(f"Tube: {tube}")
        glds_imbroa = get_imbroa_glds(tube)
        logger.info(f"Number of glds: {len(glds_imbroa)}")
        measurements_imbro = get_imbroa_measurements_after_2020(glds_imbroa)
        logger.info(measurements_imbro.keys())
        glds_imbro, summary = create_imbro_dossiers(tube, measurements_imbro, summary)
        logger.info(glds_imbro)
        logger.info(summary)
        
        dummy_regular_observations, summary = create_regular_observations(glds_imbro, summary)
        dummy_control_observations, summary = create_control_observations(glds_imbro, summary)
        summary = create_imbro_measurements(measurements_imbro, "reguliereMeting", dummy_regular_observations, dummy_control_observations, summary)
        summary = create_imbro_measurements(measurements_imbro, "controlemeting", dummy_regular_observations, dummy_control_observations, summary)

    return summary

    
class Command(BaseCommand):
    def handle(self, *args, **options):
        # Example usage
        result = create_imbro_glds()
        logger.info("IMBRO/A to IMBRO Summary:")
        logger.info(f"Total GLDs Created: {result['total_imbro_glds_created']}")
        logger.info(f"Total Regular Observations Created: {result['total_imbro_regular_observations_created']}")
        logger.info(f"Total Control Observations Created: {result['total_imbro_control_observations_created']}")
        logger.info(f"Total Regular Measurements Created: {result['total_imbro_regular_measurements_created']}")
        logger.info(f"Total Control Measurements Created: {result['total_imbro_control_measurements_created']}")