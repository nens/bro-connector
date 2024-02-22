from django.db import models
from .choices import KADER_AANLEVERING_GMN, MONITORINGDOEL
from gmw.models import GroundwaterMonitoringTubeStatic


# Create your models here.
class GroundwaterMonitoringNet(models.Model):
    id = models.AutoField(primary_key=True)
    deliver_to_bro = models.BooleanField(blank=False, null=True)
    gmn_bro_id = models.CharField(
        max_length=255, null=True, blank=True, editable=False, verbose_name="Broid GMN"
    )
    delivery_accountable_party = models.CharField(
        max_length=255,
        null=True,
        blank=False,
    )
    delivery_responsible_party = models.CharField(
        max_length=255,
        null=True,
        blank=False,
    )
    quality_regime = models.CharField(
        choices=(
            ("IMBRO", "IMBRO"),
            ("IMBRO/A", "IMBRO/A"),
        ),
        max_length=255,
        null=True,
        blank=False,
    )
    object_id_accountable_party = models.CharField(
        max_length=255,
        null=True,
        blank=False,
    )
    name = models.CharField(max_length=255, null=True, blank=False, verbose_name="Naam")
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
    end_date_monitoring = models.DateField(
        blank=True,
        null=True,
        help_text="Als een Meetnet verwijderd moet worden uit de BRO, verwijder het dan NIET uit de BRO-Connector. Vul dit veld in om de verwijdering uit de BRO te realiseren.",
    )
    removed_from_BRO = models.BooleanField(
        blank=False, null=True, default=False, editable=False
    )
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    @property
    def measuring_point_count(self):
        return MeasuringPoint.objects.filter(gmn=self).count()

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)

        # Create a new GMN_StartRegistration event when a new meetnet is added
        if is_new:
            IntermediateEvent.objects.create(
                gmn=self,
                event_type="GMN_StartRegistration",
                event_date=self.start_date_monitoring,
                synced_to_bro=False,
                deliver_to_bro=self.deliver_to_bro,
            )

        # Create a GMN_Closure event if an enddate is filled in
        if self.end_date_monitoring != None and self.removed_from_BRO != True:
            IntermediateEvent.objects.create(
                gmn=self,
                event_type="GMN_Closure",
                event_date=self.end_date_monitoring,
                synced_to_bro=False,
                deliver_to_bro=self.deliver_to_bro,
            )

    class Meta:
        managed = True
        db_table = 'gmn"."groundwater_monitoring_net'
        verbose_name = "Groundwatermonitoring Meetnet"
        verbose_name_plural = "Groundwatermonitoring Meetnetten"
        _admin_name = "Groundwatermonitoring Meetnet"
        ordering = ("name",)


class MeasuringPoint(models.Model):
    gmn = models.ForeignKey(GroundwaterMonitoringNet, on_delete=models.CASCADE)
    groundwater_monitoring_tube = models.ForeignKey(
        GroundwaterMonitoringTubeStatic,
        on_delete=models.CASCADE,
        null=True,
        blank=False,
    )
    code = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Meetpunt naam",
        editable=False,
    )
    synced_to_bro = models.BooleanField(
        blank=False, null=True, default=False, editable=False
    )
    added_to_gmn_date = models.DateField(blank=False, null=True)
    deleted_from_gmn_date = models.DateField(
        blank=True,
        null=True,
        help_text="Als een Meetpunt van een meetnet verwijderd moet worden, verwijder het object dan NIET uit de BRO-Connector, maar vul dit veld in!",
    )
    removed_from_BRO_gmn = models.BooleanField(
        blank=False, null=True, default=False, editable=False
    )

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        self.code = f"{self.groundwater_monitoring_tube.groundwater_monitoring_well_static.bro_id}_{self.groundwater_monitoring_tube.tube_number}"
        is_new = self._state.adding
        super().save(*args, **kwargs)

        # Create GMN_MeasuringPoint event if new measuringpoint is created
        if is_new:
            IntermediateEvent.objects.create(
                gmn=self.gmn,
                event_type="GMN_MeasuringPoint",
                event_date=self.added_to_gmn_date,
                synced_to_bro=False,
                measuring_point=self,
                deliver_to_bro=self.gmn.deliver_to_bro,
            )

        # Create GMN_MeasuringPointEndDate event if MP is deleted
        if self.deleted_from_gmn_date != None and self.removed_from_BRO_gmn != True:
            IntermediateEvent.objects.create(
                gmn=self.gmn,
                event_type="GMN_MeasuringPointEndDate",
                event_date=self.deleted_from_gmn_date,
                synced_to_bro=False,
                measuring_point=self,
                deliver_to_bro=self.gmn.deliver_to_bro,
            )

    class Meta:
        managed = True
        db_table = 'gmn"."measuring_point'
        verbose_name = "Meetpunt"
        verbose_name_plural = "Meetpunten"
        _admin_name = "Meetpunt"
        ordering = ("code",)


EVENT_TYPE_CHOICES = [
    ("GMN_StartRegistration", "Start Registration"),
    ("GMN_MeasuringPoint", "Add MeasuringPoint"),
    ("GMN_MeasuringPointEndDate", "Remove MeasuringPoint"),
    ("GMN_Closure", "GMN Closure"),
]


class IntermediateEvent(models.Model):
    gmn = models.ForeignKey(GroundwaterMonitoringNet, on_delete=models.CASCADE)
    event_type = models.CharField(
        choices=EVENT_TYPE_CHOICES,
        blank=False,
        null=True,
        max_length=25,
    )
    event_date = models.DateField(blank=False, null=True)
    synced_to_bro = models.BooleanField(blank=False, null=True, default=False)
    measuring_point = models.ForeignKey(
        MeasuringPoint, blank=True, null=True, on_delete=models.CASCADE
    )
    deliver_to_bro = models.BooleanField(blank=False, null=True, default=True)

    def __str__(self):
        return f"{self.gmn} - {self.event_type} - {self.event_date}"

    class Meta:
        managed = True
        db_table = 'gmn"."intermediate_event'
        verbose_name = "Tussentijdse Gebeurtenis"
        _admin_name = "Tussentijdse Gebeurtenissen"
        ordering = ("event_date",)


LEVERINGSTATUS_CHOICES = [
    ("0", "Nog niet aangeleverd"),
    ("1", "1 keer gefaald"),
    ("2", "2 keer gefaald"),
    ("3", "3 keer gefaald"),
    ("4", "Succesvol aangeleverd"),
]


class gmn_bro_sync_log(models.Model):
    date_modified = models.DateField(null=True, blank=True)
    event_type = models.CharField(
        choices=EVENT_TYPE_CHOICES,
        blank=False,
        null=True,
        max_length=25,
    )
    gmn_bro_id = models.CharField(max_length=254, null=True, blank=True)
    object_id_accountable_party = models.CharField(
        max_length=255, null=True, blank=True
    )
    validation_status = models.CharField(max_length=254, null=True, blank=True)
    levering_id = models.CharField(max_length=254, null=True, blank=True)
    levering_status = models.CharField(
        choices=LEVERINGSTATUS_CHOICES, max_length=10, null=True, blank=True, default=0
    )
    levering_status_info = models.CharField(max_length=254, null=True, blank=True)
    comments = models.CharField(max_length=10000, null=True, blank=True)
    last_changed = models.CharField(max_length=254, null=True, blank=True)
    corrections_applied = models.BooleanField(blank=True, null=True)
    timestamp_end_registration = models.DateTimeField(blank=True, null=True)
    quality_regime = models.CharField(max_length=254, null=True, blank=True)
    file = models.CharField(max_length=254, null=True, blank=True)
    process_status = models.CharField(max_length=254, null=True, blank=True)
    measuringpoint = models.ForeignKey(
        MeasuringPoint, blank=True, null=True, on_delete=models.CASCADE
    )

    def __str__(self):
        return f"{self.object_id_accountable_party}_log"

    class Meta:
        db_table = 'gmn"."gmn_bro_sync_log'
        verbose_name = "GMN Synchronisatie Log"
        verbose_name_plural = "GMN Synchronisatie Logs"
