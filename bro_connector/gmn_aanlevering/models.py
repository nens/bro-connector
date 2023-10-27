from django.db import models
from .choices import KADER_AANLEVERING_GMN, MONITORINGDOEL
from gmw_aanlevering.models import GroundwaterMonitoringTubesStatic


# Create your models here.
class GroundwaterMonitoringNet(models.Model):
    id = models.AutoField(primary_key=True)
    deliver_to_bro = models.BooleanField(blank=True, null=True)
    gmn_bro_id = models.CharField(
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
        max_length=255, null=True, blank=True, verbose_name="Meetpunt naam"
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


EVENT_TYPE_CHOICES = [
     ("GMN_StartRegistration","Start Registration"),
     ("GMN_MeasuringPoint","Add MeasuringPoints"),
     ("GMN_MeasuringPointEndDate","Remove MeasuringPoints"),
     ("GMN_Closure","GMN Closure"),
]

class IntermediateEvent(models.Model):
    gmn = models.ForeignKey(GroundwaterMonitoringNet, on_delete=models.CASCADE)
    event_type =  models.CharField(
        choices=EVENT_TYPE_CHOICES,
        blank=True,
        null=True,
        max_length = 25,
    )
    event_date = models.DateTimeField(blank=True, null=True)
    synced_to_bro = models.BooleanField(blank=True, null=True, default=False)
    measuring_points = models.ManyToManyField(MeasuringPoint, blank=True)


    def __str__(self):
        return f"{self.gmn} - {self.event_type} - {self.event_date}"
    
    class Meta:
            managed = True
            db_table = 'gmn"."intermediate_event'
            verbose_name = "GMN Intermediate Event"
            _admin_name = "GMN Intermediate Event"
            ordering = ("event_date",)

LEVERINGSTATUS_CHOICES = [
     ("0","Nog niet aangeleverd"),
     ("1","1 keer gefaald"),
     ("2","2 keer gefaald"),
     ("3","3 keer gefaald"),
     ("4","Succesvol aangeleverd"),
]

class gmn_registration_log(models.Model):
    date_modified = models.DateField(null=True, blank=True)
    gmn_bro_id = models.CharField(max_length=254, null=True, blank=True)
    object_id_accountable_party  = models.CharField(max_length=255, null=True, blank=True)
    validation_status = models.CharField(max_length=254, null=True, blank=True)
    levering_id = models.CharField(max_length=254, null=True, blank=True)
    levering_status = models.CharField(choices=LEVERINGSTATUS_CHOICES, max_length = 10, null=True, blank=True, default = 0)
    levering_status_info = models.CharField(max_length=254, null=True, blank=True)
    comments = models.CharField(max_length=10000, null=True, blank=True)
    last_changed = models.CharField(max_length=254, null=True, blank=True)
    corrections_applied = models.BooleanField(blank=True, null=True)
    timestamp_end_registration = models.DateTimeField(blank=True, null=True)
    quality_regime = models.CharField(max_length=254, null=True, blank=True)
    file = models.CharField(max_length=254, null=True, blank=True)
    process_status = models.CharField(max_length=254, null=True, blank=True)

    def __str__(self):
        return f"{self.object_id_accountable_party}_log"

    class Meta:
        db_table = 'gmn"."gmn_registration_log'
        verbose_name = "GMN Registration Log"
        verbose_name_plural = "GMN Registration Logs"