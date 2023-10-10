from django.db import models
from .choices import KADER_AANLEVERING_GMN, MONITORINGDOEL


# Create your models here.
class GroundwaterMonitoringNet(models.Model):
    id = models.AutoField(primary_key=True)
    broid_gmn = models.CharField(
        max_length=255, null=True, blank=True, editable=False, verbose_name="Broid GMN"
    )
    accountable_party = models.CharField(
        max_length=255, null=True, blank=True
    )
    object_id_accountable_party = models.CharField(
        max_length=255, null=True, blank=True,
    )
    name = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Naam"
    )
    delivery_context = models.CharField(
        blank=False,
        max_length=235,
        verbose_name="Kader aanlevering",
        choices=KADER_AANLEVERING_GMN,
    )
    monitoringPurpose = models.CharField(
        blank=False,
        max_length=235,
        verbose_name="Monitoringdoel",
        choices= MONITORINGDOEL,
    )
    groundwaterAspect = models.CharField(
        blank=True,
        max_length=235,
        verbose_name="Grondwateraspect",
        choices=(
            ("kwaliteit", "kwaliteit"),
            ("kwantiteit", "kwantiteit"),
        ),
    )
    start_date_monitoring = models.DateField(blank=True, null=True)
    end_date_monitoring = models.DateField(blank=True, null=True)


    def __str__(self):
        return self.naam
    
    def __unicode__(self):
        return self.naam
        
    class Meta:
            managed = True
            db_table = 'gmn"."Meetnet'
            verbose_name = "BRO meetnet"
            verbose_name_plural = "BRO meetnetten (2.1)"
            _admin_name = "BRO meetnet"
            ordering = ("naam",)

class MeasuringPoint(models.Model):
    gmn = models.ForeignKey(GroundwaterMonitoringNet, on_delete=models.CASCADE)
    code = models.CharField(
        max_length=255, null=True, blank=True, editable=False, verbose_name="Broid GMN"
    )