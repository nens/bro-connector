from django.db import models
import datetime
from tools.choices import BRO_TYPES
from gld.choices import (
    OBSERVATIONTYPE,
    UNIT_CHOICES,
    STATUSCODE,
    AIRPRESSURECOMPENSATIONTYPE,
    PROCESSREFERENCE,
    MEASUREMENTINSTRUMENTTYPE,
    PROCESSTYPE,
    EVALUATIONPROCEDURE,
)
from bro.models import Organisation
from django.core.exceptions import ValidationError
from gmw.models import GroundwaterMonitoringTubeStatic
from gmn.choices import KADER_AANLEVERING_GMN, MONITORINGDOEL


class BroImporter(models.Model):
    bro_type = models.CharField(
        max_length=100,
        choices=BRO_TYPES,
        null=False,
    )
    kvk_number = models.CharField(max_length=8, null=False)
    import_date = models.DateTimeField(editable=False)
    created_date = models.DateTimeField(editable=False)

    class Meta:
        managed = True
        db_table = 'tools"."bro_importer'
        verbose_name = "Importer"
        verbose_name_plural = "BRO Importer"

    def save(self, *args, **kwargs):
        if not self.pk:
            self.import_date = datetime.datetime.now()
            self.created_date = datetime.datetime.now()

        super().save(self, *args, **kwargs)


class XMLImport(models.Model):
    id = models.AutoField(primary_key=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    file = models.FileField(upload_to="bulk", validators=[])
    report = models.TextField(
        help_text="process description",
        blank=True,
        null=True,
    )
    checked = models.BooleanField(
        help_text="checked",
        editable=False,
        default=False,
        blank=True,
        null=True,
    )
    imported = models.BooleanField(
        verbose_name="fully imported",
        default=False,
        editable=False,
        blank=True,
        null=True,
    )

    class Meta:
        managed = True
        db_table = 'tools"."xml_importer'
        verbose_name = "XML Import"
        verbose_name_plural = "XML Imports"


class GLDImport(models.Model):
    file = models.FileField(
        upload_to="bulk", help_text="csv. or zip.", validators=[], null=True, blank=True
    )
    name = models.CharField(max_length=255, null=True, blank=False, verbose_name="Naam")
    groundwater_monitoring_tube = models.ForeignKey(
        GroundwaterMonitoringTubeStatic,
        on_delete=models.CASCADE,
        null=True,
        blank=False,
    )
    responsible_party = models.ForeignKey(
        Organisation, on_delete=models.SET_NULL, null=True, blank=True
    )
    observation_type = models.CharField(
        choices=OBSERVATIONTYPE, max_length=200, blank=False, null=False
    )
    field_value_unit = models.CharField(
        choices=UNIT_CHOICES,
        max_length=255,
        blank=False,
        null=False,
        default="m",
        verbose_name="Veld eenheid",
    )

    status = models.CharField(
        choices=STATUSCODE, max_length=200, blank=False, null=False
    )

    process_reference = models.CharField(
        choices=PROCESSREFERENCE, max_length=200, blank=False, null=False
    )
    measurement_instrument_type = models.CharField(
        choices=MEASUREMENTINSTRUMENTTYPE, max_length=200, blank=False, null=False
    )
    air_pressure_compensation_type = models.CharField(
        choices=AIRPRESSURECOMPENSATIONTYPE, max_length=200, blank=True, null=True
    )
    process_type = models.CharField(
        choices=PROCESSTYPE, max_length=200, blank=False, null=False
    )
    evaluation_procedure = models.CharField(
        choices=EVALUATIONPROCEDURE, max_length=200, blank=False, null=False
    )

    validated = models.BooleanField(null=True, blank=True, default=True, editable=False)
    executed = models.BooleanField(null=True, blank=True, default=False, editable=False)
    report = models.TextField(
        help_text="Information on GLD Import",
        blank=True,
        null=True,
    )

    class Meta:
        managed = True
        db_table = 'tools"."gld_importer'
        verbose_name = "GLD Import"
        verbose_name_plural = "GLD Imports"

    def clean(self):
        if self.file.path.endswith(".zip") or self.file.path.endswith(".csv"):
            return
        else:
            raise ValidationError("File should be of type: [csv, zip]")


class GMNImport(models.Model):
    file = models.FileField(
        upload_to="gmn",
        help_text="Bestand: .csv, .zip; bevat kolommen: meetpuntcode, gmwBroId, buisNummer, datum, subgroep*; gescheiden met komma.",
        null=True,
        blank=True,
        verbose_name="Meetpunten bestand",
    )
    name = models.CharField(
        max_length=255, null=True, blank=False, verbose_name="Meetnet naam"
    )
    delivery_context = models.CharField(
        blank=False,
        max_length=235,
        verbose_name="Kader aanlevering",
        choices=KADER_AANLEVERING_GMN,
    )
    monitoring_purpose = models.CharField(
        blank=False,
        max_length=235,
        verbose_name="Monitoringdoel",
        choices=MONITORINGDOEL,
    )
    groundwater_aspect = models.CharField(
        blank=False,
        max_length=235,
        verbose_name="Grondwateraspect",
        choices=(
            ("kwaliteit", "kwaliteit"),
            ("kwantiteit", "kwantiteit"),
        ),
    )
    start_date_monitoring = models.DateField(blank=False, null=True)
    quality_regime = models.CharField(
        choices=(
            ("IMBRO", "IMBRO"),
            ("IMBRO/A", "IMBRO/A"),
        ),
        max_length=255,
        null=True,
        blank=False,
        verbose_name="Kwaliteitsregime",
    )
    validated = models.BooleanField(
        null=True, blank=True, default=True, editable=False, verbose_name="Gevalideerd"
    )
    executed = models.BooleanField(
        null=True, blank=True, default=False, editable=False, verbose_name="Uitgevoerd"
    )
    report = models.TextField(
        help_text="Feedback van de import.",
        blank=True,
        null=True,
        verbose_name="Rapportage",
    )

    def __str__(self):
        return self.name

    class Meta:
        managed = True
        db_table = 'tools"."gmn_importer'
        verbose_name = "GMN Import"
        verbose_name_plural = "GMN Imports"

    def clean(self):
        if self.file.path.endswith(".zip") or self.file.path.endswith(".csv"):
            return
        else:
            raise ValidationError("File should be of type: [csv, zip]")


class GMWImport(models.Model):
    file = models.FileField(
        upload_to="gmw",
        help_text="csv. or zip.",
        validators=[],
        null=True,
        blank=True,
        verbose_name="Bestand",
    )
    name = models.CharField(max_length=255, null=True, blank=False, verbose_name="Naam")
    validated = models.BooleanField(
        null=True, blank=True, default=True, editable=False, verbose_name="Gevalideerd"
    )
    executed = models.BooleanField(
        null=True, blank=True, default=False, editable=False, verbose_name="Uitgevoerd"
    )
    report = models.TextField(
        help_text="Feedback van de import.",
        blank=True,
        null=True,
        verbose_name="Rapportage",
    )

    def __str__(self):
        return self.name

    class Meta:
        managed = True
        db_table = 'tools"."gmw_importer'
        verbose_name = "GMW Import"
        verbose_name_plural = "GMW Imports"

    def clean(self):
        if self.file.path.endswith(".zip") or self.file.path.endswith(".csv"):
            return
        else:
            raise ValidationError("File should be of type: [csv, zip]")
