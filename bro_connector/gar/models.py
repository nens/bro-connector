# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.contrib.gis.db import models


class Analyses(models.Model):
    analysis_id = models.AutoField(primary_key=True)
    analysis_process_id = models.IntegerField(blank=True, null=True)
    parameter_id = models.IntegerField(blank=True, null=True)
    analysis_measurement_value = models.DecimalField(
        max_digits=65535, decimal_places=3, blank=True, null=True
    )
    limit_symbol = models.CharField(max_length=1, blank=True, null=True)
    reporting_limit = models.DecimalField(
        max_digits=65535, decimal_places=3, blank=True, null=True
    )
    quality_control_status_id = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gar"."analyses'


class AnalysisProcesses(models.Model):
    analysis_process_id = models.AutoField(primary_key=True)
    laboratory_analysis_id = models.IntegerField(blank=True, null=True)
    analysis_date = models.DateTimeField(blank=True, null=True)
    analytical_technique_id = models.IntegerField(blank=True, null=True)
    valuation_method_id = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gar"."analysis_processes'


class Combi(models.Model):
    prov = models.CharField(max_length=2, blank=True, null=True)
    monsteridentificatie = models.CharField(max_length=128, blank=True, null=True)
    meetobjectlokaalid = models.CharField(max_length=12, blank=True, null=True)
    meetpuntidentificatie = models.CharField(max_length=18, blank=True, null=True)
    resultaatdatum = models.DateTimeField(blank=True, null=True)
    grootheidcode = models.CharField(max_length=8, blank=True, null=True)
    parametercode = models.CharField(max_length=20, blank=True, null=True)
    limietsymbool = models.CharField(max_length=1, blank=True, null=True)
    numeriekewaarde = models.FloatField(blank=True, null=True)
    meetronde = models.CharField(max_length=10, blank=True, null=True)
    eenheidcode = models.CharField(max_length=6, blank=True, null=True)
    hoedanigheidcode = models.CharField(max_length=3, blank=True, null=True)
    locatietypewaardebepalingid = models.IntegerField(blank=True, null=True)
    parametercode_v = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gar"."analysis_combiprocesses'


class FieldMeasurements(models.Model):
    field_measurement_id = models.AutoField(primary_key=True)
    field_sample_id = models.IntegerField(blank=True, null=True)
    parameter_id = models.IntegerField(blank=True, null=True)
    field_measurement_value = models.DecimalField(
        max_digits=65535, decimal_places=3, blank=True, null=True
    )
    quality_control_status = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gar"."field_measurements'


class FieldObservations(models.Model):
    field_observation_id = models.AutoField(primary_key=True)
    field_sample_id = models.IntegerField(blank=True, null=True)
    primary_colour_id = models.IntegerField(blank=True, null=True)
    secondary_colour_id = models.IntegerField(blank=True, null=True)
    colour_strength_id = models.IntegerField(blank=True, null=True)
    abnormality_in_cooling = models.BooleanField(blank=True, null=True)
    abnormality_in_device = models.BooleanField(blank=True, null=True)
    polluted_by_engine = models.BooleanField(blank=True, null=True)
    filter_aerated = models.BooleanField(blank=True, null=True)
    groundwater_level_dropped_too_much = models.BooleanField(blank=True, null=True)
    abnormal_filter = models.BooleanField(blank=True, null=True)
    sample_aerated = models.BooleanField(blank=True, null=True)
    hose_reused = models.BooleanField(blank=True, null=True)
    temperature_difficult_to_measure = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gar"."field_observations'


class FieldSamples(models.Model):
    field_sample_id = models.AutoField(primary_key=True)
    groundwater_composition_research_id = models.IntegerField(blank=True, null=True)
    delivery_accountable_party = models.IntegerField(blank=True, null=True)
    quality_control_method = models.IntegerField(blank=True, null=True)
    sampling_datetime = models.DateTimeField(blank=True, null=True)
    sampling_operator = models.IntegerField(blank=True, null=True)
    sampling_standard = models.IntegerField(blank=True, null=True)
    pump_type = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gar"."field_samples'


class GroundwaterCompositionResearches(models.Model):
    groundwater_composition_research_id = models.AutoField(primary_key=True)
    groundwater_monitoring_tube_id = models.IntegerField(blank=True, null=True)
    local_id = models.CharField(max_length=40, blank=True, null=True)
    assessment_procedure_id = models.IntegerField(blank=True, null=True)
    pesticides_examined = models.IntegerField(blank=True, null=True)
    pharmaceutical_examined = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gar"."groundwater_composition_researches'


class LaboratoryAnalyses(models.Model):
    laboratory_analysis_id = models.AutoField(primary_key=True)
    groundwater_composition_research_id = models.IntegerField(blank=True, null=True)
    responsible_laboratory = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gar"."laboratory_analyses'


class StoffenGroepen(models.Model):
    stoffen_percelen_id = models.IntegerField()
    cas_nummer = models.CharField(blank=True, null=True)
    parametercode = models.CharField(max_length=20, blank=True, null=True)
    parameter = models.CharField(blank=True, null=True)
    eenheidcode_str = models.CharField(blank=True, null=True)
    stofgroep = models.IntegerField(blank=True, null=True)
    rapportgrens = models.FloatField(blank=True, null=True)
    stofgroep_omschrijving = models.CharField(blank=True, null=True)
    toetswaarde = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gar"."stoffen_groepen'


class TypeColourStrengths(models.Model):
    id = models.IntegerField(primary_key=True)
    omschrijving = models.CharField(blank=True, null=True)
    waarde = models.CharField(blank=True, null=True)
    d_begin = models.DateTimeField(blank=True, null=True)
    d_status = models.CharField(max_length=1, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gar"."type_colour_strengths'


class TypeColours(models.Model):
    id = models.IntegerField(primary_key=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    value = models.CharField(max_length=255, blank=True, null=True)
    startingtime = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=1, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gar"."type_colours'


class TypeParameterlijsten(models.Model):
    parameter_id = models.IntegerField(primary_key=True)
    bro_id = models.IntegerField(blank=True, null=True)
    aquocode = models.CharField(blank=True, null=True)
    cas_nummer = models.CharField(blank=True, null=True)
    omschrijving = models.CharField(blank=True, null=True)
    eenheid = models.CharField(blank=True, null=True)
    hoedanigheid = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gar"."type_parameterlijsten'


class TypeWaardebepalingsmethodes(models.Model):
    id = models.IntegerField(primary_key=True)
    code = models.CharField(max_length=255, blank=True, null=True)
    omschrijving = models.CharField(blank=True, null=True)
    groep = models.CharField(max_length=255, blank=True, null=True)
    d_begin = models.DateTimeField(blank=True, null=True)
    d_status = models.CharField(max_length=1, blank=True, null=True)
    titel = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gar"."type_waardebepalingsmethodes'


class TypeWaardebepalingstechnieken(models.Model):
    id = models.IntegerField(primary_key=True)
    code = models.CharField(max_length=255, blank=True, null=True)
    omschrijving = models.CharField(blank=True, null=True)
    d_begin = models.DateTimeField(blank=True, null=True)
    d_status = models.CharField(max_length=1, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gar"."type_waardebepalingstechnieken'
