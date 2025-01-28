from django.db import models
import datetime
from .choices import *
from gld.choices import *
from bro.models import Organisation
from django.core.exceptions import ValidationError
from gmw.models import GroundwaterMonitoringTubeStatic

class BroImporter(models.Model):
    bro_type = models.CharField(
        max_length= 100, 
        choices=BRO_TYPES, 
        null=False,
    )
    kvk_number = models.IntegerField(null=False)
    bro_id = models.CharField(
        max_length=25, 
        help_text="Use this if you want to import an individual ID.", 
        null=True, 
        blank=True,
    )
    import_date = models.DateTimeField(editable=False, default=datetime.datetime.now())
    created_date = models.DateTimeField(editable=False, default=datetime.datetime.now())

    class Meta:
        managed = True
        db_table = 'tools"."bro_importer'
        verbose_name = "Importer"
        verbose_name_plural = "BRO Importer"


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
        verbose_name = "XML Import"
        verbose_name_plural = "XML Imports"


class GLDImport(models.Model):
    file = models.FileField(upload_to="bulk", help_text="csv. or zip.", validators=[], blank=True)
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
    status = models.CharField(choices=STATUSCODE, max_length=200, blank=False, null=False)

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

    validated = models.BooleanField(
        null=True, blank=True, default=False, editable=True
    )
    executed = models.BooleanField(
        null=True, blank=True, default=False, editable=True
    )
    report = models.TextField(
        help_text="process description",
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