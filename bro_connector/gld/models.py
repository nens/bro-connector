# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = True` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models
from logging import getLogger
from .choices import (
    QUALITYREGIME,
    AIRPRESSURECOMPENSATIONTYPE,
    CENSORREASON,
    UNIT_CHOICES,
    DELIVERY_TYPE_CHOICES,
    EVALUATIONPROCEDURE,
    MEASUREMENTINSTRUMENTTYPE,
    OBSERVATIONTYPE,
    PROCESSREFERENCE,
    PROCESSTYPE,
    STATUSCODE,
    STATUSQUALITYCONTROL,
)
from bro.models import Organisation
from gmw.models import GroundwaterMonitoringTubeStatic
from gmn.models import GroundwaterMonitoringNet
from main.models import BaseModel

logger = getLogger(__file__)


# %% GLD Models
def s2d(string: str):
    if len(string) > 9:
        return f"{string[0:3]}...{string[-3:]}"
    return string


class GroundwaterLevelDossier(BaseModel):
    groundwater_level_dossier_id = models.AutoField(primary_key=True)
    groundwater_monitoring_net = models.ManyToManyField(
        GroundwaterMonitoringNet,
        blank=True,
        verbose_name="Meetnetten",
    )
    groundwater_monitoring_tube = models.ForeignKey(
        GroundwaterMonitoringTubeStatic,
        on_delete=models.CASCADE,
        null=True,
        blank=False,
        related_name="groundwaterleveldossier",
    )
    gld_bro_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    quality_regime = models.CharField(
        choices=QUALITYREGIME, max_length=254, null=True, blank=True
    )
    research_start_date = models.DateField(blank=True, null=True)
    research_last_date = models.DateField(blank=True, null=True)
    research_last_correction = models.DateTimeField(blank=True, null=True)

    @property
    def gmw_bro_id(self):
        if self.groundwater_monitoring_tube is not None:
            return self.groundwater_monitoring_tube.groundwater_monitoring_well_static.bro_id
        return None

    @property
    def tube_number(self):
        return self.groundwater_monitoring_tube.tube_number

    @property
    def first_measurement(self):
        first_measurement = (
            Observation.objects.filter(groundwater_level_dossier=self)
            .order_by("observation_starttime")
            .first()
        )
        first_measurement_date = getattr(
            first_measurement, "observation_starttime", None
        )

        return first_measurement_date

    @property
    def most_recent_measurement(self):
        observations_groundwaterleveldossier = Observation.objects.filter(
            groundwater_level_dossier=self
        ).order_by("-observation_starttime")
        for observation_groundwaterleveldossier in observations_groundwaterleveldossier:
            # last_measurementTVP
            most_recent_measurement = (
                MeasurementTvp.objects.filter(
                    observation_id=observation_groundwaterleveldossier.observation_id
                )
                .order_by("-measurement_time")
                .first()
            )

            if most_recent_measurement is not None:
                return most_recent_measurement.measurement_time

        return None

    @property
    def completely_delivered(self):
        nr_of_observations_groundwaterleveldossier = Observation.objects.filter(
            groundwater_level_dossier=self,
            up_to_date_in_bro=False,
            observation_endtime__isnull=False,
        ).count()

        if nr_of_observations_groundwaterleveldossier == 0:
            return True
        return False

    @property
    def has_open_observation(self):
        nr_of_observations_groundwaterleveldossier = Observation.objects.filter(
            groundwater_level_dossier=self,
            observation_endtime__isnull=True,
        ).count()

        if nr_of_observations_groundwaterleveldossier == 0:
            return False
        return True

    def __str__(self):
        return f"GLD_{self.groundwater_monitoring_tube.__str__()}"

    class Meta:
        managed = True
        db_table = 'gld"."groundwater_level_dossier'
        verbose_name = "Grondwaterstand Dossier"
        verbose_name_plural = "Grondwaterstand Dossiers"


class Observation(BaseModel):
    observation_id = models.AutoField(primary_key=True, null=False, blank=False)
    groundwater_level_dossier = models.ForeignKey(
        "GroundwaterLevelDossier", on_delete=models.CASCADE
    )
    observation_metadata = models.ForeignKey(
        "ObservationMetadata",
        on_delete=models.SET_DEFAULT,
        default=None,
        null=True,
        blank=True,
    )
    observation_process = models.ForeignKey(
        "ObservationProcess",
        on_delete=models.SET_DEFAULT,
        default=None,
        null=True,
        blank=True,
    )
    observation_starttime = models.DateTimeField(blank=True, null=True)
    result_time = models.DateTimeField(blank=True, null=True)
    observation_endtime = models.DateTimeField(blank=True, null=True)
    up_to_date_in_bro = models.BooleanField(default=False, editable=False)

    observation_id_bro = models.CharField(
        max_length=200, blank=True, null=True, editable=False
    )  # Should also import this with the BRO-Import tool

    @property
    def timestamp_first_measurement(self):
        mtvp = (
            MeasurementTvp.objects.filter(observation=self)
            .order_by("measurement_time")
            .first()
        )

        if mtvp is not None:
            return mtvp.measurement_time
        return None

    @property
    def timestamp_last_measurement(self):
        mtvp = (
            MeasurementTvp.objects.filter(observation=self)
            .order_by("measurement_time")
            .last()
        )

        if mtvp is not None:
            return mtvp.measurement_time
        return None

    @property
    def measurement_type(self):
        if self.observation_process:
            return self.observation_process.measurement_instrument_type
        return "-"

    @property
    def observation_type(self):
        if self.observation_metadata:
            return self.observation_metadata.observation_type
        return "-"

    @property
    def status(self):
        if self.observation_metadata:
            return self.observation_metadata.status
        return "-"

    @property
    def observationperiod(self):
        if self.observation_starttime and self.observation_endtime:
            return self.observation_endtime - self.observation_starttime
        return None

    @property
    def date_stamp(self):
        if self.result_time:
            return self.result_time.date()
        return None

    @property
    def validation_status(self):
        nr_of_unvalidated = len(
            MeasurementTvp.objects.filter(
                observation=self,
                measurement_point_metadata__status_quality_control__in=[
                    "nogNietBeoordeeld",
                    "onbekend",
                ],
            )
        )
        if nr_of_unvalidated > 0:
            return "voorlopig"
        elif nr_of_unvalidated == 0:
            return "volledigBeoordeeld"
        else:
            return "onbekend"

    def __str__(self):
        start = (
            self.observation_starttime.date()
            if self.observation_starttime
            else "Unknown"
        )
        end = self.observation_endtime.date() if self.observation_endtime else "Present"
        return f"{self.groundwater_level_dossier} ({start} - {end})"

    class Meta:
        managed = True
        db_table = 'gld"."observation'
        verbose_name = "Observatie"
        verbose_name_plural = "Observaties"


class ObservationMetadata(BaseModel):
    observation_metadata_id = models.AutoField(primary_key=True)
    observation_type = models.CharField(
        choices=OBSERVATIONTYPE, max_length=200, blank=True, null=True
    )
    status = models.CharField(choices=STATUSCODE, max_length=200, blank=True, null=True)
    responsible_party = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Organisatie",
    )

    def __str__(self):
        if self.responsible_party:
            return f"{self.responsible_party.name} {str(self.status)}"
        else:
            return f"{str(self.status)}"

    class Meta:
        managed = True
        db_table = 'gld"."observation_metadata'
        verbose_name = "Observatie Metadata"
        verbose_name_plural = "Observatie Metadata"
        constraints = [
            models.UniqueConstraint(
                fields=["observation_type", "status", "responsible_party"],
                name="unique_metadata",
            )
        ]


class ObservationProcess(BaseModel):
    observation_process_id = models.AutoField(primary_key=True)
    process_reference = models.CharField(
        choices=PROCESSREFERENCE, max_length=200, blank=True, null=True
    )
    measurement_instrument_type = models.CharField(
        choices=MEASUREMENTINSTRUMENTTYPE, max_length=200, blank=False, null=False
    )
    air_pressure_compensation_type = models.CharField(
        choices=AIRPRESSURECOMPENSATIONTYPE, max_length=200, blank=True, null=True
    )
    process_type = models.CharField(
        choices=PROCESSTYPE, max_length=200, blank=True, null=True
    )
    evaluation_procedure = models.CharField(
        choices=EVALUATIONPROCEDURE, max_length=200, blank=False, null=False
    )

    def __str__(self):
        try:
            if not self.air_pressure_compensation_type:
                return f"{self.evaluation_procedure} {self.measurement_instrument_type}"
            return f"{s2d(self.evaluation_procedure)} {s2d(self.measurement_instrument_type)} {s2d(self.process_reference)}"
        except Exception as e:
            logger.exception(e)
            return str(self.observation_process_id)

    class Meta:
        managed = True
        db_table = 'gld"."observation_process'
        verbose_name = "Observatie Proces"
        verbose_name_plural = "Observatie Proces"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "process_reference",
                    "measurement_instrument_type",
                    "air_pressure_compensation_type",
                    "process_type",
                    "evaluation_procedure",
                ],
                name="unique_observation_process",
            )
        ]


# MEASUREMENT TIME VALUE PAIR
class MeasurementTvp(BaseModel):
    measurement_tvp_id = models.AutoField(primary_key=True)
    observation = models.ForeignKey(
        Observation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Observatie",
    )
    measurement_time = models.DateTimeField(
        blank=True, null=True, verbose_name="Tijd meting"
    )
    field_value = models.DecimalField(
        max_digits=25,
        decimal_places=3,
        blank=True,
        null=True,
        verbose_name="Veldmeting",
    )
    field_value_unit = models.CharField(
        choices=UNIT_CHOICES,
        max_length=255,
        blank=False,
        null=False,
        default="m",
        verbose_name="Veld eenheid",
    )
    calculated_value = models.DecimalField(
        max_digits=25,
        decimal_places=5,
        blank=True,
        null=True,
        verbose_name="Berekende waarde",
    )
    value_to_be_corrected = models.DecimalField(
        max_digits=25,
        decimal_places=5,
        blank=True,
        null=True,
        verbose_name="Te corrigeren waarde",
    )
    correction_time = models.DateTimeField(
        blank=True, null=True, verbose_name="Correctie tijd"
    )
    correction_reason = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Correctie reden"
    )
    measurement_point_metadata = models.ForeignKey(
        "MeasurementPointMetadata",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Meting metadata",
    )
    comment = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Commentaar"
    )

    class Meta:
        managed = True
        db_table = 'gld"."measurement_tvp'
        verbose_name = "Metingen Tijd-Waarde Paren"
        verbose_name_plural = "Metingen Tijd-Waarde Paren"

    def __str__(self) -> str:
        return f"{self.observation} {self.measurement_time} {self.calculated_value}"


class MeasurementPointMetadata(BaseModel):
    measurement_point_metadata_id = models.AutoField(primary_key=True)
    status_quality_control = models.CharField(
        choices=STATUSQUALITYCONTROL,
        max_length=200,
        blank=True,
        null=True,
        default="nogNietBeoordeeld",
    )
    censor_reason = models.CharField(
        choices=CENSORREASON, max_length=200, blank=True, null=True, default=None
    )
    censor_reason_datalens = models.CharField(max_length=200, blank=True, null=True)
    value_limit = models.CharField(max_length=50, blank=True, null=True, default=None)

    class Meta:
        managed = True
        app_label = "gld"
        db_table = 'gld"."measurement_point_metadata'
        verbose_name = "Meetpunt Metadata"
        verbose_name_plural = "Meetpunt Metadata"
        indexes = [
            models.Index(fields=["status_quality_control"]),
            models.Index(fields=["censor_reason"]),
        ]

    @property
    def interpolation_code(self):
        return "discontinu"

    def __str__(self):
        return f"{self.measurement_point_metadata_id} {self.status_quality_control}"


# %% Aanlevering models


class gld_registration_log(BaseModel):
    # gld = models.ForeignKey()
    gwm_bro_id = models.CharField(max_length=254, verbose_name="GMW ID")
    gld_bro_id = models.CharField(max_length=254, verbose_name="GLD ID")
    filter_number = models.CharField(max_length=254, verbose_name="Filternummer")
    validation_status = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Validatiestatus"
    )
    delivery_id = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Leverings ID"
    )
    delivery_type = models.CharField(
        choices=DELIVERY_TYPE_CHOICES,
        blank=False,
        max_length=40,
        default="register",
        verbose_name="Leverings type",
    )
    delivery_status = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Leverings status"
    )
    comments = models.CharField(
        max_length=50000, null=True, blank=True, verbose_name="Commentaar"
    )
    last_changed = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Laatste wijziging"
    )
    corrections_applied = models.BooleanField(blank=True, null=True)
    timestamp_end_registration = models.DateTimeField(blank=True, null=True)
    quality_regime = models.CharField(
        choices=QUALITYREGIME, max_length=254, null=True, blank=True
    )
    file = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Bestand"
    )
    process_status = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Proces status"
    )

    class Meta:
        db_table = 'aanlevering"."gld_registration_log'
        verbose_name = "GLD Registratie Log"
        verbose_name_plural = "GLD Registratie Logs"
        constraints = [
            models.UniqueConstraint(
                fields=["gwm_bro_id", "filter_number", "quality_regime"],
                name="unique_gld_registration_log",
            )
        ]


class gld_addition_log(BaseModel):
    broid_registration = models.CharField(max_length=254, verbose_name="GLD ID")
    observation = models.ForeignKey(
        Observation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Observatie reeks",
    )
    observation_identifier = models.CharField(
        max_length=254, verbose_name="Observatie ID"
    )
    start_date = models.DateTimeField(
        max_length=254, null=True, blank=True, verbose_name="Startdatum"
    )
    end_date = models.DateTimeField(
        max_length=254, null=True, blank=True, verbose_name="Einddatum"
    )
    validation_status = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Validatiestatus"
    )
    delivery_id = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Leverings ID"
    )
    delivery_type = models.CharField(
        choices=DELIVERY_TYPE_CHOICES,
        blank=False,
        max_length=40,
        default="register",
        verbose_name="Leverings type",
    )
    delivery_status = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Leverings status"
    )
    comments = models.CharField(
        max_length=50000, null=True, blank=True, verbose_name="Commentaar"
    )
    last_changed = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Laatste wijziging"
    )
    corrections_applied = models.BooleanField(
        blank=True, null=True, verbose_name="Correcties toegepast"
    )
    file = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Bestand"
    )
    addition_type = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Toevoeging type"
    )
    process_status = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Proces status"
    )

    class Meta:
        db_table = 'aanlevering"."gld_addition_log'
        verbose_name = "GLD Toevoeging Log"
        verbose_name_plural = "GLD Toevoeging Logs"
