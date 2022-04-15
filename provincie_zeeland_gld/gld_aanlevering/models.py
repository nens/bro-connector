# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = True` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


#%% GLD Models

class GroundwaterLevelDossier(models.Model):
    groundwater_level_dossier_id = models.AutoField(primary_key=True)
    groundwater_monitoring_tube_id = models.IntegerField(blank=True, null=True)
    gmw_bro_id = models.CharField(max_length=255, blank=True, null=True)
    gld_bro_id = models.CharField(max_length=255, blank=True, null=True)
    research_start_date = models.DateField(blank=True, null=True)
    research_last_date = models.DateField(blank=True, null=True)
    research_last_correction = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = db_table = 'gld"."groundwater_level_dossier'
        verbose_name = 'Groundwaterlevel dossier'
        verbose_name_plural = 'Groundwaterlevel dossier'


class MeasurementPointMetadata(models.Model):
    measurement_point_metadata_id = models.AutoField(primary_key=True)
    qualifier_by_category = models.IntegerField(blank=True, null=True)
    censored_reason = models.IntegerField(blank=True, null=True)
    qualifier_by_quantity = models.DecimalField(max_digits=100, decimal_places=10, blank=True, null=True)
    interpolation_code = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        app_label = 'gld_aanlevering'
        db_table = 'gld"."measurement_point_metadata'
        verbose_name = 'Measurement point metadata'
        verbose_name_plural = 'Measurement point metadata'


class MeasurementTimeSeries(models.Model):
    measurement_time_series_id = models.AutoField(primary_key=True)
    observation_id = models.IntegerField(blank=True, null=True)
    class Meta:
        managed = True
        db_table = 'gld"."measurement_time_series'
        verbose_name = 'Measurement timeseries'
        verbose_name_plural = 'Measurement timeseries'


# We don't use this 
# class MeasurementTimeseriesTvpObservation(models.Model):
#     measurement_timeseries_tvp_observation_id = models.AutoField(primary_key=True)
#     groundwater_level_dossier_id = models.IntegerField(blank=True, null=True)
#     observation_starttime = models.DateTimeField(blank=True, null=True)
#     observation_endtime = models.DateTimeField(blank=True, null=True)
#     result_time = models.DateTimeField(blank=True, null=True)
#     metadata_observation_id = models.IntegerField(blank=True, null=True)

#     class Meta:
#         managed = True
#         db_table = 'gld"."measurement_timeseries_tvp_observation'
#         verbose_name = 'Measurement timeseries tvp observation'
#         verbose_name_plural = 'Measurement timeseries tvp observation'

class MeasurementTvp(models.Model):
    measurement_tvp_id = models.AutoField(primary_key=True)
    measurement_time_series_id = models.IntegerField(blank=True, null=True)
    measurement_time = models.DateTimeField(blank=True, null=True)
    field_value = models.DecimalField(max_digits=100, decimal_places=10, blank=True, null=True)
    field_value_unit = models.CharField(max_length=255, blank=True, null=True)
    calculated_value = models.DecimalField(max_digits=100, decimal_places=10, blank=True, null=True)
    corrected_value = models.DecimalField(max_digits=100, decimal_places=10, blank=True, null=True)
    correction_time = models.DateTimeField(blank=True, null=True)
    correction_reason = models.CharField(max_length=255, blank=True, null=True)
    measurement_metadata_id = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gld"."measurement_tvp'
        verbose_name = 'Measurement time-value pairs'
        verbose_name_plural = 'Measurement time-value pairs'


class Observation(models.Model):
    observation_id = models.AutoField(primary_key=True)
    observationperiod = models.DurationField(blank=True, null=True)
    observation_starttime = models.DateTimeField(blank=True, null=True)
    result_time = models.DateTimeField(blank=True, null=True)
    observation_endtime = models.DateTimeField(blank=True, null=True)
    observation_metadata_id = models.IntegerField(blank=True, null=True)
    observation_process_id = models.IntegerField(blank=True, null=True)
    groundwater_level_dossier_id = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gld"."observation'
        verbose_name = 'Observation'
        verbose_name_plural = 'Observations'


class ObservationMetadata(models.Model):
    observation_metadata_id = models.AutoField(primary_key=True)
    date_stamp = models.DateField(blank=True, null=True)
    parameter_measurement_serie_type = models.IntegerField(blank=True, null=True)
    status = models.IntegerField(blank=True, null=True)
    responsible_party_id = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gld"."observation_metadata'
        verbose_name = 'Observation metadata'
        verbose_name_plural = 'Observation metadata'

class ObservationProcess(models.Model):
    observation_process_id = models.AutoField(primary_key=True)
    process_reference = models.IntegerField(blank=True, null=True)
    parameter_measurement_instrument_type = models.IntegerField(blank=True, null=True)
    parameter_air_pressure_compensation_type = models.IntegerField(blank=True, null=True)
    process_type = models.IntegerField(blank=True, null=True)
    parameter_evaluation_procedure = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gld"."observation_process'
        verbose_name = 'Observation process'
        verbose_name_plural = 'Observation process'


class ResponsibleParty(models.Model):
    responsible_party_id = models.AutoField(primary_key=True)
    identification = models.IntegerField(blank=True, null=True)
    organisation_name = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gld"."responsible_party'
        verbose_name = 'Responsible party'
        verbose_name_plural = 'Responsible party'


class TypeAirPressureCompensation(models.Model):
    id = models.IntegerField(blank=True, primary_key=True)
    value = models.CharField(max_length=255, blank=True, null=True)
    definition_nl = models.CharField(max_length=255, blank=True, null=True)
    imbro = models.BooleanField(blank=True, null=True)
    imbro_a = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gld"."type_air_pressure_compensation'
        verbose_name_plural = 'Air pressure compensation'


class TypeCensoredReasonCode(models.Model):
    id = models.IntegerField(blank=True, primary_key=True)
    value = models.CharField(max_length=255, blank=True, null=True)
    definition_nl = models.CharField(max_length=255, blank=True, null=True)
    imbro = models.BooleanField(blank=True, null=True)
    imbro_a = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gld"."type_censored_reason_code'
        verbose_name_plural = 'Censor reasons'


class TypeEvaluationProcedure(models.Model):
    id = models.IntegerField(blank=True, primary_key=True)
    value = models.CharField(max_length=255, blank=True, null=True)
    definition_nl = models.CharField(max_length=255, blank=True, null=True)
    imbro = models.BooleanField(blank=True, null=True)
    imbro_a = models.BooleanField(blank=True, null=True)
    
    class Meta:
        managed = True
        db_table = 'gld"."type_evaluation_procedure'
        verbose_name_plural = 'Evaluation procedures'


class TypeInterpolationCode(models.Model):
    id = models.IntegerField(blank=True, primary_key=True)
    value = models.CharField(max_length=255, blank=True, null=True)
    definition_nl = models.CharField(max_length=255, blank=True, null=True)
    imbro = models.BooleanField(blank=True, null=True)
    imbro_a = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gld"."type_interpolation_code'
        verbose_name_plural = 'Interpolation codes'


class TypeMeasurementInstrumentType(models.Model):
    id = models.IntegerField(blank=True, primary_key=True)
    value = models.CharField(max_length=255, blank=True, null=True)
    definition_nl = models.CharField(max_length=255, blank=True, null=True)
    imbro = models.BooleanField(blank=True, null=True)
    imbro_a = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gld"."type_measurement_instrument_type'
        verbose_name_plural = 'Measurement instrument types'


class TypeObservationType(models.Model):
    id = models.IntegerField(blank=True, primary_key=True)
    value = models.CharField(max_length=255, blank=True, null=True)
    definition_nl = models.CharField(max_length=255, blank=True, null=True)
    imbro = models.BooleanField(blank=True, null=True)
    imbro_a = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gld"."type_observation_type'
        verbose_name_plural = 'Observation types'


class TypeProcessReference(models.Model):
    id = models.IntegerField(blank=True, primary_key=True)
    value = models.CharField(max_length=255, blank=True, null=True)
    definition_nl = models.CharField(max_length=255, blank=True, null=True)
    imbro = models.BooleanField(blank=True, null=True)
    imbro_a = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gld"."type_process_reference'
        verbose_name_plural = 'Process references'


class TypeProcessType(models.Model):
    id = models.IntegerField(blank=True, primary_key=True)
    value = models.CharField(max_length=255, blank=True, null=True)
    definition_nl = models.CharField(max_length=255, blank=True, null=True)
    imbro = models.BooleanField(blank=True, null=True)
    imbro_a = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gld"."type_process_type'
        verbose_name_plural = 'Process types'


class TypeStatusCode(models.Model):
    id = models.IntegerField(blank=True, primary_key=True)
    value = models.CharField(max_length=255, blank=True, null=True)
    definition_nl = models.CharField(max_length=255, blank=True, null=True)
    imbro = models.BooleanField(blank=True, null=True)
    imbro_a = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gld"."type_status_code'
        verbose_name_plural = 'Status codes'


class TypeStatusQualityControl(models.Model):
    id = models.IntegerField(blank=True, primary_key=True)
    value = models.CharField(max_length=255, blank=True, null=True)
    definition_nl = models.CharField(max_length=255, blank=True, null=True)
    imbro = models.BooleanField(blank=True, null=True)
    imbro_a = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gld"."type_status_quality_control'
        verbose_name_plural = 'Quality control types'
        
#%% GMW Models

class DeliveredLocations(models.Model):
    location_id = models.AutoField(primary_key=True)
    registration_object_id = models.IntegerField(blank=True, null=True)
    coordinates = models.TextField(blank=True, null=True)  # This field type is a guess.
    referencesystem = models.TextField(blank=True, null=True)  # This field type is a guess.
    horizontal_positioning_method = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = True
        db_table = 'gmw"."delivered_locations'
        verbose_name_plural = 'Delivered locations'


class DeliveredVerticalPositions(models.Model):
    delivered_vertical_positions_id = models.AutoField(primary_key=True)
    registration_object_id = models.IntegerField(blank=True, null=True)
    local_vertical_reference_point = models.TextField(blank=True, null=True)  # This field type is a guess.
    offset = models.DecimalField(max_digits=6, decimal_places=3, blank=True, null=True)
    vertical_datum = models.TextField(blank=True, null=True)  # This field type is a guess.
    ground_level_position = models.DecimalField(max_digits=6, decimal_places=3, blank=True, null=True)
    ground_level_positioning_method = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = True
        db_table = 'gmw"."delivered_vertical_positions'
        verbose_name_plural  = 'Delivered vertical positions'


class GroundwaterMonitoringWells(models.Model):
    registration_object_id = models.AutoField(primary_key=True)
    registration_object_type = models.TextField(blank=True, null=True)  # This field type is a guess.
    bro_id = models.CharField(max_length=15, blank=True, null=True)
    request_reference = models.CharField(max_length=255, blank=True, null=True)
    delivery_accountable_party = models.IntegerField(blank=True, null=True)
    delivery_responsible_party = models.IntegerField(blank=True, null=True)
    quality_regime = models.TextField(blank=True, null=True)  # This field type is a guess.
    under_privilege = models.TextField(blank=True, null=True)  # This field type is a guess.
    delivery_context = models.TextField(blank=True, null=True)  # This field type is a guess.
    construction_standard = models.TextField(blank=True, null=True)  # This field type is a guess.
    initial_function = models.TextField(blank=True, null=True)  # This field type is a guess.
    number_of_standpipes = models.IntegerField(blank=True, null=True)
    ground_level_stable = models.TextField(blank=True, null=True)  # This field type is a guess.
    well_stability = models.TextField(blank=True, null=True)  # This field type is a guess.
    nitg_code = models.CharField(max_length=256, blank=True, null=True)
    olga_code = models.CharField(max_length=256, blank=True, null=True)
    well_code = models.CharField(max_length=256, blank=True, null=True)
    owner = models.IntegerField(blank=True, null=True)
    maintenance_responsible_party = models.IntegerField(blank=True, null=True)
    well_head_protector = models.TextField(blank=True, null=True)  # This field type is a guess.
    well_construction_date = models.DateField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gmw"."groundwater_monitoring_wells'
        verbose_name_plural = 'Groundwater monitoring wells'

class GroundwaterMonitoringTubes(models.Model):
    groundwater_monitoring_tube_id = models.IntegerField(primary_key=True)
    registration_object_id = models.IntegerField(blank=True, null=True)
    tube_number = models.IntegerField(blank=True, null=True)
    tube_type = models.TextField(blank=True, null=True)  # This field type is a guess.
    artesian_well_cap_present = models.TextField(blank=True, null=True)  # This field type is a guess.
    sediment_sump_present = models.TextField(blank=True, null=True)  # This field type is a guess.
    number_of_geo_ohm_cables = models.IntegerField(blank=True, null=True)
    tube_top_diameter = models.IntegerField(blank=True, null=True)
    variable_diameter = models.TextField(blank=True, null=True)  # This field type is a guess.
    tube_status = models.TextField(blank=True, null=True)  # This field type is a guess.
    tube_top_position = models.DecimalField(max_digits=6, decimal_places=3, blank=True, null=True)
    tube_top_positioning_method = models.TextField(blank=True, null=True)  # This field type is a guess.
    tube_packing_material = models.TextField(blank=True, null=True)  # This field type is a guess.
    tube_material = models.TextField(blank=True, null=True)  # This field type is a guess.
    glue = models.TextField(blank=True, null=True)  # This field type is a guess.
    screen_length = models.DecimalField(max_digits=6, decimal_places=3, blank=True, null=True)
    sock_material = models.TextField(blank=True, null=True)  # This field type is a guess.
    plain_tube_part_length = models.DecimalField(max_digits=6, decimal_places=3, blank=True, null=True)
    sediment_sump_length = models.DecimalField(max_digits=6, decimal_places=3, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gmw"."groundwater_monitoring_tubes'
        verbose_name_plural = 'Groundwater monitoring tubes'


#%% Aanlevering models


class gld_registration_log(models.Model):
    id = models.AutoField(primary_key=True)
    date_modified = models.CharField(max_length=254, null=True, blank=True)
    gwm_bro_id = models.CharField(max_length=254, null=True, blank=True)
    filter_id = models.CharField(max_length=254, null=True, blank=True)
    validation_status = models.CharField(max_length=254, null=True, blank=True)
    levering_id = models.CharField(max_length=254, null=True, blank=True)
    levering_status = models.CharField(max_length=254, null=True, blank=True)
    gld_bro_id = models.CharField(max_length=254, null=True, blank=True)
    comments = models.CharField(max_length=10000, null=True, blank=True)
    last_changed=models.CharField(max_length=254, null=True, blank=True)
    corrections_applied = models.BooleanField(blank=True, null=True)
    timestamp_end_registration=models.DateTimeField(blank=True, null=True)
    quality_regime=models.CharField(max_length=254, null=True, blank=True)
    file=models.CharField(max_length=254, null=True, blank=True)
    process_status=models.CharField(max_length=254, null=True, blank=True)

    class Meta:
        db_table='aanlevering"."gld_registration_log'
        verbose_name = "GLD registration logging"
        verbose_name_plural = "GLD registration logging"

class gld_addition_log(models.Model):
    date_modified = models.CharField(max_length=254, null=True, blank=True)
    observation_id = models.CharField(max_length=254, null=True, blank=True)
    start = models.CharField(max_length=254, null=True, blank=True)
    end = models.CharField(max_length=254, null=True, blank=True)
    broid_registration = models.CharField(max_length=254, null=True, blank=True)
    procedure_uuid = models.CharField(max_length=254, null=True, blank=True)
    procedure_initialized = models.CharField(max_length=254, null=True, blank=True)
    validation_status = models.CharField(max_length=254, null=True, blank=True)
    levering_id = models.CharField(max_length=254, null=True, blank=True)
    levering_status = models.CharField(max_length=254, null=True, blank=True)
    comments = models.CharField(max_length=50000, null=True, blank=True)
    file=models.CharField(max_length=254, null=True, blank=True)
    addition_type=models.CharField(max_length=254, null=True, blank=True)

    class Meta:
        db_table='aanlevering"."gld_addition_log'
        verbose_name = "GLD addition logging"
        verbose_name_plural = "GLD addition logging"

