# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
# Feel free to rename the models, but don't rename db_table values or field names.
from django.contrib.gis.db import models


class Analyses(models.Model):
    analysis_id = models.AutoField(
        primary_key=True,
        verbose_name="Analyse-ID",
    )
    analysis_process_id = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="Analyseproces-ID",
    )
    parameter_id = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="Parameter-ID",
    )
    analysis_measurement_value = models.DecimalField(
        max_digits=100,
        decimal_places=3,
        blank=True,
        null=True,
        verbose_name="Meetwaarde (analyse)",
    )
    limit_symbol = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        verbose_name="Grenssymbool",
    )
    reporting_limit = models.DecimalField(
        max_digits=100,
        decimal_places=3,
        blank=True,
        null=True,
        verbose_name="Rapportagegrens",
    )
    quality_control_status_id = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="Kwaliteitscontrole-status-ID",
    )

    class Meta:
        managed = True
        db_table = 'gar"."analyses'

        verbose_name = "Analyse"
        verbose_name_plural = "Analyses"


class AnalysisProcesses(models.Model):
    analysis_process_id = models.AutoField(
        primary_key=True, verbose_name="Analyseproces ID"
    )
    laboratory_analysis_id = models.IntegerField(
        blank=True, null=True, verbose_name="Laboratoriumanalyse ID"
    )
    analysis_date = models.DateTimeField(
        blank=True, null=True, verbose_name="Analyedatum"
    )
    analytical_technique_id = models.IntegerField(
        blank=True, null=True, verbose_name="Analytische techniek ID"
    )
    valuation_method_id = models.IntegerField(
        blank=True, null=True, verbose_name="Waarderingsmethode ID"
    )

    class Meta:
        managed = True
        db_table = 'gar"."analysis_processes'

        verbose_name = "Analyseproces"
        verbose_name_plural = "Analyseprocessen"


class Combi(models.Model):
    prov = models.CharField(
        max_length=2, blank=True, null=True, verbose_name="Provinciecode"
    )
    monsteridentificatie = models.CharField(
        max_length=128, blank=True, null=True, verbose_name="Monsteridentificatie"
    )
    meetobjectlokaalid = models.CharField(
        max_length=12, blank=True, null=True, verbose_name="Meetobject lokaal ID"
    )
    meetpuntidentificatie = models.CharField(
        max_length=18, blank=True, null=True, verbose_name="Meetpuntidentificatie"
    )
    resultaatdatum = models.DateTimeField(
        blank=True, null=True, verbose_name="Resultaatdatum"
    )
    grootheidcode = models.CharField(
        max_length=8, blank=True, null=True, verbose_name="Grootheidcode"
    )
    parametercode = models.CharField(
        max_length=20, blank=True, null=True, verbose_name="Parametercode"
    )
    limietsymbool = models.CharField(
        max_length=1, blank=True, null=True, verbose_name="Limietsymbool"
    )
    numeriekewaarde = models.FloatField(
        blank=True, null=True, verbose_name="Numerieke waarde"
    )
    meetronde = models.CharField(
        max_length=10, blank=True, null=True, verbose_name="Meetronde"
    )
    eenheidcode = models.CharField(
        max_length=6, blank=True, null=True, verbose_name="Eenheidscode"
    )
    hoedanigheidcode = models.CharField(
        max_length=3, blank=True, null=True, verbose_name="Hoedanigheidscode"
    )
    locatietypewaardebepalingid = models.IntegerField(
        blank=True, null=True, verbose_name="Locatietype waardebepaling ID"
    )
    parametercode_v = models.CharField(
        max_length=20, blank=True, null=True, verbose_name="Parametercode (V)"
    )

    class Meta:
        managed = True
        db_table = 'gar"."analysis_combiprocesses'

        verbose_name = "Combinatie"
        verbose_name_plural = "Combinaties"


class FieldMeasurements(models.Model):
    field_measurement_id = models.AutoField(
        primary_key=True, verbose_name="Veldmeting ID"
    )
    field_sample_id = models.IntegerField(
        blank=True, null=True, verbose_name="Veldmonster ID"
    )
    parameter_id = models.IntegerField(
        blank=True, null=True, verbose_name="Parameter ID"
    )
    field_measurement_value = models.DecimalField(
        max_digits=100,
        decimal_places=3,
        blank=True,
        null=True,
        verbose_name="Meetwaarde (veld)",
    )
    quality_control_status = models.IntegerField(
        blank=True, null=True, verbose_name="Kwaliteitscontrole status"
    )

    class Meta:
        managed = True
        db_table = 'gar"."field_measurements'

        verbose_name = "Veldmeting"
        verbose_name_plural = "Veldmetingen"


class FieldObservations(models.Model):
    field_observation_id = models.AutoField(
        primary_key=True, verbose_name="Veldobservatie ID"
    )
    field_sample_id = models.IntegerField(
        blank=True, null=True, verbose_name="Veldmonster ID"
    )
    primary_colour_id = models.IntegerField(
        blank=True, null=True, verbose_name="Primaire kleur ID"
    )
    secondary_colour_id = models.IntegerField(
        blank=True, null=True, verbose_name="Secundaire kleur ID"
    )
    colour_strength_id = models.IntegerField(
        blank=True, null=True, verbose_name="Kleurintensiteit ID"
    )
    abnormality_in_cooling = models.BooleanField(
        blank=True, null=True, verbose_name="Afwijking in koeling"
    )
    abnormality_in_device = models.BooleanField(
        blank=True, null=True, verbose_name="Afwijking in apparatuur"
    )
    polluted_by_engine = models.BooleanField(
        blank=True, null=True, verbose_name="Vervuild door pomp/motor"
    )
    filter_aerated = models.BooleanField(
        blank=True, null=True, verbose_name="Filter belucht"
    )
    groundwater_level_dropped_too_much = models.BooleanField(
        blank=True, null=True, verbose_name="Grondwaterstand te ver gedaald"
    )
    abnormal_filter = models.BooleanField(
        blank=True, null=True, verbose_name="Afwijkend filter"
    )
    sample_aerated = models.BooleanField(
        blank=True, null=True, verbose_name="Monster belucht"
    )
    hose_reused = models.BooleanField(
        blank=True, null=True, verbose_name="Slang hergebruikt"
    )
    temperature_difficult_to_measure = models.BooleanField(
        blank=True, null=True, verbose_name="Temperatuur moeilijk te meten"
    )

    class Meta:
        managed = True
        db_table = 'gar"."field_observations'

        verbose_name = "Veldobservatie"
        verbose_name_plural = "Veldobservaties"


class FieldSamples(models.Model):
    field_sample_id = models.AutoField(primary_key=True, verbose_name="Veldmonster ID")
    groundwater_composition_research_id = models.IntegerField(
        blank=True, null=True, verbose_name="Onderzoek samenstelling grondwater ID"
    )
    delivery_accountable_party = models.IntegerField(
        blank=True, null=True, verbose_name="Verantwoordelijke partij levering"
    )
    quality_control_method = models.IntegerField(
        blank=True, null=True, verbose_name="Kwaliteitscontrolemethode"
    )
    sampling_datetime = models.DateTimeField(
        blank=True, null=True, verbose_name="Bemonsteringsdatum en -tijd"
    )
    sampling_operator = models.IntegerField(
        blank=True, null=True, verbose_name="Bemonsteraar"
    )
    sampling_standard = models.IntegerField(
        blank=True, null=True, verbose_name="Bemonsteringsnorm"
    )
    pump_type = models.IntegerField(blank=True, null=True, verbose_name="Pompsoort")

    class Meta:
        managed = True
        db_table = 'gar"."field_samples'
        verbose_name = "Veldmonster"
        verbose_name_plural = "Veldmonsters"


class GroundwaterCompositionResearches(models.Model):
    groundwater_composition_research_id = models.AutoField(
        primary_key=True, verbose_name="Onderzoek samenstelling grondwater ID"
    )
    groundwater_monitoring_tube_id = models.IntegerField(
        blank=True, null=True, verbose_name="Grondwatermonitoringsbuis ID"
    )
    local_id = models.CharField(
        max_length=40, blank=True, null=True, verbose_name="Lokale ID"
    )
    assessment_procedure_id = models.IntegerField(
        blank=True, null=True, verbose_name="Beoordelingsprocedure ID"
    )
    pesticides_examined = models.IntegerField(
        blank=True, null=True, verbose_name="Pesticiden onderzocht"
    )
    pharmaceutical_examined = models.IntegerField(
        blank=True, null=True, verbose_name="Geneesmiddelen onderzocht"
    )

    class Meta:
        managed = True
        db_table = 'gar"."groundwater_composition_researches'
        verbose_name = "Onderzoek samenstelling grondwater"
        verbose_name_plural = "Onderzoeken samenstelling grondwater"


class LaboratoryAnalyses(models.Model):
    laboratory_analysis_id = models.AutoField(
        primary_key=True, verbose_name="Laboratoriumanalyse ID"
    )
    groundwater_composition_research_id = models.IntegerField(
        blank=True, null=True, verbose_name="Onderzoek samenstelling grondwater ID"
    )
    responsible_laboratory = models.IntegerField(
        blank=True, null=True, verbose_name="Verantwoordelijk laboratorium"
    )

    class Meta:
        managed = True
        db_table = 'gar"."laboratory_analyses'
        verbose_name = "Laboratoriumanalyse"
        verbose_name_plural = "Laboratoriumanalyses"


class StoffenGroepen(models.Model):
    stoffen_percelen_id = models.IntegerField(verbose_name="Stoffen percelen ID")
    cas_nummer = models.CharField(blank=True, null=True, verbose_name="CAS-nummer")
    parametercode = models.CharField(
        max_length=20, blank=True, null=True, verbose_name="Parametercode"
    )
    parameter = models.CharField(blank=True, null=True, verbose_name="Parameter")
    eenheidcode_str = models.CharField(
        blank=True, null=True, verbose_name="Eenheidscode"
    )
    stofgroep = models.IntegerField(blank=True, null=True, verbose_name="Stofgroep")
    rapportgrens = models.FloatField(
        blank=True, null=True, verbose_name="Rapportagegrens"
    )
    stofgroep_omschrijving = models.CharField(
        blank=True, null=True, verbose_name="Omschrijving stofgroep"
    )
    toetswaarde = models.FloatField(blank=True, null=True, verbose_name="Toetswaarde")

    class Meta:
        managed = True
        db_table = 'gar"."stoffen_groepen'
        verbose_name = "Stofgroep"
        verbose_name_plural = "Stofgroepen"


class TypeColourStrengths(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    omschrijving = models.CharField(blank=True, null=True, verbose_name="Omschrijving")
    waarde = models.CharField(blank=True, null=True, verbose_name="Waarde")
    d_begin = models.DateTimeField(blank=True, null=True, verbose_name="Begindatum")
    d_status = models.CharField(
        max_length=1, blank=True, null=True, verbose_name="Status"
    )

    class Meta:
        managed = True
        db_table = 'gar"."type_colour_strengths'
        verbose_name = "Type kleursterkte"
        verbose_name_plural = "Type kleursterktes"


class TypeColours(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    description = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Omschrijving"
    )
    value = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Waarde"
    )
    startingtime = models.DateTimeField(
        blank=True, null=True, verbose_name="Begindatum"
    )
    status = models.CharField(
        max_length=1, blank=True, null=True, verbose_name="Status"
    )

    class Meta:
        managed = True
        db_table = 'gar"."type_colours'
        verbose_name = "Type kleur"
        verbose_name_plural = "Type kleuren"


class TypeParameterlijsten(models.Model):
    parameter_id = models.IntegerField(primary_key=True, verbose_name="Parameter ID")
    bro_id = models.IntegerField(blank=True, null=True, verbose_name="BRO ID")
    aquocode = models.CharField(blank=True, null=True, verbose_name="Aquocode")
    cas_nummer = models.CharField(blank=True, null=True, verbose_name="CAS-nummer")
    omschrijving = models.CharField(blank=True, null=True, verbose_name="Omschrijving")
    eenheid = models.CharField(blank=True, null=True, verbose_name="Eenheid")
    hoedanigheid = models.CharField(blank=True, null=True, verbose_name="Hoedanigheid")

    class Meta:
        managed = True
        db_table = 'gar"."type_parameterlijsten'
        verbose_name = "Type parameterlijst"
        verbose_name_plural = "Type parameterlijsten"


class TypeWaardebepalingsmethodes(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    code = models.CharField(max_length=255, blank=True, null=True, verbose_name="Code")
    omschrijving = models.CharField(blank=True, null=True, verbose_name="Omschrijving")
    groep = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Groep"
    )
    d_begin = models.DateTimeField(blank=True, null=True, verbose_name="Begindatum")
    d_status = models.CharField(
        max_length=1, blank=True, null=True, verbose_name="Status"
    )
    titel = models.CharField(blank=True, null=True, verbose_name="Titel")

    class Meta:
        managed = True
        db_table = 'gar"."type_waardebepalingsmethodes'
        verbose_name = "Type waardebepalingsmethode"
        verbose_name_plural = "Type waardebepalingsmethodes"


class TypeWaardebepalingstechnieken(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    code = models.CharField(max_length=255, blank=True, null=True, verbose_name="Code")
    omschrijving = models.CharField(blank=True, null=True, verbose_name="Omschrijving")
    d_begin = models.DateTimeField(blank=True, null=True, verbose_name="Begindatum")
    d_status = models.CharField(
        max_length=1, blank=True, null=True, verbose_name="Status"
    )

    class Meta:
        managed = True
        db_table = 'gar"."type_waardebepalingstechnieken'

        verbose_name = "Type waardebepalingstechniek"
        verbose_name_plural = "Type waardebepalingstechnieken"
