from django.db import models
from django.core.exceptions import ValidationError
from .choices import *
from django.core.validators import MaxValueValidator, MinValueValidator
from gmw.models import GroundwaterMonitoringTubesStatic
from gmn.models import GroundwaterMonitoringNet

# Create your models here.
class FormationResistanceDossier(models.Model):
    frd_bro_id = models.CharField(
        max_length=200, null=True, blank=True, editable=False, verbose_name="Bro-ID FRD"
    )
    delivery_accountable_party = models.CharField(
        max_length=200,
        null=True,
        blank=False,
    )
    object_id_accountable_party = models.CharField(
        max_length=200,
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

    # Data not required, but returned by the BRO.
    assessment_type = models.CharField(
        choices=ASSESSMENT_TYPE,
        max_length=255,
        null=True,
        blank=True,
    )

    ### DO WE WANT TO ADD THESE?  NOT REQUIRED ###

    # first_measurement = models.DateField()
    # most_recent_measurement = models.DateField()
    # registration_history = models.ForeignKey()

    ##############################################

    # References to other tables
    instrument_configuration = models.ForeignKey(
        "InstrumentConfiguration", on_delete=models.CASCADE, null=True, blank=True
    )
    electromagnetic_measurement_method = models.ForeignKey(
        "ElectromagneticMeasurementMethod",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    gmw_tube = models.ForeignKey(
        GroundwaterMonitoringTubesStatic,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    gmn = models.ForeignKey(
        GroundwaterMonitoringNet, on_delete=models.CASCADE, null=True, blank=True
    )
    geo_ohm_measurement_method = models.ForeignKey(
        "GeoOhmMeasurementMethod", on_delete=models.CASCADE, null=True, blank=True
    )

    deliver_to_bro = models.BooleanField(blank=False, null=True)

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    @property
    def name(self):
        nitg_code = self.gmw_tube.groundwater_monitoring_well.nitg_code
        name = f"FRD_{nitg_code}_{self.gmw_tube.tube_number}"
        return name

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)

    class Meta:
        managed = True
        db_table = 'frd"."formation_resistance_dossier'
        verbose_name = "Formation Resistance Dossier"
        verbose_name_plural = "Formation Resistance Dossier"
        _admin_name = "BRO formation resistance dossier"


class InstrumentConfiguration(models.Model):
    configuration_name = models.TextField(max_length=40, null=False, blank=False)
    relative_position_send_coil = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
    )
    relative_position_receive_coil = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
    )
    secondary_receive_coil = models.CharField(
        choices=PRESENT,
        max_length=200,
        blank=True,
        null=True,
    )
    relative_position_secondary_coil = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
    )
    coilfrequency_known = models.CharField(
        choices=PRESENT,
        max_length=200,
        blank=True,
        null=True,
    )
    coilfrequency = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )  # Unit is kHz
    instrument_length = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(300)],
    )  # Unit is cm (centimeter)

    class Meta:
        managed = True
        db_table = 'frd"."instrument_configuration'
        verbose_name_plural = "Instrument Configurations"


class ElectromagneticMeasurementMethod(models.Model):
    measurement_date = models.DateField(null=False, blank=True)
    measuring_responsible_party = models.TextField(
        max_length=200, null=False, blank=True
    )
    measuring_procedure = models.CharField(
        blank=False, max_length=235, choices=MEASURING_PROCEDURE
    )
    assessment_procedure = models.CharField(
        blank=False, max_length=235, choices=ASSESSMENT_PROCEDURE
    )

    def __str__(self):
        return f"{self.measuring_responsible_party} {self.measurement_date}"

    class Meta:
        managed = True
        db_table = 'frd"."electromagnetic_measurement_method'
        verbose_name_plural = "Electromagnetic Measurement Method"


class GeoOhmMeasurementMethod(models.Model):
    measurement_date = models.DateField()
    measuring_responsible_party = models.CharField(
        blank=False,
        max_length=235,
    )
    measuring_procedure = models.CharField(
        blank=False, max_length=235, choices=MEASURING_PROCEDURE
    )
    assessment_procedure = models.CharField(
        blank=False, max_length=235, choices=ASSESSMENT_PROCEDURE
    )

    def __str__(self):
        return f"{self.measuring_responsible_party} {self.measurement_date}"

    class Meta:
        managed = True
        db_table = 'frd"."geo_ohm_measurement_method'
        verbose_name_plural = "Geo Ohm Measurement Method"


class GMWElectrodeReference(models.Model):
    cable_number = models.IntegerField(blank=True, null=True)
    electrode_number = models.IntegerField(blank=True, null=True)

    def __str__(self) -> str:
        return f"C{self.cable_number}E{self.electrode_number}"

    class Meta:
        managed = True
        db_table = 'frd"."gmw_electrode_reference'
        verbose_name_plural = "GMW Electrode Reference"


class ElectrodePair(models.Model):
    # Static of dynamic electrode -> Ik denk static
    elektrode1 = models.ForeignKey(
        "GMWElectrodeReference",
        on_delete=models.CASCADE,
        null=True,
        blank=False,
        related_name="electrode_one",
    )
    elektrode2 = models.ForeignKey(
        "GMWElectrodeReference",
        on_delete=models.CASCADE,
        null=True,
        blank=False,
        related_name="electrode_two",
    )

    def __str__(self):
        return f"{self.elektrode1} - {self.elektrode2}"

    class Meta:
        managed = True
        db_table = 'frd"."electrode_pair'
        verbose_name_plural = "Electrode Pair"


class MeasurementConfiguration(models.Model):
    bro_id = models.CharField(max_length=254, null=True, blank=True)
    configuration_name = models.CharField(
        max_length=40, null=False, blank=False, unique=True
    )
    measurement_pair = models.ForeignKey(
        "ElectrodePair",
        on_delete=models.CASCADE,
        null=True,
        blank=False,
        related_name="measurement_pair",
    )
    flowcurrent_pair = models.ForeignKey(
        "ElectrodePair",
        on_delete=models.CASCADE,
        null=True,
        blank=False,
        related_name="flowcurrent_pair",
    )

    def __str__(self):
        if self.configuration_name != None:
            return f"{self.configuration_name}"
        else:
            return f"{self.id}: {self.flowcurrent_pair}-{self.measurement_pair}"

    class Meta:
        managed = True
        db_table = 'frd"."measurement_configuration'
        verbose_name_plural = "Measurement Configuration"


class ElectromagneticSeries(models.Model):

    class Meta:
        managed = True
        db_table = 'frd"."electromagnetic_series'
        verbose_name_plural = "Electromagnetic Series"


class FormationresistanceSeries(models.Model):

    class Meta:
        managed = True
        db_table = 'frd"."formationresistance_series'
        verbose_name_plural = "Formationresistance Series"


# class FRDRecord(models.Model):
#     pass


class GeoOhmMeasurementValue(models.Model):
    formationresistance = models.DecimalField(
        max_digits=6, decimal_places=3, validators=[MinValueValidator(0)]
    )
    measurement_configuration = models.ForeignKey(
        "MeasurementConfiguration", on_delete=models.CASCADE, null=True, blank=False
    )

    class Meta:
        managed = True
        db_table = 'frd"."geo_ohm_measurement_value'
        verbose_name_plural = "Geo Ohm Measurement Value"


class ElectromagneticRecord(models.Model):
    series = models.ForeignKey(
        "ElectromagneticSeries", on_delete=models.CASCADE, null=True, blank=False
    )

    vertical_position = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        validators=[MinValueValidator(-750), MaxValueValidator(325)],
    )  # Unit = m (meter)

    primary_measurement = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        validators=[MinValueValidator(0), MaxValueValidator(3000)],
    )  # Unit = mS/m (milliSiemens/meter)

    secondary_measurement = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(3000)],
    )  # Unit = mS/m (milliSiemens/meter)

    @property
    def formationresistance(self):
        if self.primary_measurement != None:
            return self.primary_measurement
        elif self.secondary_measurement != None:
            return self.secondary_measurement
        else:
            return None

    class Meta:
        managed = True
        db_table = 'frd"."electromagnetic_record'
        verbose_name_plural = "Electromagnetic Records"


class FormationresistanceRecord(models.Model):
    series = models.ForeignKey(
        "FormationresistanceSeries", on_delete=models.CASCADE, null=True, blank=False
    )
    vertical_position = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        validators=[MinValueValidator(-750), MaxValueValidator(325)],
    )  # Unit = m (meter)

    formationresistance = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        validators=[MinValueValidator(0), MaxValueValidator(10000)],
    )  # Unit = ohm.m

    status_qualitycontrol = models.CharField(
        blank=False, max_length=235, choices=QUALITY_CONTROL
    )

    class Meta:
        managed = True
        db_table = 'frd"."formationresistance_record'
        verbose_name_plural = "Formationresistance Records"


class FrdSyncLog(models.Model):
    synced = models.BooleanField(default=False)
    date_modified = models.DateTimeField(auto_now=True)
    event_type = models.CharField(
        choices=EVENT_TYPE_CHOICES,
        blank=False,
        max_length=40,
    )
    frd = models.ForeignKey(
        FormationResistanceDossier, on_delete=models.CASCADE, blank=True, null=True
    )
    configuration = models.ForeignKey(
        MeasurementConfiguration, on_delete=models.CASCADE, blank=True, null=True
    )
    process_status = models.CharField(max_length=254, null=True, blank=True)
    comment = models.CharField(max_length=10000, null=True, blank=True)
    xml_filepath = models.CharField(max_length=254, null=True, blank=True)
    delivery_status = models.IntegerField(
        choices=LEVERINGSTATUS_CHOICES, null=True, blank=True, default=0
    )
    delivery_status_info = models.CharField(max_length=254, null=True, blank=True)
    delivery_id = models.CharField(max_length=254, null=True, blank=True)

    def __str__(self):
        return f"{self.event_type}_{self.frd.object_id_accountable_party}_log"

    class Meta:
        db_table = 'frd"."frd_sync_log'
        verbose_name = "FRD Synchronisatie Log"
        verbose_name_plural = "FRD Synchronisatie Logs"
