from django.db import transaction
from django.core.management.base import BaseCommand
from django.db.models import Count
from gld.models import Observation, ObservationProcess, ObservationMetadata, MeasurementTvp, MeasurementPointMetadata, GroundwaterLevelDossier
from gmw.models import GroundwaterMonitoringTubeStatic
from bro.models import Organisation

from datetime import datetime

def create_imbro_glds():
    """
    Creates IMBRO GLDs by taking data post 2021-01-01 from existing IMBRO/A GLDs.
    Args:
        -
    Returns:
        dict: Summary of split operations
    """
    def move_measurements_from_imbroa_to_imbro_glds(glds_imbroa, observation_type, cutoff_time):
        for gld_imbroa in glds_imbroa:
            observations_imbroa = Observation.objects.filter(groundwater_level_dossier=gld_imbroa, observation_metadata__observation_type=observation_type)
            print(f"Number of {observation_type} observations: {len(observations_imbroa)}")
            measurements_imbroa = MeasurementTvp.objects.filter(observation__in=observations_imbroa)
            print(f"Number of {observation_type} measurements: {len(measurements_imbroa)}")
            measurements_imbroa_post_2020 = measurements_imbroa.filter(measurement_time__gte=cutoff_time)
            print(f"Number of {observation_type} measurements post 2020: {len(measurements_imbroa_post_2020)}")
            if measurements_imbroa_post_2020:
                gld_imbro, created = GroundwaterLevelDossier.objects.get_or_create(
                    groundwater_monitoring_tube=tube, quality_regime=imbro
                )
                if observation_type == regular:
                    dummy_observation, created = Observation.objects.get_or_create(
                        groundwater_level_dossier = gld_imbro,
                        observation_metadata = dummy_observation_metadata_regular,
                        observation_process = dummy_observation_process,
                    )
                elif observation_type == control:
                    dummy_observation, created = Observation.objects.get_or_create(
                        groundwater_level_dossier = gld_imbro,
                        observation_metadata = dummy_observation_metadata_control,
                        observation_process = dummy_observation_process,
                    )
                else:
                    dummy_observation = None
                if dummy_observation:
                    print(dummy_observation)
                    measurement_metadatas_imbroa_post_2020: list[MeasurementPointMetadata] = [mtvp.measurement_point_metadata for mtvp in measurements_imbroa_post_2020]
                    measurement_metadatas_imbro = [
                        MeasurementPointMetadata(
                            status_quality_control = mm.status_quality_control,
                            censor_reason = mm.censor_reason,
                            censor_reason_datalens = mm.censor_reason_datalens,
                            value_limit = mm.value_limit,
                        ) for mm in measurement_metadatas_imbroa_post_2020
                    ]

                    measurements_imbro = [
                        MeasurementTvp(
                            observation = mtvp.observation,
                            measurement_time = mtvp.measurement_time,
                            field_value = mtvp.field_value,
                            field_value_unit = mtvp.field_value_unit,
                            calculated_value = mtvp.calculated_value,
                            value_to_be_corrected = mtvp.value_to_be_corrected,
                            correction_time = mtvp.correction_time,
                            correction_reason = mtvp.correction_reason,
                            measurement_point_metadata = mm,
                            comment = mtvp.comment,
                        ) for mtvp, mm in zip(measurements_imbroa_post_2020, measurement_metadatas_imbro)
                    ]
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
                            print(f"Bulk updating/creating failed for {gld_imbroa}, {dummy_observation}")

    split_summary = {
        "total_glds_created": 0,
        "total_control_measurements_moved_to_imbro": 0,
        "total_regular_measurements_moved_to_imbro": 0,
    }

    zeeland = Organisation.objects.get(company_number="20168636")
    imbro_datetime = datetime(2021, 1, 1)
    imbro = "IMBRO"
    regular = "reguliereMeting"
    control = "controlemeting"

    dummy_observation_process, created = ObservationProcess.objects.get_or_create(
        process_reference = ...,
        measurement_instrument_type = ...,
        air_pressure_compensation_type = ...,
        process_type = "algoritme",
        evaluation_procedure = ...,
    )
    dummy_observation_metadata_regular, created = ObservationMetadata.objects.get_or_create(
        observation_type = regular,
        status = ...,
        responsible_party = zeeland,
    )
    dummy_observation_metadata_control, created = ObservationMetadata.objects.get_or_create(
        observation_type = control,
        status = ...,
        responsible_party = zeeland,
    )    

    tubes = GroundwaterMonitoringTubeStatic.objects.filter(groundwater_monitoring_well_static__delivery_accountable_party=zeeland)
    print(tubes)

    for tube in tubes:
        print(tube)
        glds_imbroa = GroundwaterLevelDossier.objects.filter(groundwater_monitoring_tube=tube)
        print(f"Number of glds: {len(glds_imbroa)}")
        if glds_imbroa:
            move_measurements_from_imbroa_to_imbro_glds(glds_imbroa, control, imbro_datetime)
            move_measurements_from_imbroa_to_imbro_glds(glds_imbroa, regular, imbro_datetime)
    
class Command(BaseCommand):
    def handle(self, *args, **options):
        # Example usage
        result = create_imbro_glds()
        print("Split Operation Summary:")
        print(f"Total Observations Processed: {result['total_observations_processed']}")
        print(f"Observations Split: {result['observations_split']}")
        print(
            f"Total New Observations Created: {result['total_new_observations_created']}"
        )
