# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = True` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models
from .choices import *
from gmw.models import GroundwaterMonitoringTubeStatic
import datetime


# %% GLD Models


class GroundwaterLevelDossier(models.Model):
    groundwater_level_dossier_id = models.AutoField(primary_key=True)
    groundwater_monitoring_tube = models.ForeignKey(
        GroundwaterMonitoringTubeStatic,
        on_delete=models.CASCADE,
        null=True,
        blank=False,
    )
    gmw_bro_id = models.CharField(max_length=255, blank=True, null=True)
    gld_bro_id = models.CharField(max_length=255, blank=True, null=True)
    research_start_date = models.DateField(blank=True, null=True)
    research_last_date = models.DateField(blank=True, null=True)
    research_last_correction = models.DateTimeField(blank=True, null=True)

    @property
    def tube_number(self):
        return self.groundwater_monitoring_tube.tube_number

    def __str__(self):
        return f"{self.gld_bro_id}"

    class Meta:
        managed = True
        db_table = 'gld"."groundwater_level_dossier'
        verbose_name = "Grondwaterstand dossier"
        verbose_name_plural = "Grondwaterstand dossiers"


class Observation(models.Model):
    observation_id = models.AutoField(primary_key=True, null=False, blank=False)
    observationperiod = models.DurationField(blank=True, null=True)
    observation_starttime = models.DateTimeField(blank=True, null=True)
    result_time = models.DateTimeField(blank=True, null=True)
    observation_endtime = models.DateTimeField(blank=True, null=True)
    observation_metadata = models.ForeignKey(
        "ObservationMetadata", on_delete=models.CASCADE, null=True, blank=True
    )
    observation_process = models.ForeignKey(
        "ObservationProcess", on_delete=models.CASCADE, null=True, blank=True
    )
    groundwater_level_dossier = models.ForeignKey(
        "GroundwaterLevelDossier", on_delete=models.CASCADE, null=True, blank=True
    )
    up_to_date_in_bro = models.BooleanField(default=True, editable=False)

    @property
    def status(self):
        return self.observation_metadata.status

    def __str__(self):
        try:
            starttime = str(self.observation_starttime.date())
        except:
            starttime = "?"

        try:
            endtime = str(self.observation_endtime.date())
        except:
            endtime = "?"

        try:
            dossier = str(self.groundwater_level_dossier.gld_bro_id)
        except:
            dossier = "Registratie onbekend"

        return "{} ({} - {})".format(dossier, starttime, endtime)

    def save(self, *args, **kwargs):
        if self.pk == None:
            super().save(*args, **kwargs)
            return

        if self.observation_endtime is None:
            super().save(*args, **kwargs)
            return

        if self.observation_endtime <= datetime.datetime.now().astimezone():
            super().save(*args, **kwargs)

            # Create a duplicate metadata
            metadata = self.observation_metadata
            metadata.observation_metadata_id = None
            metadata.save()

            # Create a duplicate process
            process = self.observation_process
            process.observation_process_id = None
            process.save()

            obs = Observation.objects.create(
                observation_starttime=self.observation_endtime,
                groundwater_level_dossier=self.groundwater_level_dossier,
                observation_metadata=metadata,
                observation_process=process,
            )

    class Meta:
        managed = True
        db_table = 'gld"."observation'
        verbose_name = "Observatie"
        verbose_name_plural = "Observaties"


class ObservationMetadata(models.Model):
    observation_metadata_id = models.AutoField(primary_key=True)
    date_stamp = models.DateField(blank=True, null=True)
    observation_type = models.CharField(
        choices=OBSERVATIONTYPE, max_length=200, blank=True, null=True
    )
    status = models.CharField(choices=STATUSCODE, max_length=200, blank=True, null=True)
    responsible_party = models.ForeignKey(
        "ResponsibleParty", on_delete=models.CASCADE, null=True, blank=True
    )

    def __str__(self):
        return "{}, {}, {}".format(
            str(self.date_stamp),
            str(self.status),
            self.responsible_party.organisation_name,
        )

    class Meta:
        managed = True
        db_table = 'gld"."observation_metadata'
        verbose_name = "Observatie Metadata"
        verbose_name_plural = "Observatie Metadata"


class ObservationProcess(models.Model):
    observation_process_id = models.AutoField(primary_key=True)
    process_reference = models.CharField(
        choices=PROCESSREFERENCE, max_length=200, blank=True, null=True
    )
    measurement_instrument_type = models.CharField(
        choices=MEASUREMENTINSTRUMENTTYPE, max_length=200, blank=True, null=True
    )
    air_pressure_compensation_type = models.CharField(
        choices=AIRPRESSURECOMPENSATIONTYPE, max_length=200, blank=True, null=True
    )
    process_type = models.CharField(
        choices=PROCESSTYPE, max_length=200, blank=True, null=True
    )
    evaluation_procedure = models.CharField(
        choices=EVALUATIONPROCEDURE, max_length=200, blank=True, null=True
    )

    def __str__(self):
        return str(self.observation_process_id)

    class Meta:
        managed = True
        db_table = 'gld"."observation_process'
        verbose_name = "Observatie Process"
        verbose_name_plural = "Observatie Process"


# MEASUREMENT TIME VALUE PAIR
class MeasurementTvp(models.Model):
    measurement_tvp_id = models.AutoField(primary_key=True)
    observation = models.ForeignKey(
        Observation, on_delete=models.CASCADE, null=True, blank=True
    )
    measurement_time = models.DateTimeField(blank=True, null=True)
    field_value = models.DecimalField(
        max_digits=25, decimal_places=3, blank=True, null=True
    )
    field_value_unit = models.CharField(max_length=255, blank=True, null=True)
    calculated_value = models.DecimalField(
        max_digits=25, decimal_places=5, blank=True, null=True
    )
    corrected_value = models.DecimalField(
        max_digits=25, decimal_places=5, blank=True, null=True
    )
    correction_time = models.DateTimeField(blank=True, null=True)
    correction_reason = models.CharField(max_length=255, blank=True, null=True)
    measurement_point_metadata = models.ForeignKey(
        "MeasurementPointMetadata", on_delete=models.CASCADE, null=True, blank=True
    )

    class Meta:
        managed = True
        db_table = 'gld"."measurement_tvp'
        verbose_name = "Metingen Tijd-Waarde paren"
        verbose_name_plural = "Metingen Tijd-Waarde paren"


class MeasurementPointMetadata(models.Model):
    measurement_point_metadata_id = models.AutoField(primary_key=True)
    status_quality_control = models.CharField(
        choices=STATUSQUALITYCONTROL, max_length=200, blank=True, null=True
    )
    censor_reason = models.CharField(
        choices=CENSORREASON, max_length=200, blank=True, null=True
    )
    censor_reason_artesia = models.CharField(
        max_length=200, blank=True, null=True
    )
    value_limit = models.DecimalField(
        max_digits=100, decimal_places=10, blank=True, null=True
    )
    interpolation_code = models.CharField(
        choices=INTERPOLATIONTYPE, max_length=200, blank=True, null=True
    )

    class Meta:
        managed = True
        app_label = "gld"
        db_table = 'gld"."measurement_point_metadata'
        verbose_name = "Meetpunt Metadata"
        verbose_name_plural = "Meetpunt Metadata"

    def __str__(self):
        return str(self.measurement_point_metadata_id)


class ResponsibleParty(models.Model):
    responsible_party_id = models.AutoField(primary_key=True)
    identification = models.IntegerField(blank=True, null=True)
    organisation_name = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'gld"."responsible_party'
        verbose_name = "Verantwoordelijke Partij"
        verbose_name_plural = "Verantwoordelijke Partij"

    def __str__(self):
        return "{}".format(self.organisation_name)


# %% Aanlevering models


class gld_registration_log(models.Model):
    id = models.AutoField(primary_key=True)
    date_modified = models.CharField(max_length=254, null=True, blank=True)
    gwm_bro_id = models.CharField(max_length=254, null=True, blank=True)
    gld_bro_id = models.CharField(max_length=254, null=True, blank=True)
    filter_id = models.CharField(max_length=254, null=True, blank=True)
    validation_status = models.CharField(max_length=254, null=True, blank=True)
    levering_id = models.CharField(max_length=254, null=True, blank=True)
    levering_status = models.CharField(max_length=254, null=True, blank=True)
    comments = models.CharField(max_length=10000, null=True, blank=True)
    last_changed = models.CharField(max_length=254, null=True, blank=True)
    corrections_applied = models.BooleanField(blank=True, null=True)
    timestamp_end_registration = models.DateTimeField(blank=True, null=True)
    quality_regime = models.CharField(
        choices=QUALITYREGIME, max_length=254, null=True, blank=True
    )
    file = models.CharField(max_length=254, null=True, blank=True)
    process_status = models.CharField(max_length=254, null=True, blank=True)

    class Meta:
        db_table = 'aanlevering"."gld_registration_log'
        verbose_name = "GLD Registratie Log"
        verbose_name_plural = "GLD Registratie logs"


class gld_addition_log(models.Model):
    date_modified = models.CharField(max_length=254, null=True, blank=True)
    broid_registration = models.CharField(max_length=254, null=True, blank=True)
    observation_id = models.CharField(max_length=254, null=True, blank=True)
    start_date = models.DateTimeField(max_length=254, null=True, blank=True)
    end_date = models.DateTimeField(max_length=254, null=True, blank=True)
    validation_status = models.CharField(max_length=254, null=True, blank=True)
    levering_id = models.CharField(max_length=254, null=True, blank=True)
    levering_type = models.CharField(max_length=254, null=True, blank=True)
    levering_status = models.CharField(max_length=254, null=True, blank=True)
    comments = models.CharField(max_length=50000, null=True, blank=True)
    last_changed = models.CharField(max_length=254, null=True, blank=True)
    corrections_applied = models.BooleanField(blank=True, null=True)
    file = models.CharField(max_length=254, null=True, blank=True)
    addition_type = models.CharField(max_length=254, null=True, blank=True)
    process_status = models.CharField(max_length=254, null=True, blank=True)


    class Meta:
        db_table = 'aanlevering"."gld_addition_log'
        verbose_name = "GLD Toevoeging Log"
        verbose_name_plural = "GLD Toevoeging Logs"
