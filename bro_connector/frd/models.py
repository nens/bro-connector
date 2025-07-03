from django.db import models
import logging
import reversion
import math
from .choices import (
    ASSESSMENT_PROCEDURE,
    ASSESSMENT_TYPE,
    PRESENT,
    MEASURING_PROCEDURE,
    QUALITY_CONTROL,
    EVENT_TYPE_CHOICES,
    LEVERINGSTATUS_CHOICES,
    DELIVERY_TYPE_CHOICES,
)
from django.core.validators import MaxValueValidator, MinValueValidator
from gmw.models import GroundwaterMonitoringTubeStatic, GeoOhmCable, Electrode
from gmn.models import GroundwaterMonitoringNet
import datetime
from bro.models import Organisation
from main.models import BaseModel

logger = logging.getLogger(__name__)


# Create your models here.
class FormationResistanceDossier(BaseModel):
    frd_bro_id = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        editable=False,
        verbose_name="FRD BRO ID",
        unique=True,
    )
    delivery_accountable_party = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="delivery_accountable_party_frd",
        verbose_name="Bronhouder"
    )  # Could be property from tube
    delivery_responsible_party = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="delivery_responsible_party_frd",
        verbose_name="Dataleverancier"
    )  # Could be property from tube
    quality_regime = models.CharField(
        choices=(
            ("IMBRO", "IMBRO"),
            ("IMBRO/A", "IMBRO/A"),
        ),
        max_length=255,
        null=True,
        blank=False,
        verbose_name="Kwaliteitsregime"
    )

    # Data not required, but returned by the BRO.
    assessment_type = models.CharField(
        choices=ASSESSMENT_TYPE,
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Bepaling type"
    )

    # References to other tables
    groundwater_monitoring_tube = models.ForeignKey(
        GroundwaterMonitoringTubeStatic,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Filter"
    )
    groundwater_monitoring_net = models.ForeignKey(
        GroundwaterMonitoringNet, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Meetnet"
    )

    deliver_to_bro = models.BooleanField(blank=False, null=True, verbose_name="Leveren aan BRO")
    closure_date = models.DateField(blank=True, null=True, editable=False, verbose_name="Sluitingsdatum meetnet")
    closed_in_bro = models.BooleanField(
        blank=False, null=False, editable=True, default=False, verbose_name="Afgesloten in de BRO"
    )

    @property
    def first_measurement(self):
        # TODO: add functionality to standard function?
        geo_ohm_method = (
            GeoOhmMeasurementMethod.objects.filter(formation_resistance_dossier=self)
            .order_by("measurement_date")
            .first()
        )

        electro_magnetic_method = (
            ElectromagneticMeasurementMethod.objects.filter(
                formation_resistance_dossier=self
            )
            .order_by("measurement_date")
            .first()
        )

        geo_ohm_method_date = getattr(geo_ohm_method, "measurement_date", None)
        electro_magnetic_method_date = getattr(
            electro_magnetic_method, "measurement_date", None
        )

        if geo_ohm_method_date and electro_magnetic_method:
            return min(geo_ohm_method_date, electro_magnetic_method_date)
        elif geo_ohm_method_date:
            return geo_ohm_method_date
        elif electro_magnetic_method_date:
            return electro_magnetic_method_date
        else:
            return None
    first_measurement.fget.short_description = "Datum eerste meting"

    @property
    def most_recent_measurement(self):
        geo_ohm_method = (
            GeoOhmMeasurementMethod.objects.filter(formation_resistance_dossier=self)
            .order_by("-measurement_date")
            .first()
        )

        electro_magnetic_method = (
            ElectromagneticMeasurementMethod.objects.filter(
                formation_resistance_dossier=self
            )
            .order_by("-measurement_date")
            .first()
        )

        geo_ohm_method_date = getattr(geo_ohm_method, "measurement_date", None)
        electro_magnetic_method_date = getattr(
            electro_magnetic_method, "measurement_date", None
        )

        if geo_ohm_method_date and electro_magnetic_method:
            return min(geo_ohm_method_date, electro_magnetic_method_date)
        elif geo_ohm_method_date:
            return geo_ohm_method_date
        elif electro_magnetic_method_date:
            return electro_magnetic_method_date
        else:
            return None
    most_recent_measurement.fget.short_description = "Datum meest recente meting"

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    @property
    def name(self):
        return f"FRD_{self.groundwater_monitoring_tube.__str__()}"
    name.fget.short_description = "Naam"

    def save(self, *args, **kwargs):
        if self.closed_in_bro is True and self.closure_date is None:
            self.closure_date = datetime.datetime.now().date()
        elif self.closed_in_bro is False and self.closure_date is not None:
            self.closure_date = None

        super().save(*args, **kwargs)

    class Meta:
        managed = True
        db_table = 'frd"."formationresistance_dossier'
        verbose_name = "Formatieweerstand Dossier"
        verbose_name_plural = "Formatieweerstand Dossiers"
        _admin_name = "BRO Formatieweerstand Dossier"


class ElectromagneticMeasurementMethod(BaseModel):
    formation_resistance_dossier = models.ForeignKey(
        FormationResistanceDossier, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Formatieweerstand dossier [FRD]"
    )
    measurement_date = models.DateField(null=False, blank=True, verbose_name="Meetdatum")
    measuring_responsible_party = models.ForeignKey(
        Organisation, on_delete=models.CASCADE, null=False, blank=True, verbose_name="Bronhouder"
    )
    measuring_procedure = models.CharField(
        blank=False, max_length=235, choices=MEASURING_PROCEDURE, verbose_name="Meetprocedure"
    )
    assessment_procedure = models.CharField(
        blank=False, max_length=235, choices=ASSESSMENT_PROCEDURE, verbose_name="Beoordeling procedure"
    )

    def __str__(self):
        return f"{self.measuring_responsible_party} {self.measurement_date}"

    class Meta:
        managed = True
        db_table = 'frd"."electromagnetic_measurement_method'
        verbose_name_plural = "Electromagnetisch Meetmethode"


class InstrumentConfiguration(BaseModel):
    formation_resistance_dossier = models.ForeignKey(
        FormationResistanceDossier, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Formatieweerstand dossier [FRD]"
    )
    configuration_name = models.CharField(max_length=40, null=False, blank=False, verbose_name="Configuratie")
    electromagnetic_measurement_method = models.ForeignKey(
        ElectromagneticMeasurementMethod,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Electromagnetische meetmethode"
    )
    relative_position_send_coil = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Relatieve positie zendspoel"
    )
    relative_position_receive_coil = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Relatieve positie ontvangstspoel"
    )
    secondary_receive_coil = models.CharField(
        choices=PRESENT,
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Secundaire ontvangstspoel"
    )
    relative_position_secondary_coil = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Relatieve positie secundaire spoel"
    )
    coilfrequency_known = models.CharField(
        choices=PRESENT,
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Frequentie spoel bekend"
    )
    coilfrequency = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Frequentie spoel"
    )  # Unit is kHz
    instrument_length = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(300)],
        verbose_name="Instrumentlengte"
    )  # Unit is cm (centimeter)

    class Meta:
        managed = True
        db_table = 'frd"."instrument_configuration'
        verbose_name_plural = "Instrument Configuraties"


class GeoOhmMeasurementMethod(BaseModel):
    formation_resistance_dossier = models.ForeignKey(
        FormationResistanceDossier, on_delete=models.CASCADE, null=False, blank=False, verbose_name="Formatieweerstand dossier [FRD]"
    )
    measurement_date = models.DateField(null=False, blank=True, verbose_name="Meetdatum")
    measuring_responsible_party = models.ForeignKey(
        Organisation, on_delete=models.CASCADE, null=False, blank=True, verbose_name="Bronhouder"
    )
    measuring_procedure = models.CharField(
        blank=False, max_length=235, choices=MEASURING_PROCEDURE, verbose_name="Meetprocedure"
    )
    assessment_procedure = models.CharField(
        blank=False, max_length=235, choices=ASSESSMENT_PROCEDURE, verbose_name="Beoordelingsprocedure"
    )

    def __str__(self):
        return f"{self.measuring_responsible_party} {self.measurement_date}"

    class Meta:
        managed = True
        db_table = 'frd"."geo_ohm_measurement_method'
        verbose_name_plural = "Geo Ohm Meetmethodes"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            super().save(*args, **kwargs)
            return

        super().save(*args, **kwargs)

        calculated_method = CalculatedFormationresistanceMethod.objects.filter(
            geo_ohm_measurement_method=self
        ).last()

        if calculated_method is None:
            CalculatedFormationresistanceMethod.objects.create(
                geo_ohm_measurement_method=self,
                responsible_party=85101117,  # Nelen & Schuurmans Consultancy KVK
                assessment_procedure="onbekend",
            )


class GMWElectrodeReference(BaseModel):
    cable_number = models.IntegerField(blank=True, null=True, verbose_name="Kabelnummer")
    electrode_number = models.IntegerField(blank=True, null=True, verbose_name="Electrodenummer")

    def __str__(self) -> str:
        return f"C{self.cable_number}E{self.electrode_number}"

    class Meta:
        managed = True
        db_table = 'frd"."gmw_electrode_reference'
        verbose_name_plural = "GMW Elektrode Referenties"


class ElectrodePair(BaseModel):
    # Static of dynamic electrode -> Ik denk static
    elektrode1 = models.ForeignKey(
        GMWElectrodeReference,
        on_delete=models.CASCADE,
        null=True,
        blank=False,
        related_name="electrode_one",
        verbose_name="Electrode 1"
    )
    elektrode2 = models.ForeignKey(
        GMWElectrodeReference,
        on_delete=models.CASCADE,
        null=True,
        blank=False,
        related_name="electrode_two",
        verbose_name="Electrode 2"
    )

    def __str__(self):
        return f"{self.elektrode1}-{self.elektrode2}"

    class Meta:
        managed = True
        db_table = 'frd"."electrode_pair'
        verbose_name_plural = "Elektrode Paren"


class MeasurementConfiguration(BaseModel):
    formation_resistance_dossier = models.ForeignKey(
        FormationResistanceDossier, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Formatieweerstand dossier [FRD]"
    )
    configuration_name = models.CharField(
        max_length=40, null=False, blank=False, unique=True, verbose_name="Configuratie"
    )
    measurement_pair = models.ForeignKey(
        ElectrodePair,
        on_delete=models.CASCADE,
        null=True,
        blank=False,
        related_name="measurement_pair",
        verbose_name="Meetpaar"
    )
    flowcurrent_pair = models.ForeignKey(
        ElectrodePair,
        on_delete=models.CASCADE,
        null=True,
        blank=False,
        related_name="flowcurrent_pair",
        verbose_name="Stroompaar"
    )

    def __str__(self):
        if self.configuration_name is not None:
            return f"{self.configuration_name}"
        else:
            return f"{self.id}: {self.flowcurrent_pair}-{self.measurement_pair}"

    class Meta:
        managed = True
        db_table = 'frd"."measurement_configuration'
        verbose_name_plural = "Meetconfiguraties"


class ElectromagneticSeries(BaseModel):
    electromagnetic_measurement_method = models.ForeignKey(
        ElectromagneticMeasurementMethod,
        on_delete=models.CASCADE,
        null=True,
        blank=False,
        verbose_name="Electromagnetische meetmethode"
    )

    class Meta:
        managed = True
        db_table = 'frd"."electromagnetic_series'
        verbose_name_plural = "Electromagnetische Series"


class GeoOhmMeasurementValue(BaseModel):
    geo_ohm_measurement_method = models.ForeignKey(
        GeoOhmMeasurementMethod, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Geo Ohm Meetmethode"
    )
    formationresistance = models.FloatField(validators=[MinValueValidator(0)], verbose_name="Formatieweerstand", help_text="Ohm")
    measurement_configuration = models.ForeignKey(
        MeasurementConfiguration, on_delete=models.CASCADE, null=False, blank=False, verbose_name="Configuratie"
    )
    datetime = models.DateTimeField(blank=False, null=False, verbose_name="Meetmoment")

    class Meta:
        managed = True
        db_table = 'frd"."geo_ohm_measurement_value'
        verbose_name_plural = "Geo Ohm Meetwaardes"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        calculated_method = CalculatedFormationresistanceMethod.objects.filter(
            geo_ohm_measurement_method=self.geo_ohm_measurement_method
        ).first()

        print(calculated_method)

        if calculated_method is not None:
            create_calculated_resistance_from_geo_ohm(self, calculated_method)


class ElectromagneticRecord(BaseModel):
    series = models.ForeignKey(
        ElectromagneticSeries, on_delete=models.CASCADE, null=True, blank=False, verbose_name="Electromagnetische Series"
    )

    vertical_position = models.FloatField(
        validators=[MinValueValidator(-750), MaxValueValidator(325)],
        verbose_name="Verticale positie",
        help_text="m NAP"
    )  # Unit = m (meter)

    primary_measurement = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(3000)],
        verbose_name="Primaire meting"
    )  # Unit = mS/m (milliSiemens/meter)

    secondary_measurement = models.FloatField(
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(3000)],
        verbose_name="Secundaire meting"
    )  # Unit = mS/m (milliSiemens/meter)

    @property
    def formationresistance(self):
        if self.primary_measurement is not None:
            return self.primary_measurement
        elif self.secondary_measurement is not None:
            return self.secondary_measurement
        else:
            return None
    formationresistance.fget.short_description = "Formatieweerstand"

    class Meta:
        managed = True
        db_table = 'frd"."electromagnetic_record'
        verbose_name_plural = "Electromagnetisch Waarden"


class CalculatedFormationresistanceMethod(BaseModel):
    geo_ohm_measurement_method = models.ForeignKey(
        GeoOhmMeasurementMethod, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Geo Ohm Meetmethode"
    )
    electromagnetic_measurement_method = models.ForeignKey(
        ElectromagneticMeasurementMethod,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Electromagnetische Meetmethode"
    )
    responsible_party = models.CharField(
        max_length=200,
        null=True,
        blank=False,
        verbose_name="Bronhouder"
    )
    assessment_procedure = models.CharField(
        blank=False, max_length=235, choices=ASSESSMENT_PROCEDURE, verbose_name="Beoordelingsprocedure"
    )

    class Meta:
        managed = True
        db_table = 'frd"."calculated_formationresistance_method'
        verbose_name_plural = "Berekende Formatieweerstand Methode"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.electromagnetic_measurement_method is not None:
            create_electromagnetic_series(self)

        if self.geo_ohm_measurement_method is not None:
            print(True)
            create_geo_ohm_series(self)


class FormationresistanceSeries(BaseModel):
    calculated_formationresistance = models.ForeignKey(
        CalculatedFormationresistanceMethod,
        on_delete=models.CASCADE,
        null=True,
        blank=False,
        verbose_name="Berekende Formatieweerstand Methode"
    )

    class Meta:
        managed = True
        db_table = 'frd"."formationresistance_series'
        verbose_name_plural = "Formatieweerstand Series"


class FormationresistanceRecord(BaseModel):
    """
    Schijnbare formatieweerstand meetreeks
    """

    series = models.ForeignKey(
        FormationresistanceSeries, on_delete=models.CASCADE, null=True, blank=False, verbose_name="Formatieweerstand series"
    )

    vertical_position = models.FloatField(
        validators=[MinValueValidator(-750), MaxValueValidator(325)],
        verbose_name="Verticale positie",
        help_text="m NAP"
    )  # Unit = m (meter)

    formationresistance = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(10000)],
        verbose_name="Formatieweerstand",
        help_text="Ohm.m"
    )  # Unit = ohm.m

    status_qualitycontrol = models.CharField(
        blank=False, max_length=235, choices=QUALITY_CONTROL, verbose_name="Status kwaliteitscontrole"
    )

    class Meta:
        managed = True
        db_table = 'frd"."formationresistance_record'
        verbose_name_plural = "Formatieweerstand Waarden"


class FrdSyncLog(BaseModel):
    synced = models.BooleanField(default=False, editable=False, verbose_name="Gesynchroniseerd")
    date_modified = models.DateTimeField(auto_now=True, verbose_name="Datum aangepast")
    bro_id = models.CharField(max_length=254, null=True, blank=True, verbose_name="BRO ID")
    event_type = models.CharField(
        choices=EVENT_TYPE_CHOICES,
        blank=False,
        max_length=40,
        verbose_name="Gebeurtenis type"
    )
    frd = models.ForeignKey(
        FormationResistanceDossier, on_delete=models.CASCADE, blank=True, null=True, verbose_name="FRD"
    )
    geo_ohm_measuring_method = models.ForeignKey(
        GeoOhmMeasurementMethod,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        default=None,
        verbose_name="Geo Ohm Meetmethode"
    )
    electomagnetic_method = models.ForeignKey(
        ElectromagneticMeasurementMethod,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        default=None,
        verbose_name="Electromagnetische Meetmethode"
    )
    process_status = models.CharField(max_length=254, null=True, blank=True, verbose_name="Proces status")
    comment = models.CharField(max_length=100000, null=True, blank=True, verbose_name="Commentaar")
    xml_filepath = models.CharField(max_length=254, null=True, blank=True, verbose_name="Locatie XML bestand")
    delivery_status = models.IntegerField(
        choices=LEVERINGSTATUS_CHOICES, null=True, blank=True, default=0, verbose_name="Leveringsstatus"
    )
    delivery_status_info = models.CharField(max_length=254, null=True, blank=True, verbose_name="Levering status info")
    delivery_id = models.CharField(max_length=254, null=True, blank=True, verbose_name="Levering ID")
    delivery_type = models.CharField(
        choices=DELIVERY_TYPE_CHOICES,
        blank=False,
        max_length=40,
        default="register",
        verbose_name="Leveringstype"
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

    if series is None:
        series = FormationresistanceSeries.objects.create(
            calculated_formationresistance=calculated_method
        )

    create_or_update_geo_record(instance, series)


def calculate_formationresistance_electro(measurement: float) -> float:
    return 1 / measurement


def create_electromagnetic_series(instance: CalculatedFormationresistanceMethod):
    measurement_method = instance.electromagnetic_measurement_method

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


def calculate_ohm_from_ohmm(
    calculated_resistance: float, electrode_distance: float
) -> float:
    """
    Inverse if the calculated formation resistance, to return the actual ohm value, instead of Ohm m
    """
    return calculated_resistance / (4 * math.pi * electrode_distance)


def calculate_formationresistance_geo_ohm(
    resistance: float, electrode_distance: float
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

    electrode = Electrode.objects.filter(
        geo_ohm_cable=geo_ohm_cable,
        electrode_number=electrode_reference.electrode_number,
    ).first()

    positie_float = string_to_float(electrode.electrode_position)

    return positie_float


def calculate_electode_distance(electrode_position_1, electrode_position_2) -> float:
    print(electrode_position_1, electrode_position_2)
    if electrode_position_1 is None or electrode_position_2 is None:
        return None
    return round(abs(electrode_position_1 - electrode_position_2), 3)


def create_or_update_geo_record(
    measurement_value: GeoOhmMeasurementValue, series: FormationresistanceSeries
):
    monitoring_tube = measurement_value.geo_ohm_measurement_method.formation_resistance_dossier.groundwater_monitoring_tube

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

    calculated_resistance = calculate_formationresistance_geo_ohm(
        resistance=float(measurement_value.formationresistance),
        electrode_distance=electrode_distance,
    )

    resistance_record = FormationresistanceRecord.objects.filter(
        series=series,
        vertical_position=measurement_position,
    ).first()

    if resistance_record is None:
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
    measurement_values = GeoOhmMeasurementValue.objects.filter(
        geo_ohm_measurement_method=measurement_method,
    )

    series = FormationresistanceSeries.objects.filter(
        calculated_formationresistance=instance,
    ).first()

    if series is None:
        series = FormationresistanceSeries.objects.create(
            calculated_formationresistance=instance
        )

    for measurement_value in measurement_values:
        create_or_update_geo_record(measurement_value, series)


#### REVERSION
reversion.register(FormationResistanceDossier)
reversion.register(GeoOhmMeasurementMethod)
reversion.register(GeoOhmMeasurementValue)
