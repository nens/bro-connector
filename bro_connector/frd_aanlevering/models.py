from django.db import models
from django.core.exceptions import ValidationError
from .choices import *
from django.core.validators import MaxValueValidator, MinValueValidator
from gmw_aanlevering.models import GroundwaterMonitoringTubesStatic
from gmn_aanlevering.models import GroundwaterMonitoringNet

# Create your models here.
class FormationResistanceDossier(models.Model):
    id = models.AutoField(primary_key=True)
    frd_bro_id = models.CharField(
        max_length=200, null=True, blank=True, editable=False, verbose_name="Broid FRD"
    )
    delivery_accountable_party = models.CharField(
        max_length=200, null=True, blank=False,
    )
    object_id_accountable_party = models.CharField(
        max_length=200, null=True, blank=False,
    )
    delivery_responsible_party = models.CharField(
        max_length=255, null=True, blank=False,
    )
    quality_regime = models.CharField(
        choices=(
            ("IMBRO", "IMBRO"),
            ("IMBRO/A", "IMBRO/A"),
        ),
        max_length=255, null=True, blank=False,
    )

    # Data not required, but returned by the BRO.
    assessment_type = models.CharField(
        choices=ASSESSMENT_TYPE,
        max_length=255, null=True, blank=False,
    )

    ### DO WE WANT TO ADD THESE?  NOT REQUIRED ###

    # first_measurement = models.DateField()
    # most_recent_measurement = models.DateField()
    # registration_history = models.ForeignKey()

    ##############################################

    # References to other tables
    instrument_configuration = models.ForeignKey()
    measurement_configuration = models.ForeignKey()
    electromagnetic_measurement_method = models.ForeignKey()
    gmw_tube = models.ForeignKey(GroundwaterMonitoringTubesStatic, on_delete = models.CASCADE, null = True, blank = False)
    gmn = models.ForeignKey(GroundwaterMonitoringNet, on_delete=models.CASCADE, null = True, blank = False)
    geo_ohm_measurement_method = models.ForeignKey()

    deliver_to_bro = models.BooleanField(blank=False, null=True)

    def __str__(self):
        return self.name
    
    def __unicode__(self):
        return self.name
    
    @property
    def name(self):
        nitg_code = self.filter.groundwater_monitoring_well.nitg_code
        name = f"FRD_{nitg_code}_{self.filter.tube_number}"
        return name
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding  
        super().save(*args, **kwargs)  
        

    class Meta:
            managed = True
            db_table = 'frd"."formation_resistance_dossier'
            verbose_name = "Formation Resistance Dossier"
            verbose_name_plural = "Formation Resistance Dossier (2.4)"
            _admin_name = "BRO formation resistance dossier"
            ordering = ("name",)

    

class InstrumentConfiguration(models.Model):
    configuration_name = models.TextField(max_length=40, null = False, blank = False)
    relative_position_send_coil = models.DecimalField(
        max_digits=6, decimal_places=3, null = True, blank = True,
    )
    relative_position_receive_coil = models.DecimalField(
        max_digits=6, decimal_places=3, null = True, blank = True,
    )
    secondary_receive_coil = models.CharField(
        choices=PRESENT
    )
    relative_position_secondary_coil = models.DecimalField(
        max_digits=6, decimal_places=3, null = True, blank = True,
    )
    coilfrequency_known = models.CharField(
        choices=PRESENT
    )
    coilfrequency = models.DecimalField(
        max_digits=6, decimal_places=3, null = True, blank = True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    ) # Unit is kHz
    instrument_length = models.DecimalField(
        max_digits=6, decimal_places=3, null = True, blank = True,
        validators=[MinValueValidator(1), MaxValueValidator(300)]
    ) # Unit is cm (centimeter)

    class Meta:
        db_table = 'frd"."instrument_configuration'
        verbose_name_plural = "Instrument Configurations"

class ElectromagneticMeasurementMethod(models.Model):
    measurement_date = models.DateField()
    measuring_responsible_party = models.TextField()
    measuring_procedure = models.CharField(
        blank=False,
        max_length=235,
        choices=MEASURING_PROCEDURE
    )
    assessment_procedure = models.CharField(
        blank=False,
        max_length=235,
        choices=ASSESSMENT_PROCEDURE
    )

    class Meta:
        db_table = 'frd"."electromagnetic_measurement_method'
        verbose_name_plural = "Electromagnetic Measurement Method"

class GeoOhmMeasurementMethod(models.Model):
    measuring_date = models.DateField()
    measuring_responsible_party = models.TextField()
    measuring_procedure = models.CharField(
        blank=False,
        max_length=235,
        choices=MEASURING_PROCEDURE
    )
    assessment_procedure = models.CharField(
        blank=False,
        max_length=235,
        choices=ASSESSMENT_PROCEDURE
    )

    class Meta:
        db_table = 'frd"."geo_ohm_measurement_method'
        verbose_name_plural = "Geo Ohm Measurement Method"


class GeoOhmMeasurementValue(models.Model):
    resistance = models.DecimalField(
        max_digits=6, decimal_places=3,
        validators=[MinValueValidator(0)]
    )
    measurement_configuration = models.ForeignKey('GeoOhmMeasurementMethod', on_delete = models.CASCADE, null = True, blank = False)

    class Meta:
        db_table = 'frd"."geo_ohm_measurement_value'
        verbose_name_plural = "Geo Ohm Measurement Value"


class GMWElectodeReference(models.Model):
    cable_number = models.IntegerField(blank=True, null=True)
    electrode_number = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'frd"."gmw_electrode_reference'
        verbose_name_plural = "GMW Electrode Reference"

class ElectrodePair(models.Model):
    id = models.AutoField(primary_key=True)
    # Static of dynamic electrode -> Ik denk static
    elektrode1 = models.ForeignKey('GMWElectrodeReference', on_delete = models.CASCADE, null = True, blank = False)
    elektrode2 = models.ForeignKey('GMWElectrodeReference', on_delete = models.CASCADE, null = True, blank = False)

    class Meta:
        db_table = 'frd"."electrode_pair'
        verbose_name_plural = "Electrode Pair"


class MeasurementConfiguration(models.Model):
    id = models.AutoField(primary_key=True)
    configuration_name = models.CharField(max_length=40, null = False, blank = False)
    measurement_pair = models.ForeignKey('ElectrodePair', on_delete = models.CASCADE, null = True, blank = False)
    flowcurrent_pair = models.ForeignKey('ElectrodePair', on_delete = models.CASCADE, null = True, blank = False)

    def clean(self):
        # Check if the config name is unique
        if len(
            MeasurementConfiguration.objects.filter(
                configuration_name = self.configuration_name
            )
        ) > 0:
            raise ValidationError(f"Configuration name ({self.configuration_name}) already exists.")
        
    class Meta:
        db_table = 'frd"."measurement_configuration'
        verbose_name_plural = "Measurement Configuration"


class ElectromagneticSeries(models.Model):
    id = models.AutoField(primary_key=True)

    class Meta:
        db_table = 'frd"."electromagnetic_series'
        verbose_name_plural = "Electromagnetic Series"


class FormationresistanceSeries(models.Model):
    id = models.AutoField(primary_key=True)

    class Meta:
        db_table = 'frd"."formationresistance_series'
        verbose_name_plural = "Formationresistance Series"


class ElectromagneticRecord(models.Model):
    id = models.AutoField(primary_key=True)
    series = models.ForeignKey('ElectromagneticSeries', on_delete = models.CASCADE, null = True, blank = False)
    measurement_datetime = models.DateTimeField(blank=True, null=True)

    vertical_position = models.DecimalField(
        max_digits=6, decimal_places=3,
        validators=[MinValueValidator(-750), MaxValueValidator(325)]
    ) # Unit = m (meter)

    primary_measurement = models.DecimalField(
        max_digits=6, decimal_places=3,
        validators=[MinValueValidator(0), MaxValueValidator(3000)]
    ) # Unit = mS/m (milliSiemens/meter)

    secondary_measurement = models.DecimalField(
        max_digits=6, decimal_places=3, blank=True, null=True,
        validators=[MinValueValidator(0), MaxValueValidator(3000)]
    ) # Unit = mS/m (milliSiemens/meter)

    class Meta:
        db_table = 'frd"."electromagnetic_record'
        verbose_name_plural = "Electromagnetic Records"


class FormationresistanceRecord(models.Model):
    id = models.AutoField(primary_key=True)
    series = models.ForeignKey('FormationresistanceSeries', on_delete = models.CASCADE, null = True, blank = False)
    measurement_datetime = models.DateTimeField(blank=True, null=True)
    vertical_position = models.DecimalField(
        max_digits=6, decimal_places=3,
        validators=[MinValueValidator(-750), MaxValueValidator(325)]
    ) # Unit = m (meter)

    formationresistance = models.DecimalField(
        max_digits=6, decimal_places=3,
        validators=[MinValueValidator(0), MaxValueValidator(10000)]
    ) # Unit = ohm.m

    status_qualitycontrol = models.CharField(
        blank=False,
        max_length=235,
        choices=QUALITY_CONTROL
    )

    class Meta:
        db_table = 'frd"."formationresistance_record'
        verbose_name_plural = "Formationresistance Records"