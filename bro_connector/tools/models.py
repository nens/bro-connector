from django.db import models
from pathlib import Path
import datetime
from tools.choices import BRO_TYPES, BRO_HANDLERS
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
from main.models import BaseModel


class BroImport(BaseModel):
    handler = models.CharField(
        max_length=100,
        choices=BRO_HANDLERS,
        null=False,
        verbose_name="Importeermethode",
        help_text="KvK: Haal data op obv KvK-nummer. Shape: Haal data op obv SHP bestand.",
    )
    bro_type = models.CharField(
        max_length=100,
        choices=BRO_TYPES,
        null=False,
        verbose_name="BRO type",
        help_text="Type BRO data om te importeren."
    )
    kvk_number = models.CharField(
        max_length=8,
        null=True, 
        blank=True,
        verbose_name="KvK nummer",
        help_text="Is optioneel als je de importeert op basis van SHP bestand."
    )

    file = models.FileField(
        upload_to="bulk",
        help_text="Zip bestand met daarin [.shp, .dbf, .prj, .shx]-bestanden van het projectgebied.",
        validators=[],
        null=True,
        blank=True,
        verbose_name="Shape Bestand"
    )
    @property
    def file_name(self):
        if self.file:
            return Path(self.file.name).stem + ".shp"
        return "-"
    file_name.fget.short_description = "Bestandsnaam"

    delete_outside = models.BooleanField(
        null=True, 
        blank=True, 
        default=False, 
        editable=True, 
        verbose_name="Punten verwijderen",
        help_text="Verwijder punten die buiten het SHP bestand liggen"
    )

    import_date = models.DateTimeField(editable=False, verbose_name="Datum geïmporteerd")
    created_date = models.DateTimeField(editable=False, verbose_name="Datum gecreëerd")

    validated = models.BooleanField(null=True, blank=True, default=True, editable=False, verbose_name="Gevalideerd")
    executed = models.BooleanField(null=True, blank=True, default=False, editable=False, verbose_name="Uitgevoerd")
    report = models.TextField(
        help_text="Informatie over de BRO Import",
        blank=True,
        null=True,
        verbose_name="Rapportage"
    )

    class Meta:
        managed = True
        db_table = 'tools"."bro_importer'
        verbose_name = "BRO Importer"
        verbose_name_plural = "BRO Importer"

    def save(self, *args, **kwargs) -> None:
        if not self.pk:
            self.import_date = datetime.datetime.now()
            self.created_date = datetime.datetime.now()
        super().save(*args, **kwargs)


class XMLImport(BaseModel):
    id = models.AutoField(primary_key=True, verbose_name="ID")
    created = models.DateTimeField(auto_now_add=True, editable=False, verbose_name="Datum aangemaakt")
    file = models.FileField(upload_to="bulk", validators=[], verbose_name="Bestand")
    report = models.TextField(
        help_text="process description",
        blank=True,
        null=True,
        verbose_name="Rapportage"
    )
    checked = models.BooleanField(
        help_text="checked",
        editable=False,
        default=False,
        blank=True,
        null=True,
        verbose_name="Gecheckt"
    )
    imported = models.BooleanField(
        verbose_name="Volledig geïmporteerd",
        default=False,
        editable=False,
        blank=True,
        null=True,
    )

    class Meta:
        managed = True
        db_table = 'tools"."xml_importer'
        verbose_name = "XML Importer"
        verbose_name_plural = "XML Importer"


class GLDImport(BaseModel):
    file = models.FileField(
        upload_to="bulk",
        help_text="columns: [time, value], optional: [status_quality_control, censor_reason, censor_limit]. Filetype: csv or zip.",
        validators=[],
        null=True,
        blank=True,
        verbose_name="Bestand"
    )
    name = models.CharField(max_length=255, null=True, blank=False, verbose_name="Naam")
    groundwater_monitoring_tube = models.ForeignKey(
        GroundwaterMonitoringTubeStatic,
        on_delete=models.CASCADE,
        null=True,
        blank=False,
        verbose_name="Filter"
    )
    responsible_party = models.ForeignKey(
        Organisation, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Bronhouder"
    )
    observation_type = models.CharField(
        choices=OBSERVATIONTYPE, max_length=200, blank=False, null=False, verbose_name="Observatie type"
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
        choices=STATUSCODE, max_length=200, blank=False, null=False, verbose_name="Status"
    )

    process_reference = models.CharField(
        choices=PROCESSREFERENCE, max_length=200, blank=False, null=False, verbose_name="Proces referentie"
    )
    measurement_instrument_type = models.CharField(
        choices=MEASUREMENTINSTRUMENTTYPE, max_length=200, blank=False, null=False, verbose_name="Meetinstrument type"
    )
    air_pressure_compensation_type = models.CharField(
        choices=AIRPRESSURECOMPENSATIONTYPE, max_length=200, blank=True, null=True, verbose_name="Luchtdrukcompensatie type"
    )
    process_type = models.CharField(
        choices=PROCESSTYPE,
        max_length=200,
        blank=False,
        null=False,
        default="algoritme",
        verbose_name="Proces type"
    )
    evaluation_procedure = models.CharField(
        choices=EVALUATIONPROCEDURE, max_length=200, blank=False, null=False, verbose_name="Evaluatieprocedure"
    )

    validated = models.BooleanField(null=True, blank=True, default=True, editable=False, verbose_name="Gevalideerd")
    executed = models.BooleanField(null=True, blank=True, default=False, editable=False, verbose_name="Uitgevoerd")
    report = models.TextField(
        help_text="Information on GLD Import",
        blank=True,
        null=True,
        verbose_name="Rapportage"
    )

    class Meta:
        managed = True
        db_table = 'tools"."gld_importer'
        verbose_name = "GLD Importer"
        verbose_name_plural = "GLD Importer"

    def __str__(self) -> str:
        return f"{self.name} ({self.date_created.date()})"

    def clean(self):
        if self.file.path.endswith(".zip") or self.file.path.endswith(".csv"):
            return
        else:
            raise ValidationError("File should be of type: [csv, zip]")


class GMNImport(BaseModel):
    file = models.FileField(
        upload_to="gmn",
        help_text="Bestand: .csv, .zip; bevat kolommen: meetpuntcode, gmwBroId, buisNummer, datum, subgroep*; gescheiden met komma.",
        null=True,
        blank=True,
        verbose_name="Meetpunten bestand",
    )
    name = models.CharField(
        max_length=255, null=True, blank=False, verbose_name="Meetnet"
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
        verbose_name = "GMN Importer"
        verbose_name_plural = "GMN Importer"

    def clean(self):
        if self.file.path.endswith(".zip") or self.file.path.endswith(".csv"):
            return
        else:
            raise ValidationError("File should be of type: [csv, zip]")


class GMWImport(BaseModel):
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
        verbose_name = "GMW Importer"
        verbose_name_plural = "GMW Importer"

    def clean(self):
        if self.file.path.endswith(".zip") or self.file.path.endswith(".csv"):
            return
        else:
            raise ValidationError("File should be of type: [csv, zip]")
