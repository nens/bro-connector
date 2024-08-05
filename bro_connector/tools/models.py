from django.db import models
import datetime
from .choices import *

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
