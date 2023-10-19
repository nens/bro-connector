from django.db import models
from .choices import KADER_AANLEVERING_GMN, MONITORINGDOEL
from gmw_aanlevering.models import GroundwaterMonitoringTubesStatic


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
    
    @property
    def measuring_point_count(self):
        return MeasuringPoint.objects.filter(gmn=self).count()
        
    class Meta:
            managed = True
            db_table = 'gmn"."groundwater_monitoring_net'
            verbose_name = "Groundwater Monitoring Network"
            verbose_name_plural = "Groundwater Monitoring Networks (2.1)"
            _admin_name = "BRO meetnet"
            ordering = ("name",)

class MeasuringPoint(models.Model):
    gmn = models.ForeignKey(GroundwaterMonitoringNet, on_delete=models.CASCADE)
    groundwater_monitoring_tube = models.ForeignKey(GroundwaterMonitoringTubesStatic, on_delete = models.CASCADE, null = True, blank = True)
    code = models.CharField(
        max_length=255, null=True, blank=True, editable=False, verbose_name="Meetpunt naam"
    )
    
    def __str__(self):
        return self.code
    
    class Meta:
            managed = True
            db_table = 'gmn"."measuring_point'
            verbose_name = "GMN Meetpunt"
            verbose_name_plural = "GMN Meetpunt (3.1)"
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
            verbose_name = "GMN Intermediate Event"
            _admin_name = "GMN Intermediate Event"
            ordering = ("event_date",)