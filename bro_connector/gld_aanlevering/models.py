# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = True` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models
from django.contrib.gis.db import models as geo_models


#%% GLD Models


class GroundwaterLevelDossier(models.Model):
    groundwater_level_dossier_id = models.AutoField(primary_key=True)
    #groundwater_monitoring_tube = models.ForeignKey('GroundwaterMonitoringTubes', on_delete = models.CASCADE,null = True, blank = True)
    groundwater_monitoring_tube_id = models.IntegerField(blank=True, null=True)
    gmw_bro_id = models.CharField(max_length=255, blank=True, null=True)
    gld_bro_id = models.CharField(max_length=255, blank=True, null=True)
    research_start_date = models.DateField(blank=True, null=True)
    research_last_date = models.DateField(blank=True, null=True)
    research_last_correction = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return('{}'.format(str(self.gld_bro_id)))

    class Meta:
        managed = True
        db_table = 'gld"."groundwater_level_dossier'
        verbose_name = "Groundwaterlevel dossier"
        verbose_name_plural = "Groundwaterlevel dossier"



class MeasurementPointMetadata(models.Model):
    measurement_point_metadata_id = models.AutoField(primary_key=True)
    #qualifier_by_category = models.IntegerField(blank=True, null=True)
    qualifier_by_category = models.ForeignKey('TypeStatusQualityControl', on_delete = models.CASCADE, null = True, blank = True)
    #censored_reason = models.IntegerField(blank=True, null=True)
    censored_reason = models.ForeignKey('TypeCensoredReasonCode', on_delete = models.CASCADE, null = True, blank = True)
    qualifier_by_quantity = models.DecimalField(
        max_digits=100, decimal_places=10, blank=True, null=True
    )
    #interpolation_code = models.IntegerField(blank=True, null=True)
    interpolation_code = models.ForeignKey('TypeInterpolationCode', models.CASCADE, null = True, blank = True)    

    class Meta:
        managed = True
        app_label = "gld_aanlevering"
        db_table = 'gld"."measurement_point_metadata'
        verbose_name = "Measurement point metadata"
        verbose_name_plural = "Measurement point metadata"






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
#         verbose_name_plural = 'Measurement timeserTrueies tvp observation'


class Observation(models.Model):
    observation_id=models.AutoField(primary_key=True, null=False,blank=False)
   # idid=models.IntegerField(null=True,blank=True)
    observationperiod = models.DurationField(blank=True, null=True)
    observation_starttime = models.DateTimeField(blank=True, null=True)
    result_time = models.DateTimeField(blank=True, null=True)
    observation_endtime = models.DateTimeField(blank=True, null=True)
    observation_metadata = models.ForeignKey('ObservationMetadata' , on_delete = models.CASCADE, null = True, blank = True)
    #observation_metadata_id = models.IntegerField(blank=True, null=True)
    observation_process = models.ForeignKey('ObservationProcess', on_delete = models.CASCADE, null = True, blank = True)
    #observation_process_id = models.IntegerField(blank=True, null=True)
    groundwater_level_dossier = models.ForeignKey('GroundwaterLevelDossier', on_delete = models.CASCADE, null = True, blank = True)
    #groundwater_level_dossier_id = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):

        try:
            starttime = str(self.observation_starttime.date())
        except:
            starttime = '?'

        try:
            endtime = str(self.observation_endtime.date())
        except:
            endtime = '?'

        try:
            dossier = str(self.groundwater_level_dossier.gld_bro_id)
        except:
            dossier = 'Registratie onbekend'

        try:
            status = str(self.observation_metadata.status)
        except:
            status = 'Status onbekend'

        return('{}, {}, {} - {}'.format(dossier, status, starttime, endtime))


    class Meta:
        managed = True
        db_table = 'gld"."observation'
        verbose_name = "Observation"
        verbose_name_plural = "Observations"

class MeasurementTvp(models.Model):
    measurement_tvp_id = models.AutoField(primary_key=True)
    observation = models.ForeignKey(Observation, on_delete=models.CASCADE, null = True, blank = True)
    #measurement_time_series_id = models.IntegerField(blank=True, null=True)
    measurement_time = models.DateTimeField(blank=True, null=True)
    field_value = models.DecimalField(
        max_digits=100, decimal_places=10, blank=True, null=True
    )
    field_value_unit = models.CharField(max_length=255, blank=True, null=True)
    calculated_value = models.DecimalField(
        max_digits=100, decimal_places=10, blank=True, null=True
    )
    corrected_value = models.DecimalField(
        max_digits=100, decimal_places=10, blank=True, null=True
    )
    correction_time = models.DateTimeField(blank=True, null=True) 
    correction_reason = models.CharField(max_length=255, blank=True, null=True)
    measurement_point_metadata = models.ForeignKey('MeasurementPointMetadata', on_delete = models.CASCADE, null = True, blank = True)
    #measurement_point_metadata_id = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gld"."measurement_tvp'
        verbose_name = "Measurement time-value pairs"
        verbose_name_plural = "Measurement time-value pairs"

class ObservationMetadata(models.Model):
    observation_metadata_id = models.AutoField(primary_key=True)
    date_stamp = models.DateField(blank=True, null=True)
    # parameter_measurement_serie_type = models.IntegerField(blank=True, null=True) 
    parameter_measurement_serie_type = models.ForeignKey('TypeObservationType', blank=True,  null=True, on_delete = models.CASCADE) 
    #status = models.IntegerField(blank=True, null=True) 
    status = models.ForeignKey('TypeStatusCode', on_delete = models.CASCADE, null = True, blank = True) 
    #responsible_party_id = models.IntegerField(blank=True, null=True)
    responsible_party = models.ForeignKey('ResponsibleParty', on_delete = models.CASCADE, null = True, blank = True)

    def __str__(self):
        return('{}, {}, {}'.format(str(self.date_stamp),str(self.status.value),self.responsible_party.organisation_name))

    class Meta:
        managed = True
        db_table = 'gld"."observation_metadata'
        verbose_name = "Observation metadata"
        verbose_name_plural = "Observation metadata"


class ObservationProcess(models.Model):
    observation_process_id = models.AutoField(primary_key=True)
    #process_reference = models.IntegerField(blank=True, null=True)
    process_reference = models.ForeignKey('TypeProcessReference', on_delete=models.CASCADE, blank = True, null = True)
    #parameter_measurement_instrument_type = models.IntegerField(blank=True, null=True)
    parameter_measurement_instrument_type = models.ForeignKey('TypeMeasurementInstrumentType', on_delete=models.CASCADE, null = True, blank = True)
    # parameter_air_pressure_compensation_type = models.IntegerField(
    #     blank=True, null=True
    # )
    parameter_air_pressure_compensation_type = models.ForeignKey('TypeAirPressureCompensation', on_delete=models.CASCADE, null = True, blank = True)
    #process_type = models.IntegerField(blank=True, null=True)    
    process_type = models.ForeignKey('TypeProcessType', on_delete=models.CASCADE, null = True, blank = True)
    #parameter_evaluation_procedure = models.IntegerField(blank=True, null=True)
    parameter_evaluation_procedure = models.ForeignKey('TypeEvaluationProcedure', on_delete=models.CASCADE, null = True, blank = True)

    def __str__(self):
        return(str(self.observation_process_id))

    class Meta:
        managed = True
        db_table = 'gld"."observation_process'
        verbose_name = "Observation process"
        verbose_name_plural = "Observation process"


class ResponsibleParty(models.Model):
    responsible_party_id = models.AutoField(primary_key=True)
    identification = models.IntegerField(blank=True, null=True) 
    organisation_name = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gld"."responsible_party'
        verbose_name = "Responsible party"
        verbose_name_plural = "Responsible party"

    def __str__(self):
        return "{}".format(self.organisation_name)

class TypeAirPressureCompensation(models.Model):
    id = models.IntegerField(blank=True, primary_key=True)
    value = models.CharField(max_length=255, blank=True, null=True)
    definition_nl = models.CharField(max_length=255, blank=True, null=True)
    imbro = models.BooleanField(blank=True, null=True)
    imbro_a = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gld"."type_air_pressure_compensation'
        verbose_name_plural = "Air pressure compensation"

    def __str__(self):
        return "{}".format(self.value)

class TypeCensoredReasonCode(models.Model):
    id = models.IntegerField(blank=True, primary_key=True)
    value = models.CharField(max_length=255, blank=True, null=True)
    definition_nl = models.CharField(max_length=255, blank=True, null=True)
    imbro = models.BooleanField(blank=True, null=True)
    imbro_a = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gld"."type_censored_reason_code'
        verbose_name_plural = "Censor reasons"

    def __str__(self):
        return "{}".format(self.value)

class TypeEvaluationProcedure(models.Model):
    id = models.IntegerField(blank=True, primary_key=True)
    value = models.CharField(max_length=255, blank=True, null=True)
    definition_nl = models.CharField(max_length=255, blank=True, null=True)
    imbro = models.BooleanField(blank=True, null=True)
    imbro_a = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gld"."type_evaluation_procedure'
        verbose_name_plural = "Evaluation procedures"

    def __str__(self):
        return "{}".format(self.value)

class TypeInterpolationCode(models.Model):
    id = models.IntegerField(blank=True, primary_key=True)
    value = models.CharField(max_length=255, blank=True, null=True)
    definition_nl = models.CharField(max_length=255, blank=True, null=True)
    imbro = models.BooleanField(blank=True, null=True)
    imbro_a = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gld"."type_interpolation_code'
        verbose_name_plural = "Interpolation codes"

    def __str__(self):
        return "{}".format(self.value)

class TypeMeasurementInstrumentType(models.Model):
    id = models.IntegerField(blank=True, primary_key=True)
    value = models.CharField(max_length=255, blank=True, null=True)
    definition_nl = models.CharField(max_length=255, blank=True, null=True)
    imbro = models.BooleanField(blank=True, null=True)
    imbro_a = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gld"."type_measurement_instrument_type'
        verbose_name_plural = "Measurement instrument types"

    def __str__(self):
        return "{}".format(self.value)

class TypeObservationType(models.Model):
    id = models.IntegerField(blank=True, primary_key=True)
    value = models.CharField(max_length=255, blank=True, null=True)
    definition_nl = models.CharField(max_length=255, blank=True, null=True)
    imbro = models.BooleanField(blank=True, null=True)
    imbro_a = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gld"."type_observation_type'
        verbose_name_plural = "Observation types"

    def __str__(self):
        return "{}".format(self.value)

class TypeProcessReference(models.Model):
    id = models.IntegerField(blank=True, primary_key=True)
    value = models.CharField(max_length=255, blank=True, null=True)
    definition_nl = models.CharField(max_length=255, blank=True, null=True)
    imbro = models.BooleanField(blank=True, null=True)
    imbro_a = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gld"."type_process_reference'
        verbose_name_plural = "Process references"

    def __str__(self):
        return "{}".format(self.value)

class TypeProcessType(models.Model):
    id = models.IntegerField(blank=True, primary_key=True)
    value = models.CharField(max_length=255, blank=True, null=True)
    definition_nl = models.CharField(max_length=255, blank=True, null=True)
    imbro = models.BooleanField(blank=True, null=True)
    imbro_a = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gld"."type_process_type'
        verbose_name_plural = "Process types"

    def __str__(self):
        return "{}".format(self.value)

class TypeStatusCode(models.Model):
    id = models.IntegerField(blank=True, primary_key=True)
    value = models.CharField(max_length=255, blank=True, null=True)
    definition_nl = models.CharField(max_length=255, blank=True, null=True)
    imbro = models.BooleanField(blank=True, null=True)
    imbro_a = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gld"."type_status_code'
        verbose_name_plural = "Status codes"

    def __str__(self):
        return "{}".format(self.value)

class TypeStatusQualityControl(models.Model):
    id = models.IntegerField(blank=True, primary_key=True)
    value = models.CharField(max_length=255, blank=True, null=True)
    definition_nl = models.CharField(max_length=255, blank=True, null=True)
    imbro = models.BooleanField(blank=True, null=True)
    imbro_a = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gld"."type_status_quality_control'
        verbose_name_plural = "Quality control types"

    def __str__(self):
        return "{}".format(self.value)

#
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
    last_changed = models.CharField(max_length=254, null=True, blank=True)
    corrections_applied = models.BooleanField(blank=True, null=True)
    timestamp_end_registration = models.DateTimeField(blank=True, null=True)
    quality_regime = models.CharField(max_length=254, null=True, blank=True)
    file = models.CharField(max_length=254, null=True, blank=True)
    process_status = models.CharField(max_length=254, null=True, blank=True)

    class Meta:
        db_table = 'aanlevering"."gld_registration_log'
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
    file = models.CharField(max_length=254, null=True, blank=True)
    addition_type = models.CharField(max_length=254, null=True, blank=True)

    class Meta:
        db_table = 'aanlevering"."gld_addition_log'
        verbose_name = "GLD addition logging"
        verbose_name_plural = "GLD addition logging"
