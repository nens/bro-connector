# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = True` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
import bisect
import datetime
import os
import uuid
from datetime import timedelta
from logging import getLogger
from xml.etree import ElementTree as ET

import bro_exchange as brx
from bro.models import Organisation
from django.apps import apps
from django.db import models
from django.db.models import Manager
from django.utils import timezone
from gmn.models import GroundwaterMonitoringNet
from gmw.models import GroundwaterMonitoringTubeStatic, GroundwaterMonitoringWellStatic
from main.localsecret import DEMO
from main.models import BaseModel

from .choices import (
    AIRPRESSURECOMPENSATIONTYPE,
    CENSORREASON,
    CORRECTION_REASON,
    DELIVERY_TYPE_CHOICES,
    EVALUATIONPROCEDURE,
    MEASUREMENTINSTRUMENTTYPE,
    OBSERVATIONTYPE,
    PROCESSREFERENCE,
    PROCESSTYPE,
    QUALITYREGIME,
    STATUSCODE,
    STATUSQUALITYCONTROL,
    UNIT_CHOICES,
)

logger = getLogger(__file__)

failed_update_strings = ["failed_once", "failed_twice", "failed_thrice"]

app_config = apps.get_app_config("gld")
REGISTRATIONS_DIR = os.path.join(app_config.path, "startregistrations")
ADDITION_DIR = os.path.join(app_config.path, "additions")


# %% GLD Models
def s2d(string: str):
    if len(string) > 9:
        return f"{string[0:3]}...{string[-3:]}"
    return string


def read_observation_id_from_xml(xml_string) -> str:
    # Define the namespaces
    namespaces = {
        "gml": "http://www.opengis.net/gml/3.2",
        "om": "http://www.opengis.net/om/2.0",
    }

    # Parse the XML string
    root = ET.fromstring(xml_string)

    # Find the OM_Observation element and get its gml:id attribute
    observation_elem = root.find(".//om:OM_Observation", namespaces)
    print(observation_elem)
    if observation_elem is not None:
        return observation_elem.attrib.get("{http://www.opengis.net/gml/3.2}id")

    return None


def get_timeseries_tvp_for_observation_id(observation):
    """
    Get all timeseries values between start and stop datetime, including metadata
    """
    measurement_tvp = observation.measurement.all()
    measurements_list = []
    for measurement in measurement_tvp:
        if measurement.measurement_point_metadata:
            metadata = measurement.measurement_point_metadata.get_sourcedocument_data()
        else:
            continue

        # If the measurement value  is None, this value must have been censored
        if measurement.calculated_value is None:
            if metadata.get("censoredReason") is None:
                # We can't include a missing value without a censoring reason
                continue

        measurement_data = {
            "time": measurement.measurement_time.isoformat(),
            "value": float(measurement.calculated_value)
            if measurement.calculated_value
            else None,
            "metadata": metadata,
        }

        measurements_list += [measurement_data]
    measurements_list_ordered = _order_measurements_list(measurements_list)
    return measurements_list_ordered


class GroundwaterLevelDossier(BaseModel):
    groundwater_level_dossier_id = models.AutoField(
        primary_key=True, verbose_name="DB ID"
    )
    groundwater_monitoring_net = models.ManyToManyField(
        GroundwaterMonitoringNet,
        blank=True,
        verbose_name="Meetnet",
    )
    groundwater_monitoring_tube = models.ForeignKey(
        GroundwaterMonitoringTubeStatic,
        on_delete=models.CASCADE,
        null=True,
        blank=False,
        related_name="groundwaterleveldossier",
        verbose_name="Filter",
    )
    gld_bro_id = models.CharField(
        max_length=255, blank=True, null=True, unique=True, verbose_name="GLD BRO ID"
    )
    quality_regime = models.CharField(
        choices=QUALITYREGIME,
        max_length=254,
        null=True,
        blank=True,
        verbose_name="Kwaliteitsregime",
    )
    correction_reason = models.CharField(
        choices=CORRECTION_REASON, null=True, blank=True, verbose_name="Correctie reden"
    )
    research_start_date = models.DateField(
        blank=True, null=True, verbose_name="Onderzoeksstartdatum"
    )
    research_last_date = models.DateField(
        blank=True, null=True, verbose_name="Onderzoekseinddatum"
    )
    research_last_correction = models.DateTimeField(
        blank=True, null=True, verbose_name="Laatste correctie"
    )

    @property
    def gmw_bro_id(self):
        if self.groundwater_monitoring_tube is not None:
            return self.groundwater_monitoring_tube.groundwater_monitoring_well_static.bro_id
        return None

    gmw_bro_id.fget.short_description = "GMW BRO ID"

    @property
    def tube_number(self):
        return self.groundwater_monitoring_tube.tube_number

    tube_number.fget.short_description = "Filternummer"

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

    first_measurement.fget.short_description = "Eerste observatiedatum"

    @property
    def last_measurement(self):
        last_measurement = (
            Observation.objects.filter(groundwater_level_dossier=self)
            .order_by("observation_starttime")
            .last()
        )
        last_measurement_date = getattr(last_measurement, "observation_starttime", None)

        return last_measurement_date

    last_measurement.fget.short_description = "Laatste observatiedatum"

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

    most_recent_measurement.fget.short_description = "Meest recente meetmoment"

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

    completely_delivered.fget.short_description = "Volledig geleverd"

    @property
    def has_open_observation(self):
        nr_of_observations_groundwaterleveldossier = Observation.objects.filter(
            groundwater_level_dossier=self,
            observation_endtime__isnull=True,
        ).count()

        if nr_of_observations_groundwaterleveldossier == 0:
            return False
        return True

    has_open_observation.fget.short_description = "Heeft open observatie(s)"

    @property
    def nr_measurements(self):
        observations = Observation.objects.filter(groundwater_level_dossier=self)
        return MeasurementTvp.objects.filter(
            observation__in=observations,
        ).count()

    nr_measurements.fget.short_description = "Aantal metingen"

    def __str__(self):
        return f"GLD_{self.groundwater_monitoring_tube.__str__()}_{self.quality_regime}"

    class Meta:
        managed = True
        db_table = 'gld"."groundwater_level_dossier'
        verbose_name = "Grondwaterstandonderzoek"
        verbose_name_plural = "Grondwaterstandonderzoeken"
        constraints = [
            models.UniqueConstraint(
                fields=["groundwater_monitoring_tube", "quality_regime"],
                name="unique_tube_quality_regime",
            )
        ]


class Observation(BaseModel):
    observation_id = models.AutoField(
        primary_key=True, null=False, blank=False, verbose_name="DB ID"
    )
    groundwater_level_dossier = models.ForeignKey(
        "GroundwaterLevelDossier",
        on_delete=models.CASCADE,
        related_name="observation",
        verbose_name="Grondwaterstand dossier [GLD]",
    )
    observation_metadata = models.ForeignKey(
        "ObservationMetadata",
        on_delete=models.SET_DEFAULT,
        default=None,
        null=True,
        blank=True,
        verbose_name="Observatie Metadata",
    )
    observation_process = models.ForeignKey(
        "ObservationProcess",
        on_delete=models.SET_DEFAULT,
        default=None,
        null=True,
        blank=True,
        verbose_name="Observatie Proces",
    )
    observation_starttime = models.DateTimeField(
        blank=True, null=True, verbose_name="Starttijd"
    )
    result_time = models.DateTimeField(
        blank=True, null=True, verbose_name="Resultaat tijd"
    )
    observation_endtime = models.DateTimeField(
        blank=True, null=True, verbose_name="Eindtijd"
    )
    up_to_date_in_bro = models.BooleanField(
        default=False, editable=False, verbose_name="Up to date in BRO"
    )

    correction_reason = models.CharField(
        choices=CORRECTION_REASON, null=True, blank=True, verbose_name="Correctie reden"
    )

    observation_id_bro = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        editable=False,
        verbose_name="BRO ID",
    )  # Should also import this with the BRO-Import tool

    measurement: Manager["MeasurementTvp"]

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

    timestamp_first_measurement.fget.short_description = "Moment eerste meting"

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

    timestamp_last_measurement.fget.short_description = "Moment laatste meting"

    @property
    def measurement_type(self):
        if self.observation_process:
            return self.observation_process.measurement_instrument_type
        return "-"

    measurement_type.fget.short_description = "Meting type"

    @property
    def observation_type(self):
        if self.observation_metadata:
            return self.observation_metadata.observation_type
        return "-"

    observation_type.fget.short_description = "Observatie type"

    @property
    def status(self):
        if self.observation_metadata:
            return self.observation_metadata.status
        return "-"

    status.fget.short_description = "Status Metadata"

    @property
    def observationperiod(self):
        if self.observation_starttime and self.observation_endtime:
            return self.observation_endtime - self.observation_starttime
        return None

    observationperiod.fget.short_description = "Observatie periode"

    @property
    def date_stamp(self):
        if self.result_time:
            return self.result_time.date()
        return None

    date_stamp.fget.short_description = "Datum resultaattijd"

    @property
    def all_measurements_validated(self):
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

    all_measurements_validated.fget.short_description = "Alle metingen gevalideerd"

    @property
    def addition_type(self):
        if self.observation_type == "controlemeting":
            return "controlemeting"
        return f"regulier_{self.observation_type}"

    addition_type.fget.short_description = "Toevoegingstype"

    @property
    def active_measurement(self):
        one_week_ago = timezone.now() - timedelta(weeks=1)
        return MeasurementTvp.objects.filter(
            observation=self, measurement_time__gte=one_week_ago
        ).exists()

    active_measurement.fget.short_description = "Actieve meting"

    @property
    def nr_measurements(self):
        return len(MeasurementTvp.objects.filter(observation=self))

    nr_measurements.fget.short_description = "Aantal metingen"

    def __str__(self):
        start = (
            self.observation_starttime.date()
            if self.observation_starttime
            else "Unknown"
        )
        end = self.observation_endtime.date() if self.observation_endtime else "Present"
        return f"{self.groundwater_level_dossier} ({start} - {end})"

    def get_sourcedocument_data(self):
        """
        Generate the GLD addition sourcedocs, without result data
        """
        # Get the GLD registration id for this measurement timeseries
        # Check which parts of the observation have already been succesfully delivered
        # Get the observation metadata and procedure data
        observation_metadata = {
            "observationType": self.observation_type,
            "principalInvestigator": self.observation_metadata.responsible_party.company_number,
        }

        observation_procedure = self.observation_process.get_sourcedocument_data()

        date_stamp = None
        observation_result_time = ""
        if self.result_time:
            observation_result_time = self.result_time.astimezone().strftime(
                "%Y-%m-%dT%H:%M:%S%z"
            )
            date_stamp = self.result_time.astimezone().strftime("%Y-%m-%d")

            if "+" in observation_result_time:
                splited_time = observation_result_time.split("+")
                tz_seporator = "+"
            else:
                splited_time = observation_result_time.split("-")
                tz_seporator = "-"

            timezone = splited_time[-1]
            observation_result_time = (
                f"{splited_time[0]}{tz_seporator}{timezone[0:2]}:{timezone[2:4]}"
            )

        source_document_data = {
            "metadata": {"parameters": observation_metadata, "dateStamp": date_stamp},
            "procedure": {"parameters": observation_procedure},
            "resultTime": observation_result_time,
            "result": get_timeseries_tvp_for_observation_id(self),
        }
        if self.observation_type != "controlemeting":
            source_document_data["metadata"].update(
                {"status": self.observation_metadata.status}
            )

        return source_document_data

    class Meta:
        managed = True
        db_table = 'gld"."observation'
        verbose_name = "Observatie"
        verbose_name_plural = "Observaties"


class ObservationMetadata(BaseModel):
    observation_metadata_id = models.AutoField(primary_key=True, verbose_name="DB ID")
    observation_type = models.CharField(
        choices=OBSERVATIONTYPE,
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Observatie type",
    )
    status = models.CharField(
        choices=STATUSCODE,
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Mate beoordeling",
    )
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
    observation_process_id = models.AutoField(primary_key=True, verbose_name="DB ID")
    process_reference = models.CharField(
        choices=PROCESSREFERENCE,
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Proces referentie",
    )
    measurement_instrument_type = models.CharField(
        choices=MEASUREMENTINSTRUMENTTYPE,
        max_length=200,
        blank=False,
        null=False,
        verbose_name="Meetinstrument type",
    )
    air_pressure_compensation_type = models.CharField(
        choices=AIRPRESSURECOMPENSATIONTYPE,
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Luchtdrukcompensatie type",
    )
    process_type = models.CharField(
        choices=PROCESSTYPE,
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Proces type",
    )
    evaluation_procedure = models.CharField(
        choices=EVALUATIONPROCEDURE,
        max_length=200,
        blank=False,
        null=False,
        verbose_name="Evaluatie procedure",
    )

    def __str__(self):
        try:
            if not self.air_pressure_compensation_type:
                return f"{self.evaluation_procedure} {self.measurement_instrument_type}"
            return f"{s2d(self.evaluation_procedure)} {s2d(self.measurement_instrument_type)} {s2d(self.process_reference)}"
        except Exception as e:
            logger.exception(e)
            return str(self.observation_process_id)

    def get_sourcedocument_data(self):
        """
        Get the procedure data for the observation
        This is unique for each observation
        """
        observation_procedure_data = {
            "airPressureCompensationType": self.air_pressure_compensation_type,
            "evaluationProcedure": self.evaluation_procedure,
            "measurementInstrumentType": self.measurement_instrument_type,
        }

        if self.measurement_instrument_type in [
            "analoogPeilklokje",
            "elektronischPeilklokje",
            "onbekendPeilklokje",
            "onbekend",
            None,
        ]:
            observation_procedure_data.pop("airPressureCompensationType")

        return observation_procedure_data

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
    measurement_tvp_id = models.AutoField(primary_key=True, verbose_name="DB ID")
    observation = models.ForeignKey(
        Observation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Observatie",
        related_name="measurement",
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
    initial_calculated_value = models.DecimalField(
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
        on_delete=models.SET_NULL,
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
        indexes = [
            models.Index(fields=["observation", "-measurement_time"]),
        ]
        ## IMPORTANT: Temporarily turned off the unique constraint of mtvps due to complications with Zeeland DB.
        # constraints = [
        #     models.UniqueConstraint(
        #         fields=["observation", "measurement_time"],  # composite uniqueness
        #         name="unique_observation_measurement_time"
        #     )
        # ]

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
        verbose_name="Status kwaliteitscontrole",
    )
    censor_reason = models.CharField(
        choices=CENSORREASON,
        max_length=200,
        blank=True,
        null=True,
        default=None,
        verbose_name="Censuurreden",
    )
    status_quality_control_reason_datalens = models.CharField(
        max_length=200, blank=True, null=True, verbose_name="Status kwaliteitscontrole reden Datalens"
    )
    value_limit = models.CharField(
        max_length=50, blank=True, null=True, default=None, verbose_name="Limietwaarde"
    )

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

    interpolation_code.fget.short_description = "Interpolatie code"

    def __str__(self):
        return f"{self.measurement_point_metadata_id} {self.status_quality_control}"

    def get_sourcedocument_data(
        self,
    ):
        metadata = {
            "StatusQualityControl": self.status_quality_control,
            "interpolationType": "Discontinuous",
        }
        if self.censor_reason not in ["", "nan", None]:
            metadata["censoredReason"] = self.censor_reason

        return metadata


# %% Aanlevering models


class gld_registration_log(BaseModel):
    # gld = models.ForeignKey()
    gmw_bro_id = models.CharField(max_length=254, verbose_name="GMW ID")
    gld_bro_id = models.CharField(
        max_length=254, verbose_name="GLD ID", null=True, blank=True
    )
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
    corrections_applied = models.BooleanField(
        blank=True, null=True, verbose_name="Correcties toegepast"
    )
    timestamp_end_registration = models.DateTimeField(
        blank=True, null=True, verbose_name="Moment einde registratie"
    )
    quality_regime = models.CharField(
        choices=QUALITYREGIME,
        max_length=254,
        null=True,
        blank=True,
        verbose_name="Kwaliteitsregime",
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
                fields=["gmw_bro_id", "filter_number", "quality_regime"],
                name="unique_gld_registration_log",
            )
        ]

    @property
    def groundwaterleveldossier(self) -> GroundwaterLevelDossier | None:
        groundwater_monitoring_well = GroundwaterMonitoringWellStatic.objects.get(
            bro_id=self.gmw_bro_id
        )
        tube = groundwater_monitoring_well.tube.get(tube_number=self.filter_number)
        try:
            return GroundwaterLevelDossier.objects.get(
                groundwater_monitoring_tube=tube,
                quality_regime=self.quality_regime,
            )
        except GroundwaterLevelDossier.MultipleObjectsReturned:
            return None
        except GroundwaterLevelDossier.DoesNotExist:
            return None

    def save(self, *args, **kwargs):
        if self.pk is not None:
            db = gld_registration_log.objects.get(id=self.id)
            if (
                self.delivery_status == "OPGENOMEN_LVBRO"
                and db.delivery_status != "OPGENOMEN_LVBRO"
            ):
                gld = self.groundwaterleveldossier
                gld.correction_reason = None
                gld.save(update_fields=["correction_reason"])

        super().save(*args, **kwargs)

    def generate_sourcedocument(
        self,
    ) -> str:
        if self.gmw_bro_id is None or self.filter_number is None:
            self.comments = "No GMW ID or filter number provided"
            self.save()
            return

        dossier = self.groundwaterleveldossier

        bro_id_gmw = dossier.gmw_bro_id
        internal_id = dossier.groundwater_monitoring_tube.__str__()
        quality_regime = dossier.quality_regime
        delivery_accountable_party = (
            "27376655"
            if DEMO
            else dossier.groundwater_monitoring_tube.groundwater_monitoring_well_static.delivery_accountable_party.company_number
        )
        monitoringpoints = [{"broId": bro_id_gmw, "tubeNumber": dossier.tube_number}]

        if dossier.groundwater_monitoring_net.count() == 0:
            srcdocdata = {
                "objectIdAccountableParty": f"{internal_id}-{dossier.quality_regime}",
                "monitoringPoints": monitoringpoints,
            }
        else:
            gmn_ids = [
                {"broId": item}
                for item in dossier.groundwater_monitoring_net.all().values_list(
                    "gmn_bro_id", flat=True
                )
            ]
            srcdocdata = {
                "objectIdAccountableParty": f"{internal_id}-{dossier.quality_regime}",
                "groundwaterMonitoringNets": gmn_ids,
                "monitoringPoints": monitoringpoints,
            }

        request_reference = f"GLD_StartRegistration_{bro_id_gmw}_tube_{str(dossier.tube_number)}{'-replace' if self.delivery_type == 'replace' else ''}"
        if self.delivery_type == "register":
            gld_startregistration_request = brx.gld_registration_request(
                srcdoc="GLD_StartRegistration",
                requestReference=request_reference,
                deliveryAccountableParty=delivery_accountable_party,
                qualityRegime=quality_regime,
                srcdocdata=srcdocdata,
            )
        else:
            correction_reason = self.groundwaterleveldossier.correction_reason
            gld_startregistration_request = brx.gld_replace_request(
                srcdoc="GLD_StartRegistration",
                broId=self.gld_bro_id,
                correctionReason=correction_reason,
                requestReference=request_reference,
                deliveryAccountableParty=delivery_accountable_party,
                qualityRegime=quality_regime,
                srcdocdata=srcdocdata,
            )

        filename = request_reference + ".xml"
        gld_startregistration_request.generate()
        gld_startregistration_request.write_request(
            output_dir=REGISTRATIONS_DIR, filename=filename
        )
        process_status = "succesfully_generated_startregistration_request"
        self.comments = ("Succesfully generated startregistration request",)
        self.date_modified = datetime.datetime.now()
        self.validation_status = None
        self.process_status = process_status
        self.file = filename

        self.save()

        return process_status

    def validate_sourcedocument(
        self,
    ) -> str:
        """
        Validate the generated GLD sourcedoc
        """
        if not self.file:
            self.comments = "No file to validate"
            self.save()
            return

        gmw = GroundwaterMonitoringWellStatic.objects.get(bro_id=self.gmw_bro_id)
        source_doc_file = os.path.join(REGISTRATIONS_DIR, self.file)
        payload = open(source_doc_file)
        try:
            validation_info = brx.validate_sourcedoc(
                payload, bro_info=gmw.get_bro_info(), demo=DEMO
            )
            validation_status = validation_info["status"]
            if validation_status != "VALIDE":
                logger.info(validation_info)

            if "errors" in validation_info:
                comments = f"Validated sourcedocument, found errors: {validation_info['errors']}"
                self.process_status = "source_document_validation_failed"

            else:
                comments = "Succesfully validated sourcedocument, no errors"

            self.date_modified = datetime.datetime.now()
            self.comments = comments[0:20000]
            self.validation_status = validation_status
            self.process_status = "source_document_validation_succeeded"

        except Exception as e:
            self.date_modified = datetime.datetime.now()
            self.comments = f"Failed to validate source document: {e}"
            self.process_status = "source_document_validation_failed"

        self.save()
        return validation_status

    def deliver_sourcedocument(
        self,
    ) -> str:
        """
        Deliver the generated GLD sourcedoc
        """
        if not self.file:
            self.comments = "No file to deliver"
            self.save()
            return

        # If the delivery fails, use the this to indicate how many attempts were made
        delivery_status = self.delivery_status
        if delivery_status is None:
            delivery_status_update = "failed_once"
        else:
            position = bisect.bisect_left(failed_update_strings, delivery_status)
            delivery_status_update = failed_update_strings[position + 1]

        gmw = GroundwaterMonitoringWellStatic.objects.get(bro_id=self.gmw_bro_id)
        bro_info = gmw.get_bro_info()
        file = self.file
        source_doc_file = os.path.join(REGISTRATIONS_DIR, file)
        payload = open(source_doc_file)
        try:
            request = {file: payload}
            upload_info = brx.upload_sourcedocs_from_dict(
                request,
                token=bro_info["token"],
                project_id=bro_info["projectnummer"],
                demo=DEMO,
            )
            if upload_info == "Error":
                comments = "Error occurred during delivery of sourcedocument"
                self.date_modified = datetime.datetime.now()
                self.comments = comments
                self.delivery_status = delivery_status_update
                self.process_status = "failed_to_deliver_sourcedocuments"
            else:
                upload_data = upload_info.json()
                self.date_modified = datetime.datetime.now()
                self.comments = "Successfully delivered startself sourcedocument"
                self.delivery_status = upload_data["status"]
                self.last_changed = upload_data["lastChanged"]
                self.delivery_id = upload_data["identifier"]
                self.process_status = "succesfully_delivered_sourcedocuments"

        except Exception as e:
            comments = (
                f"Exception occured during delivery of startself sourcedocument: {e}"
            )
            self.date_modified = datetime.datetime.now()
            self.comments = comments
            self.delivery_status = delivery_status_update
            self.process_status = "failed_to_deliver_sourcedocuments"

        self.save()
        return delivery_status

    def check_delivery_status(
        self,
    ) -> str:
        """
        Check the delivery status of the generated GLD sourcedoc
        """
        if not self.delivery_id:
            return

        gmw = GroundwaterMonitoringWellStatic.objects.get(bro_id=self.gmw_bro_id)
        bro_info = gmw.get_bro_info()

        try:
            delivery_info = brx.check_delivery_status(
                self.delivery_id,
                token=bro_info["token"],
                demo=DEMO,
                project_id=bro_info["projectnummer"],
            )
            delivery_status = delivery_info.json()["status"]
            self.date_modified = datetime.datetime.now()
            self.comments = f"Delivery status: {delivery_status}"
            self.delivery_status = delivery_status
            self.last_changed = delivery_info.json()["lastChanged"]
            self.process_status = "delivery_status_checked"

            if (
                self.delivery_status == "OPGENOMEN_LVBRO"
                and self.delivery_type == "replace"
            ):
                gld = self.groundwaterleveldossier
                gld.correction_reason = None
                gld.save(update_fields=["correction_reason"])

        except Exception as e:
            logger.info(f"Failed to check delivery status: {e}")
            delivery_status = "failed_to_deliver"
            comments = f"Failed to check delivery status: {e}"
            self.date_modified = datetime.datetime.now()
            self.comments = comments
            self.process_status = "failed_to_check_delivery_status"

        self.save()
        return delivery_status


class gld_addition_log(BaseModel):
    broid_registration = models.CharField(max_length=254, verbose_name="GLD ID")
    observation = models.ForeignKey(
        Observation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Observatie reeks",
    )
    addition_type = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Reeks type"
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
    process_status = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="Proces status"
    )

    class Meta:
        db_table = 'aanlevering"."gld_addition_log'
        verbose_name = "GLD Toevoeging Log"
        verbose_name_plural = "GLD Toevoeging Logs"

    def generate_sourcedocument(
        self,
    ) -> str:
        observation_source_document_data = self.observation.get_sourcedocument_data()
        print(observation_source_document_data)
        if len(observation_source_document_data["result"]) < 1:
            logger.warning("No results in observation")
            self.date_modified = datetime.datetime.now()
            self.comments = "No results in observation"
            self.process_status = "failed_to_create_source_document"
            self.save()
            return

        first_timestamp_datetime = self.observation.timestamp_first_measurement
        final_timestamp_datetime = self.observation.timestamp_last_measurement

        # Add the timeseries to the sourcedocument
        gld_addition_sourcedocument = observation_source_document_data
        gld_addition_sourcedocument["observationId"] = f"_{uuid.uuid4()}"

        # filename should be unique
        filename = f"GLD_Addition_Observation_{self.observation.observation_id}_{self.observation.groundwater_level_dossier.gld_bro_id}.xml"
        # try to create source document
        try:
            # Create addition source document
            gld_addition_registration_request = brx.gld_registration_request(
                srcdoc="GLD_Addition",
                requestReference=filename,
                deliveryAccountableParty=self.observation.observation_metadata.responsible_party.company_number,  # investigator_identification (NENS voor TEST)
                qualityRegime=self.observation.groundwater_level_dossier.quality_regime,
                broId=self.observation.groundwater_level_dossier.gld_bro_id,
                srcdocdata=gld_addition_sourcedocument,
            )
            gld_addition_registration_request.generate()
            gld_addition_registration_request.write_request(
                output_dir=ADDITION_DIR, filename=filename
            )

            observation_id = read_observation_id_from_xml(
                gld_addition_registration_request.request
            )

            # Set or update the record fields
            self.observation_identifier = observation_id
            self.date_modified = datetime.datetime.now()
            self.start_date = first_timestamp_datetime
            self.end_date = final_timestamp_datetime
            self.comments = "Successfully generated XML sourcedocument"
            self.file = filename
            self.validation_status = "TO_BE_VALIDATED"
            self.addition_type = self.observation.addition_type
            self.process_status = "source_document_created"

        except Exception as e:
            print(e)
            self.date_modified = datetime.datetime.now()
            self.comments = f"Failed to generate XML source document, {e}"
            self.process_status = "failed_to_create_source_document"

        self.save()

    def validate_sourcedocument(
        self,
    ) -> str:
        """
        Validate the generated GLD sourcedoc
        """
        if not self.file:
            self.comments = "No file to validate"
            self.save()
            return

        gmw: GroundwaterMonitoringWellStatic = self.observation.groundwater_level_dossier.groundwater_monitoring_tube.groundwater_monitoring_well_static
        source_doc_file = os.path.join(ADDITION_DIR, self.file)
        payload = open(source_doc_file)
        try:
            validation_info = brx.validate_sourcedoc(
                payload,
                bro_info=gmw.get_bro_info(),
                demo=DEMO,
            )
            validation_status = validation_info["status"]

            if "errors" in validation_info:
                comments = f"Validated sourcedocument, found errors: {validation_info['errors']}"
                self.process_status = "source_document_validation_failed"

            else:
                comments = "Succesfully validated sourcedocument, no errors"

            self.date_modified = datetime.datetime.now()
            self.comments = comments[0:20000]
            self.validation_status = validation_status
            self.process_status = "source_document_validation_succeeded"

        except Exception as e:
            self.date_modified = datetime.datetime.now()
            self.comments = f"Failed to validate source document: {e}"
            self.process_status = "source_document_validation_failed"

        self.save()
        return validation_status

    def deliver_sourcedocument(
        self,
    ) -> str:
        """
        Deliver the generated GLD sourcedoc
        """
        if not self.file:
            return

        # If the delivery fails, use the this to indicate how many attempts were made
        delivery_status = self.delivery_status
        if delivery_status is None:
            delivery_status_update = "failed_once"
        else:
            position = bisect.bisect_left(failed_update_strings, delivery_status)
            delivery_status_update = failed_update_strings[position + 1]

        gmw: GroundwaterMonitoringWellStatic = self.observation.groundwater_level_dossier.groundwater_monitoring_tube.groundwater_monitoring_well_static
        bro_info = gmw.get_bro_info()
        file = self.file
        source_doc_file = os.path.join(ADDITION_DIR, file)
        payload = open(source_doc_file)
        try:
            request = {file: payload}
            upload_info = brx.upload_sourcedocs_from_dict(
                request,
                token=bro_info["token"],
                project_id=bro_info["projectnummer"],
                demo=DEMO,
            )
            if upload_info == "Error":
                comments = "Error occured during delivery of sourcedocument"

                self.date_modified = datetime.datetime.now()
                self.comments = comments
                self.delivery_status = delivery_status_update

            else:
                self.date_modified = datetime.datetime.now()
                self.comments = "Succesfully delivered sourcedocument"
                self.delivery_status = upload_info.json()["status"]
                self.last_changed = upload_info.json()["lastChanged"]
                self.delivery_id = upload_info.json()["identifier"]
                self.process_status = "source_document_delivered"

        except Exception as e:
            comments = f"Error occured in attempting to deliver sourcedocument, {e}"

            self.date_modified = datetime.datetime.now()
            self.comments = comments
            self.delivery_status = delivery_status_update

        self.save()
        return delivery_status

    def check_delivery_status(
        self,
    ) -> str:
        """
        Check the delivery status of the generated GLD sourcedoc
        """
        if not self.delivery_id:
            return

        gmw: GroundwaterMonitoringWellStatic = self.observation.groundwater_level_dossier.groundwater_monitoring_tube.groundwater_monitoring_well_static
        bro_info = gmw.get_bro_info()

        try:
            delivery_info = brx.check_delivery_status(
                identifier=self.delivery_id,
                token=bro_info["token"],
                project_id=bro_info["projectnummer"],
                demo=DEMO,
            )
            delivery_status = delivery_info.json()["status"]
            self.date_modified = datetime.datetime.now()
            self.comments = f"Delivery status: {delivery_status}"
            self.delivery_status = delivery_status
            self.last_changed = delivery_info.json()["lastChanged"]
            self.process_status = "delivery_status_checked"

        except Exception as e:
            delivery_status = "Failed"
            comments = f"Failed to check delivery status: {e}"
            self.date_modified = datetime.datetime.now()
            self.comments = comments
            self.process_status = "failed_to_check_delivery_status"

        self.save()
        return delivery_status


### Helper functions
def _order_measurements_list(measurement_list: list):
    datetime_values = [
        datetime.datetime.fromisoformat(tvp["time"]) for tvp in measurement_list
    ]
    datetime_ordered = sorted(datetime_values)
    indices = [
        datetime_values.index(datetime_value) for datetime_value in datetime_ordered
    ]

    measurement_list_ordered = []
    for index in indices:
        measurement_list_ordered.append(measurement_list[index])

    # print(measurement_list_ordered)
    return measurement_list_ordered
