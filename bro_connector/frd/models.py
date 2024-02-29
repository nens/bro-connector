from django.db import models
import logging
import reversion
import re
import math
from .choices import *
from django.core.validators import MaxValueValidator, MinValueValidator
from gmw.models import GroundwaterMonitoringTubeStatic, GeoOhmCable, ElectrodeStatic
from gmn.models import GroundwaterMonitoringNet
from django.db.models.signals import post_delete, post_save, pre_delete, pre_save

logger = logging.getLogger(__name__)


# Create your models here.
class FormationResistanceDossier(models.Model):
    frd_bro_id = models.CharField(
        max_length=200, null=True, blank=True, editable=True, verbose_name="Bro-ID FRD"
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
    groundwater_monitoring_tube = models.ForeignKey(
        GroundwaterMonitoringTubeStatic,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    groundwater_monitoring_net = models.ForeignKey(
        GroundwaterMonitoringNet, on_delete=models.CASCADE, null=True, blank=True
    )

    deliver_to_bro = models.BooleanField(blank=False, null=True)

    closure_date = models.DateField(blank=True, null=True)

    closed_in_bro = models.BooleanField(
        blank=False, null=False, editable=True, default=False
    )

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    @property
    def name(self):
        if self.frd_bro_id != None:
            return f"{self.frd_bro_id}"
        return f"FRD_{self.object_id_accountable_party}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)

    class Meta:
        managed = True
        db_table = 'frd"."formationresistance_dossier'
        verbose_name = "Formationresistance Dossier"
        verbose_name_plural = "Formationresistance Dossier"
        _admin_name = "BRO formationresistance dossier"


class ElectromagneticMeasurementMethod(models.Model):
    formation_resistance_dossier = models.ForeignKey(
        FormationResistanceDossier, on_delete=models.CASCADE, null=True, blank=True
    )
    bro_id = models.CharField(max_length=254, null=True, blank=True)
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


class InstrumentConfiguration(models.Model):
    formation_resistance_dossier = models.ForeignKey(
        FormationResistanceDossier, on_delete=models.CASCADE, null=True, blank=True
    )
    bro_id = models.CharField(max_length=254, null=True, blank=True)
    configuration_name = models.CharField(max_length=40, null=False, blank=False)
    electromagnetic_measurement_method = models.ForeignKey(
        ElectromagneticMeasurementMethod,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    relative_position_send_coil = models.FloatField(
        null=True,
        blank=True,
    )
    relative_position_receive_coil = models.FloatField(
        null=True,
        blank=True,
    )
    secondary_receive_coil = models.CharField(
        choices=PRESENT,
        max_length=200,
        blank=True,
        null=True,
    )
    relative_position_secondary_coil = models.FloatField(
        null=True,
        blank=True,
    )
    coilfrequency_known = models.CharField(
        choices=PRESENT,
        max_length=200,
        blank=True,
        null=True,
    )
    coilfrequency = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )  # Unit is kHz
    instrument_length = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(300)],
    )  # Unit is cm (centimeter)

    class Meta:
        managed = True
        db_table = 'frd"."instrument_configuration'
        verbose_name_plural = "Instrument Configurations"


class GeoOhmMeasurementMethod(models.Model):
    formation_resistance_dossier = models.ForeignKey(
        FormationResistanceDossier, on_delete=models.CASCADE, null=False, blank=False
    )
    bro_id = models.CharField(max_length=254, null=True, blank=True)
    measurement_date = models.DateField(null=False, blank=True)
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

    def save(self, *args, **kwargs):
        if self.pk != None:
            super().save(*args, **kwargs)
            return

        super().save(*args, **kwargs)

        calculated_method = CalculatedFormationresistanceMethod.objects.filter(
            geo_ohm_measurement_method=self
        ).last()

        if calculated_method == None:
            CalculatedFormationresistanceMethod.objects.create(
                geo_ohm_measurement_method=self,
                responsible_party=85101117,  # Nelen & Schuurmans Consultancy KVK
                assessment_procedure="onbekend",
            )


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
        GMWElectrodeReference,
        on_delete=models.CASCADE,
        null=True,
        blank=False,
        related_name="electrode_one",
    )
    elektrode2 = models.ForeignKey(
        GMWElectrodeReference,
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
    formation_resistance_dossier = models.ForeignKey(
        FormationResistanceDossier, on_delete=models.CASCADE, null=True, blank=True
    )
    bro_id = models.CharField(max_length=254, null=True, blank=True)
    configuration_name = models.CharField(
        max_length=40, null=False, blank=False, unique=True
    )
    measurement_pair = models.ForeignKey(
        ElectrodePair,
        on_delete=models.CASCADE,
        null=True,
        blank=False,
        related_name="measurement_pair",
    )
    flowcurrent_pair = models.ForeignKey(
        ElectrodePair,
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
    electromagnetic_measurement_method = models.ForeignKey(
        ElectromagneticMeasurementMethod,
        on_delete=models.CASCADE,
        null=True,
        blank=False,
    )

    class Meta:
        managed = True
        db_table = 'frd"."electromagnetic_series'
        verbose_name_plural = "Electromagnetic Series"


class GeoOhmMeasurementValue(models.Model):
    geo_ohm_measurement_method = models.ForeignKey(
        GeoOhmMeasurementMethod, on_delete=models.CASCADE, null=True, blank=True
    )
    formationresistance = models.FloatField(validators=[MinValueValidator(0)])
    measurement_configuration = models.ForeignKey(
        MeasurementConfiguration, on_delete=models.CASCADE, null=False, blank=False
    )
    datetime = models.DateTimeField(blank=False, null=False)

    class Meta:
        managed = True
        db_table = 'frd"."geo_ohm_measurement_value'
        verbose_name_plural = "Geo Ohm Measurement Value"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        calculated_method = CalculatedFormationresistanceMethod.objects.filter(
            geo_ohm_measurement_method=self.geo_ohm_measurement_method
        ).first()

        print(calculated_method)

        if calculated_method != None:
            create_calculated_resistance_from_geo_ohm(self, calculated_method)


class ElectromagneticRecord(models.Model):
    series = models.ForeignKey(
        ElectromagneticSeries, on_delete=models.CASCADE, null=True, blank=False
    )

    vertical_position = models.FloatField(
        validators=[MinValueValidator(-750), MaxValueValidator(325)],
    )  # Unit = m (meter)

    primary_measurement = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(3000)],
    )  # Unit = mS/m (milliSiemens/meter)

    secondary_measurement = models.FloatField(
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


class CalculatedFormationresistanceMethod(models.Model):
    geo_ohm_measurement_method = models.ForeignKey(
        GeoOhmMeasurementMethod, on_delete=models.CASCADE, null=True, blank=True
    )
    electromagnetic_measurement_method = models.ForeignKey(
        ElectromagneticMeasurementMethod,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    responsible_party = models.CharField(
        max_length=200,
        null=True,
        blank=False,
    )
    assessment_procedure = models.CharField(
        blank=False, max_length=235, choices=ASSESSMENT_PROCEDURE
    )

    class Meta:
        managed = True
        db_table = 'frd"."calculated_formationresistance_method'
        verbose_name_plural = "Calculated Formationresistance Method"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.electromagnetic_measurement_method != None:
            create_electromagnetic_series(self)

        if self.geo_ohm_measurement_method != None:
            print(True)
            create_geo_ohm_series(self)


class FormationresistanceSeries(models.Model):
    calculated_formationresistance = models.ForeignKey(
        CalculatedFormationresistanceMethod,
        on_delete=models.CASCADE,
        null=True,
        blank=False,
    )

    class Meta:
        managed = True
        db_table = 'frd"."formationresistance_series'
        verbose_name_plural = "Formationresistance Series"


class FormationresistanceRecord(models.Model):
    """
    Schijnbare formatieweerstand meetreeks
    """

    series = models.ForeignKey(
        FormationresistanceSeries, on_delete=models.CASCADE, null=True, blank=False
    )

    vertical_position = models.FloatField(
        validators=[MinValueValidator(-750), MaxValueValidator(325)],
    )  # Unit = m (meter)

    formationresistance = models.FloatField(
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
    bro_id = models.CharField(max_length=254, null=True, blank=True)
    event_type = models.CharField(
        choices=EVENT_TYPE_CHOICES,
        blank=False,
        max_length=40,
    )
    frd = models.ForeignKey(
        FormationResistanceDossier, on_delete=models.CASCADE, blank=True, null=True
    )
    geo_ohm_measuring_method = models.ForeignKey(
        GeoOhmMeasurementMethod,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        default=None,
    )
    electomagnetic_method = models.ForeignKey(
        ElectromagneticMeasurementMethod,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        default=None,
    )
    process_status = models.CharField(max_length=254, null=True, blank=True)
    comment = models.CharField(max_length=100000, null=True, blank=True)
    xml_filepath = models.CharField(max_length=254, null=True, blank=True)
    delivery_status = models.IntegerField(
        choices=LEVERINGSTATUS_CHOICES, null=True, blank=True, default=0
    )
    delivery_status_info = models.CharField(max_length=254, null=True, blank=True)
    delivery_id = models.CharField(max_length=254, null=True, blank=True)
    delivery_type = models.CharField(
        choices=DELIVERY_TYPE_CHOICES,
        blank=False,
        max_length=40,
    )

    def __str__(self):
        return f"{self.event_type}_log"

    class Meta:
        db_table = 'frd"."frd_sync_log'
        verbose_name = "FRD Synchronisatie Log"
        verbose_name_plural = "FRD Synchronisatie Logs"


def create_calculated_resistance_from_geo_ohm(
    instance: GeoOhmMeasurementValue,
    calculated_method: CalculatedFormationresistanceMethod,
) -> None:
    series = FormationresistanceSeries.objects.filter(
        calculated_formationresistance=calculated_method
    ).first()

    if series == None:
        series = FormationresistanceSeries.objects.create(
            calculated_formationresistance=calculated_method
        )

    create_or_update_geo_record(instance, series)


def calculate_formationresistance_electro(measurement: float) -> float:
    return 1 / measurement


def create_electromagnetic_series(instance: CalculatedFormationresistanceMethod):
    measurement_method = instance.electromagnetic_measurement_method
    try:
        monitoring_tube = (
            measurement_method.formation_resistance_dossier.groundwater_monitoring_tube
        )
    except measurement_method.formation_resistance_dossier.DoesNotExist:
        logger.exception(
            "Unable to find a connected Monitoring Tube, cannot calculate the formation resistance."
        )
        return

    series = ElectromagneticSeries.objects.get(
        electromagnetic_measurement_method=measurement_method
    )
    records = ElectromagneticRecord.objects.filter(series=series)

    form_series = FormationresistanceSeries.objects.create(
        calculated_formationresistance=instance
    )

    for record in records:
        FormationresistanceRecord.objects.create(
            series=form_series,
            vertical_position=record.vertical_position,
            formationresistance=(1 / record.formationresistance),
            status_qualitycontrol="onbeslist",
        )


def calculate_formationresistance_geo_ohm(
    resistance: float, area: float, electrode_distance: float
) -> float:
    """
    Calculate the formation resistance in Ohm.m \n

    Arguments:\n
    - resistance:           geo ohm measured resistance (Ohm)
    - electrode_distance:   length of the cable between the electrodes (m)

    """
    return resistance * 4 * math.pi * electrode_distance


def get_measurement_pair(
    geo_ohm_measurement_value: GeoOhmMeasurementValue,
) -> ElectrodePair:
    return geo_ohm_measurement_value.measurement_configuration.measurement_pair


def string_to_float(string: str) -> float:
    negative = 1
    if string[0] == "-":
        negative = -1
        string = string.removeprefix("-")

    split_string = string.split(",")

    if len(split_string) == 1:
        return float(split_string[0]) * negative
    elif len(split_string) == 2:
        return float(f"{split_string[0]}.{split_string[1]}") * negative
    else:
        raise Exception("Unkown formationresistance format.")


def retrieve_electrode_position(
    electrode_reference: GMWElectrodeReference,
    monitoring_tube: GroundwaterMonitoringTubeStatic,
) -> float:
    geo_ohm_cable = GeoOhmCable.objects.filter(
        cable_number=electrode_reference.cable_number,
        groundwater_monitoring_tube_static=monitoring_tube,
    ).first()

    electrode = ElectrodeStatic.objects.filter(
        geo_ohm_cable=geo_ohm_cable,
        electrode_number=electrode_reference.electrode_number,
    ).first()

    positie_float = string_to_float(electrode.electrode_position)

    return positie_float


def retrieve_geo_ohm_cable_area(
    electrode_reference: GMWElectrodeReference,
    monitoring_tube: GroundwaterMonitoringTubeStatic,
) -> float:
    geo_ohm_cable = GeoOhmCable.objects.filter(
        cable_number=electrode_reference.cable_number,
        groundwater_monitoring_tube_static=monitoring_tube,
    ).first()

    # Will be retrieving the area if this is gonna be registered under geo ohm cables
    return 0.01


def calculate_electode_distance(electrode_position_1, electrode_position_2) -> float:
    print(electrode_position_1, electrode_position_2)
    if electrode_position_1 == None or electrode_position_2 == None:
        return None
    return round(abs(electrode_position_1 - electrode_position_2), 3)


def create_or_update_geo_record(
    measurement_value: GeoOhmMeasurementValue, series: FormationresistanceSeries
):
    monitoring_tube = (
        measurement_value.geo_ohm_measurement_method.formation_resistance_dossier.groundwater_monitoring_tube
    )

    measurement_pair = get_measurement_pair(measurement_value)
    electrode_position_1 = retrieve_electrode_position(
        measurement_pair.elektrode1, monitoring_tube
    )
    electrode_position_2 = retrieve_electrode_position(
        measurement_pair.elektrode2, monitoring_tube
    )
    measurement_position = (electrode_position_1 + electrode_position_2) / 2

    electrode_distance = calculate_electode_distance(
        electrode_position_1, electrode_position_2
    )
    area = retrieve_geo_ohm_cable_area(measurement_pair.elektrode1, monitoring_tube)
    calculated_resistance = calculate_formationresistance_geo_ohm(
        resistance=float(measurement_value.formationresistance),
        area=area,
        electrode_distance=electrode_distance,
    )

    resistance_record = FormationresistanceRecord.objects.filter(
        series=series,
        vertical_position=measurement_position,
    ).first()

    if resistance_record == None:
        FormationresistanceRecord.objects.create(
            series=series,
            vertical_position=measurement_position,
            formationresistance=calculated_resistance,
            status_qualitycontrol="onbeslist",
        )

    if resistance_record.formationresistance != calculated_resistance:
        resistance_record.formationresistance = calculated_resistance
        resistance_record.status_qualitycontrol = "onbeslist"
        resistance_record.save()


def create_geo_ohm_series(instance: CalculatedFormationresistanceMethod):
    measurement_method = instance.geo_ohm_measurement_method
    try:
        monitoring_tube = (
            measurement_method.formation_resistance_dossier.groundwater_monitoring_tube
        )
    except measurement_method.formation_resistance_dossier.DoesNotExist:
        logger.exception(
            "Unable to find a connected Monitoring Tube, cannot calculate the formation resistance."
        )
        return

    measurement_values = GeoOhmMeasurementValue.objects.filter(
        geo_ohm_measurement_method=measurement_method,
    )

    series = FormationresistanceSeries.objects.filter(
        calculated_formationresistance=instance,
    ).first()

    if series == None:
        series = FormationresistanceSeries.objects.create(
            calculated_formationresistance=instance
        )

    for measurement_value in measurement_values:
        create_or_update_geo_record(measurement_value, series)


#### REVERSION
try:
    reversion.register(FormationResistanceDossier)
except:
    pass

try:
    reversion.register(GeoOhmMeasurementMethod)
except:
    pass

try:
    reversion.register(GeoOhmMeasurementValue)
except:
    pass
