from django.db import models
from .choices import *
from django.core.validators import MaxValueValidator, MinValueValidator
from gmw_aanlevering.models import GroundwaterMonitoringTubesStatic
from gmn_aanlevering.models import GroundwaterMonitoringNet


# Create your models here.
class FormationResistance(models.Model):
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
            db_table = 'frd"."formation_resistance'
            verbose_name = "Formation Resistance"
            verbose_name_plural = "Formation Resistance (2.4)"
            _admin_name = "BRO formation resistance"
            ordering = ("name",)


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


class GeoOhmMeasurementValue(models.Model):
    resistance = models.DecimalField(
        max_digits=6, decimal_places=3,
        validators=[MinValueValidator(0)]
    )
    measurement_configuration = models.ForeignKey('GeoOhmMeasurementMethod', on_delete = models.CASCADE, null = True, blank = False)

class GMWElectodeReference(models.Model):
     cable_number = models.IntegerField(blank=True, null=True)
     electrode_number = models.IntegerField(blank=True, null=True)

class ElectrodePair(models.Model):
    id = models.AutoField(primary_key=True)
    # Static of dynamic electrode -> Ik denk static
    elektrode1 = models.ForeignKey('GMWElectrodeReference', on_delete = models.CASCADE, null = True, blank = False)
    elektrode2 = models.ForeignKey('GMWElectrodeReference', on_delete = models.CASCADE, null = True, blank = False)
     
class MeasurementConfiguration(models.Model):
    id = models.AutoField(primary_key=True)
    configuratie_naam = models.CharField(max_length=255, null=True, blank=True,)
    meetpaar = models.ForeignKey('ElectrodePair', on_delete = models.CASCADE, null = True, blank = False)
    stroompaar = models.ForeignKey('ElectrodePair', on_delete = models.CASCADE, null = True, blank = False)

class ElectrodemagneticSeries(models.Model):
    id = models.AutoField(primary_key=True)


# For now just a class to which multiple records can link.
class FormationresistanceSeries(models.Model):
    id = models.AutoField(primary_key=True)

class ElectrodemagneticRecord(models.Model):
    id = models.AutoField(primary_key=True)
    series = models.ForeignKey('ElectrodemagneticSeries', on_delete = models.CASCADE, null = True, blank = False)
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