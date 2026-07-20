from django.db import models

from bro_delivery.choices import MESSAGE_STATUS_CHOICES, REGISTRATION_TYPE_CHOICES, REQUEST_TYPE_CHOICES
from main.models import BaseModel

QUALITY_REGIME_CHOICES = [
    ("IMBRO", "IMBRO"),
    ("IMBRO/A", "IMBRO/A"),
]


class Message(BaseModel):
    """
    Abstract base for all BRO delivery messages sent via BROSTAR.

    Each concrete subclass corresponds to one BRO domain and holds a FK
    to the domain's root object (e.g. GroundwaterMonitoringWellStatic for GMW).
    """

    registration_type = models.CharField(
        max_length=60,
        choices=REGISTRATION_TYPE_CHOICES,
        verbose_name="Registratietype",
    )
    request_type = models.CharField(
        max_length=20,
        choices=REQUEST_TYPE_CHOICES,
        default="registration",
        verbose_name="Verzoektype",
    )
    quality_regime = models.CharField(
        max_length=10,
        choices=QUALITY_REGIME_CHOICES,
        null=True,
        blank=True,
        verbose_name="Kwaliteitsregime",
    )
    metadata = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Metadata",
        help_text="UploadTaskMetadata als dict (requestReference, deliveryAccountableParty, qualityRegime, …).",
    )
    sourcedocument_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Brondocumentdata",
        help_text="Brondocumentdata als dict, overeenkomend met het BROSTAR upload-model.",
    )
    bro_project = models.ForeignKey(
        "bro.BROProject",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="BRO Project",
    )
    # ── BROSTAR response fields ──────────────────────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=MESSAGE_STATUS_CHOICES,
        default="pending",
        verbose_name="Status",
    )
    bro_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="BRO ID",
    )
    bro_errors = models.JSONField(
        null=True,
        blank=True,
        verbose_name="BRO fouten",
    )
    brostar_task_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="BROSTAR taak ID",
    )
    brostar_task_url = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="BROSTAR taak URL",
    )

    class Meta:
        abstract = True
        ordering = ["-date_created"]


class GMWMessage(Message):
    """Bericht voor het domein Grondwatermonitoringput (GMW)."""

    groundwater_monitoring_well = models.ForeignKey(
        "gmw.GroundwaterMonitoringWellStatic",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="messages",
        verbose_name="Grondwatermonitoringput",
    )

    def __str__(self):
        well = self.groundwater_monitoring_well
        bro_id = well.bro_id if well else "-"
        return f"GMW Bericht [{self.registration_type}] {bro_id} ({self.status})"

    class Meta:
        db_table = 'bro_delivery"."gmw_message'
        verbose_name = "GMW Bericht"
        verbose_name_plural = "GMW Berichten"


class GLDMessage(Message):
    """Bericht voor het domein Grondwaterstandsdossier (GLD)."""

    groundwater_level_dossier = models.ForeignKey(
        "gld.GroundwaterLevelDossier",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="messages",
        verbose_name="Grondwaterstandsdossier",
    )

    def __str__(self):
        dossier = self.groundwater_level_dossier
        bro_id = dossier.gld_bro_id if dossier else "-"
        return f"GLD Bericht [{self.registration_type}] {bro_id} ({self.status})"

    class Meta:
        db_table = 'bro_delivery"."gld_message'
        verbose_name = "GLD Bericht"
        verbose_name_plural = "GLD Berichten"


class FRDMessage(Message):
    """Bericht voor het domein Formatieweerstandsdossier (FRD)."""

    formation_resistance_dossier = models.ForeignKey(
        "frd.FormationResistanceDossier",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="messages",
        verbose_name="Formatieweerstandsdossier",
    )

    def __str__(self):
        frd = self.formation_resistance_dossier
        bro_id = frd.frd_bro_id if frd else "-"
        return f"FRD Bericht [{self.registration_type}] {bro_id} ({self.status})"

    class Meta:
        db_table = 'bro_delivery"."frd_message'
        verbose_name = "FRD Bericht"
        verbose_name_plural = "FRD Berichten"


class GMNMessage(Message):
    """Bericht voor het domein Grondwatermonitoringnet (GMN)."""

    groundwater_monitoring_net = models.ForeignKey(
        "gmn.GroundwaterMonitoringNet",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="messages",
        verbose_name="Grondwatermonitoringnet",
    )

    def __str__(self):
        gmn = self.groundwater_monitoring_net
        bro_id = gmn.gmn_bro_id if gmn else "-"
        return f"GMN Bericht [{self.registration_type}] {bro_id} ({self.status})"

    class Meta:
        db_table = 'bro_delivery"."gmn_message'
        verbose_name = "GMN Bericht"
        verbose_name_plural = "GMN Berichten"
