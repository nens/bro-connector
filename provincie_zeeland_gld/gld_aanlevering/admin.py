from django.contrib import admin

from . import models

def _register(model, admin_class):
    admin.site.register(model, admin_class)


#%% GLD model registration

class GroundwaterLevelDossierAdmin(admin.ModelAdmin):

    list_display = (
        'groundwater_level_dossier_id',
        'groundwater_monitoring_tube_id',
        'research_start_date',
        'research_last_date',
    )
    list_filter = (
        'research_start_date',
        'research_last_date',
        'groundwater_level_dossier_id',
        'groundwater_monitoring_tube_id',
        'research_start_date',
        'research_last_date',
    )


class MeasurementPointMetadataAdmin(admin.ModelAdmin):

    list_display = (
        'measurement_point_metadata_id',
        'qualifier_by_category',
        'censored_reason',
        'qualifier_by_quantity',
        'interpolation_code',
    )
    list_filter = (
        'measurement_point_metadata_id',
        'qualifier_by_category',
        'censored_reason',
        'qualifier_by_quantity',
        'interpolation_code',
    )


class MeasurementTimeSeriesAdmin(admin.ModelAdmin):

    list_display = ('measurement_time_series_id',)
    list_filter = ('measurement_time_series_id',)


class MeasurementTimeseriesTvpObservationAdmin(admin.ModelAdmin):

    list_display = (
        'measurement_timeseries_tvp_observation_id',
        'groundwater_level_dossier_id',
        'observation_starttime',
        'observation_endtime',
        'result_time',
        'metadata_observation_id',
    )
    list_filter = (
        'observation_starttime',
        'observation_endtime',
        'result_time',
        'measurement_timeseries_tvp_observation_id',
        'groundwater_level_dossier_id',
        'observation_starttime',
        'observation_endtime',
        'result_time',
        'metadata_observation_id',
    )


class MeasurementTvpAdmin(admin.ModelAdmin):

    list_display = (
        'measurement_tvp_id',
        'measurement_time_series_id',
        'measurement_time',
        'field_value',
        'calculated_value',
        'corrected_value',
        'correction_time',
        'correction_reason',
    )
    list_filter = (
        'measurement_time',
        'correction_time',
        'measurement_tvp_id',
        'measurement_time_series_id',
        'measurement_time',
        'field_value',
        'calculated_value',
        'corrected_value',
        'correction_time',
        'correction_reason',
    )


class ObservationMetadataAdmin(admin.ModelAdmin):

    list_display = (
        'observation_metadata_id',
        'date_stamp',
        'parameter_measurement_serie_type',
        'status',
        'responsible_party_id',
    )
    list_filter = (
        'date_stamp',
        'observation_metadata_id',
        'date_stamp',
        'parameter_measurement_serie_type',
        'status',
        'responsible_party_id',
    )


class ObservationProcessAdmin(admin.ModelAdmin):

    list_display = (
        'observation_process_id',
        'process_reference',
        'parameter_measurement_instrument_type',
        'parameter_air_pressure_compensation_type',
        'process_type',
        'parameter_evaluation_procedure',
    )
    list_filter = (
        'observation_process_id',
        'process_reference',
        'parameter_measurement_instrument_type',
        'parameter_air_pressure_compensation_type',
        'process_type',
        'parameter_evaluation_procedure',
    )


class ResponsiblePartyAdmin(admin.ModelAdmin):

    list_display = (
        'responsible_party_id',
        'identification',
        'organisation_name',
    )
    list_filter = (
        'responsible_party_id',
        'identification',
        'organisation_name',
    )


class TypeAirPressureCompensationAdmin(admin.ModelAdmin):

    list_display = ('id', 'value', 'definition_nl', 'imbro', 'imbro_a')
    list_filter = (
        'imbro',
        'imbro_a',
        'id',
        'value',
        'definition_nl',
        'imbro',
        'imbro_a',
    )


class TypeCensoredReasonCodeAdmin(admin.ModelAdmin):

    list_display = ('id', 'value', 'definition_nl', 'imbro', 'imbro_a')
    list_filter = (
        'imbro',
        'imbro_a',
        'id',
        'value',
        'definition_nl',
        'imbro',
        'imbro_a',
    )


class TypeEvaluationProcedureAdmin(admin.ModelAdmin):

    list_display = ('id', 'value', 'definition_nl', 'imbro', 'imbro_a')
    list_filter = (
        'imbro',
        'imbro_a',
        'id',
        'value',
        'definition_nl',
        'imbro',
        'imbro_a',
    )


class TypeInterpolationCodeAdmin(admin.ModelAdmin):

    list_display = ('id', 'value', 'definition_nl', 'imbro', 'imbro_a')
    list_filter = (
        'imbro',
        'imbro_a',
        'id',
        'value',
        'definition_nl',
        'imbro',
        'imbro_a',
    )


class TypeMeasementInstrumentTypeAdmin(admin.ModelAdmin):

    list_display = ('id', 'value', 'definition_nl', 'imbro', 'imbro_a')
    list_filter = (
        'imbro',
        'imbro_a',
        'id',
        'value',
        'definition_nl',
        'imbro',
        'imbro_a',
    )


class TypeObservationTypeAdmin(admin.ModelAdmin):

    list_display = ('id', 'value', 'definition_nl', 'imbro', 'imbro_a')
    list_filter = (
        'imbro',
        'imbro_a',
        'id',
        'value',
        'definition_nl',
        'imbro',
        'imbro_a',
    )


class TypeProcessReferenceAdmin(admin.ModelAdmin):

    list_display = ('id', 'value', 'definition_nl', 'imbro', 'imbro_a')
    list_filter = (
        'imbro',
        'imbro_a',
        'id',
        'value',
        'definition_nl',
        'imbro',
        'imbro_a',
    )


class TypeProcessTypeAdmin(admin.ModelAdmin):

    list_display = ('id', 'value', 'definition_nl', 'imbro', 'imbro_a')
    list_filter = (
        'imbro',
        'imbro_a',
        'id',
        'value',
        'definition_nl',
        'imbro',
        'imbro_a',
    )


class TypeStatusCodeAdmin(admin.ModelAdmin):

    list_display = ('id', 'value', 'definition_nl', 'imbro', 'imbro_a')
    list_filter = (
        'imbro',
        'imbro_a',
        'id',
        'value',
        'definition_nl',
        'imbro',
        'imbro_a',
    )


class TypeStatusQualityControlAdmin(admin.ModelAdmin):

    list_display = ('id', 'value', 'definition_nl', 'imbro', 'imbro_a')
    list_filter = (
        'imbro',
        'imbro_a',
        'id',
        'value',
        'definition_nl',
        'imbro',
        'imbro_a',
    )

#%% GMW model registration

class DeliveredLocationsAdmin(admin.ModelAdmin):

    list_display = (
        'location_id',
        'registration_object_id',
        'coordinates',
        'referencesystem',
        'horizontal_positioning_method',
    )


class DeliveredVerticalPositionsAdmin(admin.ModelAdmin):

    list_display = (
        'delivered_vertical_positions_id',
        'registration_object_id',
        'local_vertical_reference_point',
        'offset',
        'vertical_datum',
        'ground_level_position',
        'ground_level_positioning_method',
    )


class GroundwaterMonitoringTubesAdmin(admin.ModelAdmin):

    list_display = (
        'groundwater_monitoring_tube_id',
        'registration_object_id',
        'tube_number',
        'tube_type',
        'artesian_well_cap_present',
        'sediment_sump_present',
        'number_of_geo_ohm_cables',
        'tube_top_diameter',
        'variable_diameter',
        'tube_status',
        'tube_top_position',
        'tube_top_positioning_method',
        'tube_packing_material',
        'tube_material',
        'glue',
        'screen_length',
        'sock_material',
        'plain_tube_part_length',
        'sediment_sump_length',
    )


class GroundwaterMonitoringWellsAdmin(admin.ModelAdmin):

    list_display = (
        'registration_object_id',
        'registration_object_type',
        'bro_id',
        'request_reference',
        'delivery_accountable_party',
        'delivery_responsible_party',
        'quality_regime',
        'under_privilege',
        'delivery_context',
        'construction_standard',
        'initial_function',
        'number_of_standpipes',
        'ground_level_stable',
        'well_stability',
        'nitg_code',
        'olga_code',
        'well_code',
        'owner',
        'maintenance_responsible_party',
        'well_head_protector',
        'well_construction_date',
    )
    list_filter = ('well_construction_date',)



#%% Aanlevering models registration

class aanleverinfo_filtersAdmin(admin.ModelAdmin):
    list_display = ('meetpunt',
                    'aanleveren',
                    )
    list_filter = ('aanleveren',)

class gld_registration_logAdmin(admin.ModelAdmin):
    list_display = ('date_modified',
                    'gwm_bro_id',
                    'filter_id',
                    'validation_status',
                    'levering_id',
                    'levering_status',
                    'comments',
                    )
    list_filter = ('validation_status',
                    'levering_status',)

class gld_addition_log_controleAdmin(admin.ModelAdmin):
    list_display = ('date_modified',
                    'observation_id',
                    'start',
                    'end',
                    'validation_status',
                    'levering_id',
                    'levering_status',
                    )
    list_filter = ('validation_status',
                    'levering_status',)

class gld_addition_log_voorlopigAdmin(admin.ModelAdmin):
    list_display = ('date_modified',
                    'observation_id',
                    'start',
                    'end',
                    'validation_status',
                    'levering_id',
                    'levering_status',
                    )
    list_filter = ('validation_status',
                    'levering_status',)

class gld_addition_log_volledigAdmin(admin.ModelAdmin):
    list_display = ('date_modified',
                    'observation_id',
                    'start',
                    'end',
                    'validation_status',
                    'levering_id',
                    'levering_status',
                    )
    list_filter = ('validation_status',
                    'levering_status',)



_register(models.GroundwaterLevelDossier, GroundwaterLevelDossierAdmin)
_register(models.MeasurementPointMetadata, MeasurementPointMetadataAdmin)
_register(models.MeasurementTimeSeries, MeasurementTimeSeriesAdmin)
_register(
    models.MeasurementTimeseriesTvpObservation,
    MeasurementTimeseriesTvpObservationAdmin)
_register(models.MeasurementTvp, MeasurementTvpAdmin)
_register(models.ObservationMetadata, ObservationMetadataAdmin)
_register(models.ObservationProcess, ObservationProcessAdmin)
_register(models.ResponsibleParty, ResponsiblePartyAdmin)
_register(
    models.TypeAirPressureCompensation,
    TypeAirPressureCompensationAdmin)
_register(models.TypeCensoredReasonCode, TypeCensoredReasonCodeAdmin)
_register(models.TypeEvaluationProcedure, TypeEvaluationProcedureAdmin)
_register(models.TypeInterpolationCode, TypeInterpolationCodeAdmin)
_register(
    models.TypeMeasementInstrumentType,
    TypeMeasementInstrumentTypeAdmin)
_register(models.TypeObservationType, TypeObservationTypeAdmin)
_register(models.TypeProcessReference, TypeProcessReferenceAdmin)
_register(models.TypeProcessType, TypeProcessTypeAdmin)
_register(models.TypeStatusCode, TypeStatusCodeAdmin)
_register(models.TypeStatusQualityControl, TypeStatusQualityControlAdmin)


_register(models.aanleverinfo_filters, aanleverinfo_filtersAdmin)
_register(models.gld_registration_log, gld_registration_logAdmin)
_register(models.gld_addition_log_controle, gld_addition_log_controleAdmin)
_register(models.gld_addition_log_voorlopig, gld_addition_log_voorlopigAdmin)
_register(models.gld_addition_log_volledig, gld_addition_log_volledigAdmin)


_register(models.DeliveredLocations, DeliveredLocationsAdmin)
_register(models.DeliveredVerticalPositions, DeliveredVerticalPositionsAdmin)
_register(models.GroundwaterMonitoringTubes, GroundwaterMonitoringTubesAdmin)
_register(models.GroundwaterMonitoringWells, GroundwaterMonitoringWellsAdmin)

