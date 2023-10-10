from django.db import models
from .choices import KADER_AANLEVERING_GMN, MONITORINGDOEL


# Create your models here.
class GroundwaterMonitoringNet(models.Model):
    id = models.AutoField(primary_key=True)
    broid_gmn = models.CharField(
        max_length=255, null=True, blank=True, editable=False, verbose_name="Broid GMN"
    )
    delivery_accountable_party = models.CharField(
        max_length=255, null=True, blank=True,
    )
    delivery_responsible_party = models.CharField(
        max_length=255, null=True, blank=True,
    )
    quality_regime = models.CharField(
        max_length=255, null=True, blank=True,
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
    monitoring_purpose = models.CharField(
        blank=False,
        max_length=235,
        verbose_name="Monitoringdoel",
        choices= MONITORINGDOEL,
    )
    groundwater_aspect = models.CharField(
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
        return self.name
    
    def __unicode__(self):
        return self.name
        
    class Meta:
            managed = True
            db_table = 'gmn"."groundwater_monitoring_net'
            verbose_name = "BRO meetnet"
            verbose_name_plural = "BRO meetnetten (2.1)"
            _admin_name = "BRO meetnet"
            ordering = ("name",)

class MeasuringPoint(models.Model):
    gmn = models.ForeignKey(GroundwaterMonitoringNet, on_delete=models.CASCADE)
    code = models.CharField(
        max_length=255, null=True, blank=True, editable=False, verbose_name="Broid GMN"
    )
    def __str__(self):
        return self.code
    
    class Meta:
            managed = True
            db_table = 'gmn"."measuring_point'
            verbose_name = "BRO Meetpunt"
            verbose_name_plural = "BRO Meetpunt (3.1)"
            _admin_name = "BRO Meetpunt"
            ordering = ("code",)


class IntermediateEvent(models.Model):
    id = models.AutoField(primary_key=True)
    gmn = models.ForeignKey(GroundwaterMonitoringNet, on_delete=models.CASCADE)
    event_name =  models.TextField(
        blank=True, null=True
    )
    event_date = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.code
    
    class Meta:
            managed = True
            db_table = 'gmn"."intermediate_event'
            verbose_name = "Meetnet Tussentijdse Gebeurtenis"
            _admin_name = "Meetnet Tussentijdse Gebeurtenis"
            ordering = ("event_date",)