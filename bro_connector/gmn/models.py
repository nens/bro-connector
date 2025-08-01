from django.db import models
from django.db.models import Manager
import random
from .choices import (
    KADER_AANLEVERING_GMN,
    BRO_DOMEINEN,
    PROVINCIE_NAMEN,
    MONITORINGDOEL,
    DELIVERY_TYPE_CHOICES,
    LEVERINGSTATUS_CHOICES,
    EVENT_TYPE_CHOICES,
)
from gmw.models import GroundwaterMonitoringTubeStatic
from bro.models import Organisation, BROProject


def get_color_value():
    # Generate random values for red, green, and blue components
    red = random.randint(0, 255)
    green = random.randint(0, 255)
    blue = random.randint(0, 255)

    # Convert decimal values to hexadecimal and format them
    color_code = f"#{red:02x}{green:02x}{blue:02x}"

    return color_code


# Create your models here.
class GroundwaterMonitoringNet(models.Model):
    id = models.AutoField(primary_key=True, verbose_name="DB ID")
    project = models.ForeignKey(
        BROProject,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Project"
    )
    deliver_to_bro = models.BooleanField(
        blank=False, null=True, verbose_name="Leveren aan BRO?"
    )
    gmn_bro_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        editable=True,
        verbose_name="GMN BRO ID",
        unique=True,
    )
    delivery_accountable_party = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="delivery_accountable_party_gmn",
        verbose_name="Bronhouder"
    )
    delivery_responsible_party = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="delivery_responsible_party_gmn",
        verbose_name="Dataleverancier"
    )
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
    object_id_accountable_party = models.CharField(
        max_length=255, null=True, blank=False, verbose_name="Intern ID"
    )
    name = models.CharField(max_length=255, null=True, blank=False, verbose_name="Naam")
    province_name = models.CharField(max_length=50, choices=PROVINCIE_NAMEN, verbose_name="Provincie", blank=False, null=False)
    bro_domain = models.CharField(max_length=50, choices=BRO_DOMEINEN, verbose_name="BRO Domein", blank=False, null=False)
    regio = models.CharField(max_length=100, verbose_name="Regio", blank=True, null=True)
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
        verbose_name="Stopdatum monitoring",
        help_text="Als een Meetnet verwijderd moet worden uit de BRO, verwijder het dan NIET uit de BRO-Connector. Vul dit veld in om de verwijdering uit de BRO te realiseren.",
    )
    removed_from_BRO = models.BooleanField(
        blank=False,
        null=True,
        default=False,
        editable=False,
        verbose_name="Verwijderd uit de BRO?",
    )
    description = models.TextField(null=True, blank=True, verbose_name="Beschrijving")
    color = models.CharField(max_length=50, null=True, blank=True)

    measuring_point: Manager["MeasuringPoint"]

    def __str__(self):
        if self.name:
            return self.name
        elif self.id:
            return self.id
        return "New Monitoring Net"

    def __unicode__(self):
        return self.name

    @property
    def bro_name(self):
        name = f"{self.province_name} - {self.bro_domain} - {self.name}"
        if self.regio:
            name += f" - {self.regio}"
        return name

    bro_name.fget.short_description = "BRO Naam"

    @property
    def project_number(self):
        if self.project:
            return self.project.project_number
        else:
            None
    project_number.fget.short_description = "Projectnummer"

    @property
    def measuring_point_count(self):
        return MeasuringPoint.objects.filter(gmn=self).count()
    measuring_point_count.fget.short_description = "Aantal meetpunten"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if not self.color or self.color == "#000000":
            self.color = get_color_value()

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
        if self.end_date_monitoring is not None and self.removed_from_BRO is not True:
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
        verbose_name = "Grondwatermonitoring Meetnet"
        verbose_name_plural = "Grondwatermonitoring Meetnetten"
        ordering = ("name",)


class Subgroup(models.Model):
    gmn = models.ForeignKey(
        GroundwaterMonitoringNet,
        related_name="subgroups",
        on_delete=models.CASCADE,
        verbose_name="Meetnet",
    )
    name = models.CharField(
        max_length=100, null=False, blank=False, verbose_name="Naam"
    )
    code = models.CharField(max_length=25, null=True, blank=True, verbose_name="Code")
    description = models.TextField(null=True, blank=True, verbose_name="Beschrijving")
    color = models.CharField(max_length=50, null=True, blank=True, verbose_name="Kleurcode")

    def __str__(self) -> str:
        if self.name:
            return self.name
        elif self.id:
            return self.id
        else:
            return "New subgroup"

    def save(self, *args, **kwargs):
        if not self.color or self.color == "#000000":
            self.color = get_color_value()
        super().save(*args, **kwargs)

    class Meta:
        managed = True
        db_table = 'gmn"."subgroup'
        verbose_name = "Subgroep"
        verbose_name_plural = "Subgroepen"
        ordering = ("name",)


class MeasuringPoint(models.Model):
    gmn = models.ForeignKey(
        GroundwaterMonitoringNet,
        related_name="measuring_point",
        on_delete=models.CASCADE,
        verbose_name="Meetnet",
    )
    subgroup = models.ManyToManyField(
        Subgroup,
        related_name="measuring_point",
        blank=True,
        help_text="Optional value to define smaller groups within a network.",
        verbose_name="Subgroep"
    )
    groundwater_monitoring_tube = models.ForeignKey(
        GroundwaterMonitoringTubeStatic,
        on_delete=models.CASCADE,
        null=True,
        blank=False,
        verbose_name="Filter",
        related_name="measuring_point",
    )
    code = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Meetpunt naam",
        editable=False,
    )
    synced_to_bro = models.BooleanField(
        blank=False,
        null=True,
        default=False,
        editable=False,
        verbose_name="Opgestuurd naar de BRO",
    )
    added_to_gmn_date = models.DateField(
        blank=True, null=True, verbose_name="Datum toegevoegd aan meetnet"
    )
    deleted_from_gmn_date = models.DateField(
        blank=True,
        null=True,
        help_text="Als een Meetpunt van een meetnet verwijderd moet worden, verwijder het object dan NIET uit de BRO-Connector, maar vul dit veld in!",
        verbose_name="Datum uit meetnet gehaald",
    )
    removed_from_BRO_gmn = models.BooleanField(
        blank=False,
        null=True,
        default=False,
        editable=False,
        verbose_name="Verwijderd uit de BRO?",
    )

    def __str__(self):
        if self.code:
            return self.code
        elif self.id:
            return self.id
        else:
            return "New monitoring point"

    def save(self, *args, **kwargs):
        if (
            self.groundwater_monitoring_tube.groundwater_monitoring_well_static.well_code
            is None
        ):
            self.code = f"{self.groundwater_monitoring_tube.groundwater_monitoring_well_static.bro_id}_{self.groundwater_monitoring_tube.tube_number}"
        else:
            self.code = f"{self.groundwater_monitoring_tube.groundwater_monitoring_well_static.well_code}_{self.groundwater_monitoring_tube.tube_number}"

        is_new = self._state.adding
        if not is_new:
            old = MeasuringPoint.objects.get(pk=self.pk)

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
        else:
            if self.gmn.name != old.gmn.name:
                IntermediateEvent.objects.create(
                gmn=self.gmn,
                event_type="GMN_MeasuringPoint",
                event_date=self.added_to_gmn_date,
                synced_to_bro=False,
                measuring_point=self,
                deliver_to_bro=self.gmn.deliver_to_bro,
            )
            if self.groundwater_monitoring_tube != old.groundwater_monitoring_tube:
                IntermediateEvent.objects.create(
                    gmn=self.gmn,
                    event_type="GMN_TubeReference",
                    event_date=self.added_to_gmn_date,
                    synced_to_bro=False,
                    measuring_point=self,
                    deliver_to_bro=self.gmn.deliver_to_bro,
                )

        # Create GMN_MeasuringPointEndDate event if MP is deleted
        if (
            self.deleted_from_gmn_date is not None
            and self.removed_from_BRO_gmn is not True
        ):
            IntermediateEvent.objects.create(
                gmn=self.gmn,
                event_type="GMN_MeasuringPointEndDate",
                event_date=self.deleted_from_gmn_date,
                synced_to_bro=False,
                measuring_point=self,
                deliver_to_bro=self.gmn.deliver_to_bro,
            )
            ## remove the meetpunt from the meetnet in question
            ## OR: meetpunt will stay but has end date and will not be used therefore?

    def list_subgroups(self):
        return ", ".join([subgroup.name for subgroup in self.subgroup.all()])

    class Meta:
        managed = True
        db_table = 'gmn"."measuring_point'
        verbose_name = "Meetpunt"
        verbose_name_plural = "Meetpunten"
        ordering = ("code",)
        constraints = [
            models.UniqueConstraint(
                fields=["gmn", "groundwater_monitoring_tube"],
                name="unique_gmn_groundwater_monitoring_tube",
            )
        ]


class MeasuringPointSubgroup(models.Model):
    measuring_point = models.ForeignKey(
        MeasuringPoint,
        on_delete=models.CASCADE,
    )
    subgroup = models.ForeignKey(
        Subgroup,
        on_delete=models.SET_NULL,
        null=True,
    )


class IntermediateEvent(models.Model):
    gmn = models.ForeignKey(
        GroundwaterMonitoringNet, on_delete=models.CASCADE, verbose_name="Meetnet"
    )
    measuring_point = models.ForeignKey(
        MeasuringPoint,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        verbose_name="Meetpunt",
    )
    event_type = models.CharField(
        choices=EVENT_TYPE_CHOICES,
        blank=False,
        null=True,
        max_length=25,
        verbose_name="Bericht type",
    )
    event_date = models.DateField(
        blank=False, null=True, verbose_name="Datum gebeurtenis"
    )
    deliver_to_bro = models.BooleanField(
        blank=False, null=True, default=True, verbose_name="Leverplichtig BRO"
    )
    synced_to_bro = models.BooleanField(
        blank=False, null=True, default=False, verbose_name="Opgestuurd naar de BRO"
    )

    def __str__(self):
        return f"{self.gmn} - {self.event_type} - {self.event_date}"

    class Meta:
        managed = True
        db_table = 'gmn"."intermediate_event'
        verbose_name = "Tussentijdse Gebeurtenis"
        verbose_name_plural = "Tussentijdse Gebeurtenissen"
        ordering = ("event_date",)


class gmn_bro_sync_log(models.Model):
    date_modified = models.DateField(null=True, blank=True, verbose_name="Datum aangepast")
    event_type = models.CharField(
        choices=EVENT_TYPE_CHOICES,
        blank=False,
        null=True,
        max_length=25,
        verbose_name="Gebeurtenis type"
    )
    gmn_bro_id = models.CharField(
        max_length=254, null=True, blank=True, verbose_name="GMN BRO ID"
    )
    object_id_accountable_party = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Intern ID"
    )
    validation_status = models.CharField(max_length=254, null=True, blank=True, verbose_name="Validatiestatus")
    delivery_id = models.CharField(max_length=254, null=True, blank=True, verbose_name="Levering ID")
    delivery_type = models.CharField(
        choices=DELIVERY_TYPE_CHOICES,
        blank=False,
        max_length=40,
        default="register",
        verbose_name="Levering type"
    )
    delivery_status = models.CharField(
        choices=LEVERINGSTATUS_CHOICES, max_length=10, null=True, blank=True, default=0, verbose_name="Levering status"
    )
    delivery_status_info = models.CharField(max_length=254, null=True, blank=True, verbose_name="Levering status info")
    comments = models.CharField(max_length=10000, null=True, blank=True, verbose_name="Commentaar")
    last_changed = models.CharField(max_length=254, null=True, blank=True, verbose_name="Laatst veranderd")
    corrections_applied = models.BooleanField(blank=True, null=True, verbose_name="Correcties toegepast")
    timestamp_end_registration = models.DateTimeField(blank=True, null=True, verbose_name="Moment einde registratie")
    quality_regime = models.CharField(max_length=254, null=True, blank=True, verbose_name="Kwaliteitsregime")
    file = models.CharField(max_length=254, null=True, blank=True, verbose_name="Bestand")
    process_status = models.CharField(max_length=254, null=True, blank=True, verbose_name="Proces status")
    measuringpoint = models.ForeignKey(
        MeasuringPoint, blank=True, null=True, on_delete=models.CASCADE, verbose_name="Meetpunt"
    )

    def __str__(self):
        return f"{self.object_id_accountable_party}_log"

    class Meta:
        db_table = 'gmn"."gmn_bro_sync_log'
        verbose_name = "GMN Synchronisatie Log"
        verbose_name_plural = "GMN Synchronisatie Logs"
