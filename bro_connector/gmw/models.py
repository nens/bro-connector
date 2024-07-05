from django.db import models
import django.contrib.gis.db.models as geo_models
from .choices import *
import main.utils.validators_models as validators_models
from bro.models import Organisation, BROProject, SecureCharField
import datetime
from .utils import generate_put_code

class GroundwaterMonitoringWellStatic(models.Model):
    groundwater_monitoring_well_static_id = models.AutoField(primary_key=True)
    registration_object_type = models.CharField(max_length=256, blank=True, null=True)
    bro_id = models.CharField(max_length=15, blank=True, null=True)
    project = models.ForeignKey(
        BROProject,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    request_reference = models.CharField(max_length=255, blank=True, null=True)
    delivery_accountable_party = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="delivery_accountable_party",
    )
    delivery_responsible_party = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="delivery_responsible_party",
    )
    quality_regime = models.CharField(choices=QUALITYREGIME, max_length=256, blank=True, null=True)
    under_privilege = models.CharField(choices=UNDERPRIVILIGE, max_length=256, blank=True, null=True)
    delivery_context = models.CharField(
        choices=DELIVERYCONTEXT, max_length=200, blank=True, null=True
    )
    construction_standard = models.CharField(
        choices=CONSTRUCTIONSTANDARD, max_length=200, blank=True, null=True
    )
    initial_function = models.CharField(
        choices=INITIALFUNCTION, max_length=200, blank=True, null=True
    )
    nitg_code = models.CharField(max_length=256, blank=True, null=True)
    olga_code = models.CharField(max_length=256, blank=True, null=True)
    well_code = models.CharField(max_length=256, blank=True, null=True)
    monitoring_pdok_id = models.IntegerField(blank=True, null=True)
    coordinates = geo_models.PointField(
        srid=28992, blank=True, null=True, editable=False
    )  # This field type is a guess.
    coordinates_4236 = geo_models.PointField(
        srid=4326, blank=True, null=True, editable=False, help_text="Passief veld. Vul deze niet in. Wordt automatisch berekend op basis van de RD coordinaten in het coordinates field."
    )
    reference_system = models.CharField(max_length=256, blank=True, null=True)
    horizontal_positioning_method = models.CharField(
        choices=HORIZONTALPOSITIONINGMETHOD, max_length=200, blank=True, null=True
    )
    local_vertical_reference_point = models.CharField(
        choices=LOCALVERTICALREFERENCEPOINT, max_length=200, blank=True, null=True
    )
    well_offset = models.FloatField(blank=True, null=True)
    vertical_datum = models.CharField(
        choices=VERTICALDATUM, max_length=200, blank=True, null=True
    )

    # Added for additional wells that are not owned by the user
    in_management = models.BooleanField(
        null=True, blank=True, default=True, editable=True
    )

    # Added for GMW delivery
    deliver_gmw_to_bro = models.BooleanField(
        blank=True, default=False
    )  # Should information of this well be delivered to the BRO
    complete_bro = models.BooleanField(
        blank=True, default=False
    )  # Is the data in the table complete as required for the BRO

    # Customization fields
    last_horizontal_positioning_date = models.DateField(blank=True, null=True)
    construction_coordinates = geo_models.PointField(
        srid=28992, blank=True, null=True, editable=False
    )  # This field type is a guess.

    @property
    def x(self):
        return self.coordinates.x
    @property
    def y(self):
        return self.coordinates.y
    
    @property
    def lat(self):
        return self.coordinates_4236.y
    @property
    def lon(self):
        return self.coordinates_4236.x

    @property
    def project_number(self):
        if self.project:
            return self.project.project_number
        else:
            None

    def cx(self):
        return self.construction_coordinates.x

    def cy(self):
        return self.construction_coordinates.y

    def __str__(self):
        if self.well_code:
            return str(self.well_code)
        elif self.bro_id:
            return str(self.bro_id)
        else:
            return str(self.groundwater_monitoring_well_static_id)

    def save(self, *args, **kwargs):
        # Call the parent class's save method
        super().save(*args, **kwargs)

        if self.well_code is None and self.nitg_code is not None:
            print("Generate wellcode.")
            self.well_code = generate_put_code(self.nitg_code)
            super().save(update_fields=['well_code'])

        # If coordinates are available, convert and save them to coordinates_4236
        if self.coordinates:
            self.coordinates_4236 = self.coordinates.transform(4326, clone=True)
            # Save the updated instance
            super().save(update_fields=['coordinates_4236'])
    
    class Meta:
        managed = True
        db_table = 'gmw"."groundwater_monitoring_well_static'
        verbose_name = "Grondwatermonitoring Put - Statisch"
        verbose_name_plural = "Grondwatermonitoring Putten - Statisch"


class GroundwaterMonitoringWellDynamic(models.Model):
    groundwater_monitoring_well_dynamic_id = models.AutoField(primary_key=True)
    groundwater_monitoring_well_static = models.ForeignKey(
        GroundwaterMonitoringWellStatic,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    date_from = models.DateTimeField(help_text="formaat: YYYY-MM-DD")
    ground_level_stable = models.CharField(choices=BOOLEAN_CHOICES, max_length=254, null=True, blank=True)
    well_stability = models.CharField(
        choices=WELLSTABILITY, max_length=200, blank=True, null=True
    )
    owner = models.IntegerField(blank=True, null=True)
    maintenance_responsible_party = models.IntegerField(blank=True, null=True)
    well_head_protector = models.CharField(
        choices=WELLHEADPROTECTOR, max_length=200, blank=True, null=True
    )
    ground_level_position = models.FloatField(
        blank=True, 
        null=True,
        validators=[validators_models.maaiveldhoogte_validation],
    )
    ground_level_positioning_method = models.CharField(
        choices=GROUNDLEVELPOSITIONINGMETHOD, max_length=200, blank=True, null=True
    )

    # CUSTOMIZATION FIELDS
    well_head_protector_subtype = models.CharField(
        max_length=254, choices=WELLHEADPROTECTOR_SUBTYPES, null=True, blank=True
    )
    lock = models.CharField(max_length=254, choices=LOCKS, null=True, blank=True)
    key = models.CharField(max_length=254, blank=True, null=True)
    place = models.CharField(max_length=254, null=True, blank=True)
    street = models.CharField(max_length=254, null=True, blank=True)
    location_description = models.CharField(max_length=254, null=True, blank=True)
    label = models.CharField(max_length=254, choices=LABELS, null=True, blank=True)
    foundation = models.CharField(
        max_length=254, choices=FOUNDATIONS, null=True, blank=True
    )
    collision_protection = models.CharField(
        max_length=254, choices=COLLISION_PROTECTION_TYPES, null=True, blank=True
    )
    remark = models.TextField(blank=True, null=True)

    def __str__(self):
        if self.date_till:
            till = self.date_till.date()
            return f"{self.groundwater_monitoring_well_static.__str__()} ({self.date_from.date()} - {till})"
        return f"{self.groundwater_monitoring_well_static.__str__()} ({self.date_from.date()} - Present)"

    @property
    def date_till(self):
        next_dynamic = GroundwaterMonitoringWellDynamic.objects.filter(
            groundwater_monitoring_well_static = self.groundwater_monitoring_well_static,
            date_from__gt = self.date_from
        ).order_by("date_from").first()

        if next_dynamic:
            return next_dynamic.date_from
        return None

    @property
    def number_of_standpipes(self):
        return GroundwaterMonitoringTubeStatic.objects.filter(
            groundwater_monitoring_well_static=self.groundwater_monitoring_well_static
        ).count()

    @property
    def deliver_gld_to_bro(self):
        return (
            GroundwaterMonitoringTubeStatic.objects.filter(
                deliver_gld_to_bro=True,
                groundwater_monitoring_well_static=self.groundwater_monitoring_well_static,
            ).count()
            > 0
        )

    class Meta:
        managed = True
        db_table = 'gmw"."groundwater_monitoring_well_dynamic'
        verbose_name = "Grondwatermonitoring Put - Dynamisch"
        verbose_name_plural = "Grondwatermonitoring Putten - Dynamisch"


class GroundwaterMonitoringTubeStatic(models.Model):
    groundwater_monitoring_tube_static_id = models.AutoField(primary_key=True)
    groundwater_monitoring_well_static = models.ForeignKey(
        GroundwaterMonitoringWellStatic,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    deliver_gld_to_bro = models.BooleanField(blank=True, default=False)
    tube_number = models.IntegerField(
        blank=True, null=True, validators=[validators_models.tube_number_validation]
    )
    tube_type = models.CharField(
        choices=TUBETYPE, max_length=200, blank=True, null=True
    )
    artesian_well_cap_present = models.CharField(choices=BOOLEAN_CHOICES, max_length=200, blank=True, null=True)
    sediment_sump_present = models.CharField(choices=BOOLEAN_CHOICES, max_length=200, blank=True, null=True)
    tube_material = models.CharField(
        choices=TUBEMATERIAL, max_length=200, blank=True, null=True
    )
    screen_length = models.FloatField(blank=True, null=True)
    sock_material = models.CharField(
        choices=SOCKMATERIAL, max_length=200, blank=True, null=True
    )
    sediment_sump_length = models.FloatField(
        blank=True, 
        null=True, 
        validators=[validators_models.zandvanglengte_validator]
    )

    @property
    def number_of_geo_ohm_cables(self):
        return GeoOhmCable.objects.filter(
            groundwater_monitoring_tube_static=self
        ).count()

    def __str__(self):
        if self.groundwater_monitoring_well_static:
            well = f"{self.groundwater_monitoring_well_static.__str__()}"
            return f"{well}-{format_integer(int(self.tube_number))}"
        return self.groundwater_monitoring_tube_static_id

    class Meta:
        managed = True
        db_table = 'gmw"."groundwater_monitoring_tube_static'
        verbose_name = "Grondwatermonitoring Filter - Statisch"
        verbose_name_plural = "Grondwatermonitoring Filters - Statisch"


class GroundwaterMonitoringTubeDynamic(models.Model):
    groundwater_monitoring_tube_dynamic_id = models.AutoField(primary_key=True)
    groundwater_monitoring_tube_static = models.ForeignKey(
        GroundwaterMonitoringTubeStatic,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    date_from = models.DateTimeField(help_text="formaat: YYYY-MM-DD")
    tube_top_diameter = models.IntegerField(blank=True, null=True)
    variable_diameter = models.CharField(choices=BOOLEAN_CHOICES, max_length=200, blank=True, null=True)
    tube_status = models.CharField(
        choices=TUBESTATUS, max_length=200, blank=True, null=True
    )
    tube_top_position = models.FloatField(
        blank=True, 
        null=True,
        validators=[validators_models.referentiehoogte_validation],
        help_text="Hoogte bovenkant buis. Eenheid: mNAP"
    )
    tube_top_positioning_method = models.CharField(
        choices=TUBETOPPOSITIONINGMETHOD, max_length=200, blank=True, null=True
    )
    tube_packing_material = models.CharField(
        choices=TUBEPACKINGMATERIAL, max_length=200, blank=True, null=True
    )
    glue = models.CharField(choices=GLUE, max_length=200, blank=True, null=True)
    plain_tube_part_length = models.FloatField(
        blank=True, null=True
    )  # Lengte stijbuisdeel
    inserted_part_diameter = models.FloatField(
        blank=True, 
        null=True, 
        validators=[validators_models.diameter_bovenkant_ingeplaatst_deel_validation],
    )  # This field type is a guess.
    inserted_part_length = models.FloatField(
        blank=True, 
        null=True,
        validators=[validators_models.lengte_ingeplaatst_deel_validation],
    )  # This field type is a guess.
    inserted_part_material = models.CharField(max_length=200, blank=True, null=True)

    @property
    def date_till(self):
        next_dynamic = GroundwaterMonitoringTubeDynamic.objects.filter(
            groundwater_monitoring_tube_static = self.groundwater_monitoring_tube_static,
            date_from__gt = self.date_from
        ).order_by("date_from").first()

        if next_dynamic:
            return next_dynamic.date_from
        return None

    @property
    def tube_inserted(self):
        if self.inserted_part_diameter or self.inserted_part_length or self.inserted_part_material:
            return True
        return False

    @property
    def screen_top_position(self):
        if self.tube_top_position is not None and self.plain_tube_part_length is not None:
            return self.tube_top_position - self.plain_tube_part_length
        return None

    @property
    def screen_bottom_position(self):
        if self.screen_top_position is not None and self.groundwater_monitoring_tube_static.screen_length is not None:
            return self.screen_top_position - self.groundwater_monitoring_tube_static.screen_length
        return None

    @property
    def tube_bottom_position(self):
        if self.screen_bottom_position is not None:
            if self.groundwater_monitoring_tube_static.sediment_sump_present:
                return self.screen_bottom_position 
            elif self.groundwater_monitoring_tube_static.sediment_sump_length is not None:
                return self.screen_bottom_position - self.groundwater_monitoring_tube_static.sediment_sump_length
        return None


    def __str__(self):
        if self.groundwater_monitoring_tube_static:
            if self.date_till:
                till = self.date_till.date()
                return f"{self.groundwater_monitoring_tube_static.__str__()} ({self.date_from.date()} - {till})"

            return f"{self.groundwater_monitoring_tube_static.__str__()} ({self.date_from.date()} - Present)"
        else:
            return self.groundwater_monitoring_tube_dynamic_id

    class Meta:
        managed = True
        db_table = 'gmw"."groundwater_monitoring_tube_dynamic'
        verbose_name = "Grondwatermonitoring Filter - Dynamisch"
        verbose_name_plural = "Grondwatermonitoring Filters - Dynamisch"


class GeoOhmCable(models.Model):
    geo_ohm_cable_id = models.AutoField(primary_key=True)
    groundwater_monitoring_tube_static = models.ForeignKey(
        GroundwaterMonitoringTubeStatic,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    cable_number = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"{self.groundwater_monitoring_tube_static}-K{self.cable_number}"

    @property
    def electrode_count(self):
        
        number_of_electrodes = ElectrodeStatic.objects.filter(geo_ohm_cable=self).count()
        # validators_models.aantal_elektrodes_validator(number_of_electrodes)
        if number_of_electrodes < 2:
            return "minimaal aantal elektrodes van 2 nog niet gelinkt aan Geo-ohmkabel"
        else:
            return number_of_electrodes

    class Meta:
        managed = True
        db_table = 'gmw"."geo_ohm_cable_static'
        verbose_name = "Geo Ohm Kabel"
        verbose_name_plural = "Geo Ohm Kabels"


class ElectrodeStatic(models.Model):
    electrode_static_id = models.AutoField(primary_key=True)
    geo_ohm_cable = models.ForeignKey(
        GeoOhmCable, on_delete=models.CASCADE, null=True, blank=True
    )
    electrode_packing_material = models.CharField(
        choices=ELECTRODEPACKINGMATERIAL, max_length=200, blank=True, null=True
    )
    electrode_position = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        validators=[validators_models.elektrodepositie_validator],
    )
    electrode_number = models.IntegerField(
        blank=True, null=True
    )

    def __str__(self):
        return f"{self.geo_ohm_cable.groundwater_monitoring_tube_static}-K{self.geo_ohm_cable.cable_number}E{self.electrode_number}"

    class Meta:
        managed = True
        db_table = 'gmw"."electrode_static'
        verbose_name = "Electrode - Statisch"
        verbose_name_plural = "Electrodes - Statisch"


class ElectrodeDynamic(models.Model):
    electrode_dynamic_id = models.AutoField(primary_key=True)
    electrode_static = models.ForeignKey(
        ElectrodeStatic, on_delete=models.CASCADE, null=True, blank=True
    )
    date_from = models.DateTimeField(help_text="formaat: YYYY-MM-DD")
    electrode_status = models.CharField(
        choices=ELECTRODESTATUS, max_length=200, blank=True, null=True
    )

    def __str__(self):
        if self.date_till:
            till = self.date_till.date()
            return str(f"{self.electrode_static.__str__()} ({self.date_from} - {till})")
        return str(f"{self.electrode_static.__str__()} ({self.date_from} - Present)")

    @property
    def date_till(self):
        next_dynamic = ElectrodeDynamic.objects.filter(
            electrode_static = self.electrode_static,
            date_from__gt = self.date_from
        ).order_by("date_from").first()

        if next_dynamic:
            return next_dynamic.date_from
        return None

    class Meta:
        managed = True
        db_table = 'gmw"."electrode_dynamic'
        verbose_name = "Electrode - Dynamisch"
        verbose_name_plural = "Electrodes - Dynamisch"


class Event(models.Model):
    change_id = models.AutoField(primary_key=True)
    event_name = models.CharField(
        choices=EVENTNAME, max_length=200, blank=True, null=True
    )
    event_date = models.DateField(
        null=True, 
        blank=True,
        help_text="Formaat: YYYY-MM-DD", 
        validators=[validators_models.datetime_validation],
    )
    groundwater_monitoring_well_static = models.ForeignKey(
        GroundwaterMonitoringWellStatic,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    groundwater_monitoring_well_dynamic = models.ForeignKey(
        GroundwaterMonitoringWellDynamic,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    groundwater_monitoring_tube_dynamic = models.ForeignKey(
        GroundwaterMonitoringTubeDynamic,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    electrode_dynamic = models.ForeignKey(
        ElectrodeDynamic, on_delete=models.CASCADE, null=True, blank=True
    )
    delivered_to_bro = models.BooleanField(blank=True, default=False)

    def __str__(self):
        return str(self.change_id)

    class Meta:
        managed = True
        db_table = 'gmw"."event'
        verbose_name = "Tussentijdse Gebeurtenis"
        verbose_name_plural = "Tussentijdse Gebeurtenissen"

def get_current_values(instance):
    """Get a dictionary of the current field values."""
    return {field.name: getattr(instance, field.name) for field in instance._meta.fields}

class gmw_registration_log(models.Model):
    date_modified = models.CharField(max_length=254, null=True, blank=True)
    bro_id = models.CharField(max_length=254, null=True, blank=True)
    event_id = models.CharField(max_length=254, null=True, blank=True)
    validation_status = models.CharField(max_length=254, null=True, blank=True)
    delivery_id = models.CharField(max_length=254, null=True, blank=True)
    delivery_type = models.CharField(
        choices=DELIVERY_TYPE_CHOICES,
        blank=False,
        max_length=40,
        default="register",
    )
    delivery_status = models.CharField(max_length=254, null=True, blank=True)
    comments = models.CharField(max_length=10000, null=True, blank=True)
    last_changed = models.CharField(max_length=254, null=True, blank=True)
    corrections_applied = models.BooleanField(blank=True, null=True)
    quality_regime = models.CharField(max_length=254, null=True, blank=True)
    file = models.CharField(max_length=254, null=True, blank=True)
    process_status = models.CharField(max_length=254, null=True, blank=True)

    # Could possibly be removed later
    object_id_accountable_party = models.CharField(
        max_length=254, null=True, blank=True
    )

    @property
    def event_type(self):
        if self.event_id is not None:
            return Event.objects.get(change_id=self.event_id).event_name
        return "-"

    def __str__(self):
        if self.bro_id is None:
            return f"{self.id}-{self.delivery_type}_log ({self.date_modified})"
        return f"{self.bro_id}-{self.delivery_type}_log ({self.date_modified})"

    def _set_original_values(self, instance):
        self._original_values = get_current_values(instance)

    def has_changed(self):
        """Check if any field has changed."""
        current_values = get_current_values(self)
        return any(current_values[field] != self._original_values[field] for field in current_values)

    def save(self, *args, **kwargs):
        if self.id is not None:
            db_instance = gmw_registration_log.objects.get(id=self.id)
            self._set_original_values(db_instance)

            if self.has_changed():
                # If there is any change
                self.last_changed = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        super().save(*args, **kwargs)


    class Meta:
        managed = True
        db_table = 'aanlevering"."gmw_registration_log'
        verbose_name = "GMW Synchronisatie Log"
        verbose_name_plural = "GMW Synchronisatie Logs"


class Picture(models.Model):
    picture_id = models.AutoField(primary_key=True)
    groundwater_monitoring_well_static = models.ForeignKey(
        GroundwaterMonitoringWellStatic,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    recording_date = models.DateField(blank=True, null=True)
    picture = models.BinaryField(blank=True, null=True, editable=True)
    description = models.CharField(max_length=254, null=True, blank=True)

    class Meta:
        managed = True
        db_table = 'gmw"."picture'
        verbose_name = "Foto"
        verbose_name_plural = "Fotos"


class MaintenanceParty(models.Model):
    maintenance_party_id = models.AutoField(primary_key=True)
    surname = models.CharField(max_length=100, null=True, blank=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    function = models.CharField(max_length=100, null=True, blank=True)
    organisation = models.CharField(max_length=100, null=True, blank=True)
    adress = models.CharField(max_length=254, null=True, blank=True)
    postal_code = models.CharField(max_length=50, null=True, blank=True)
    place = models.CharField(max_length=254, null=True, blank=True)
    phone = models.IntegerField(blank=True, null=True)
    mobilephone = models.IntegerField(null=True, blank=True)
    email = models.CharField(max_length=254, null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.surname}"

    class Meta:
        db_table = 'gmw"."maintenance_party'
        verbose_name = "Onderhoudsteam"
        verbose_name_plural = "Onderhoudsteams"


class Maintenance(models.Model):
    maintenance_id = models.AutoField(primary_key=True)
    groundwater_monitoring_well_static = models.ForeignKey(
        GroundwaterMonitoringWellStatic,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    groundwater_monitoring_tube_static = models.ForeignKey(
        GroundwaterMonitoringTubeStatic,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    notification_date = models.DateField(blank=True, null=True)
    kind_of_maintenance = models.CharField(max_length=254)
    description = models.CharField(max_length=254, null=True, blank=True)
    picture = models.ForeignKey(
        Picture, on_delete=models.SET_NULL, null=True, blank=True
    )
    reporter = models.ForeignKey(
        MaintenanceParty,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="Reporter",
    )  # Maintenance_party_id
    execution_date = models.DateField(blank=True, null=True)
    execution_by = models.ForeignKey(
        MaintenanceParty,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="Executioner",
    )  # Maintenance_party_id

    class Meta:
        managed = True
        db_table = 'gmw"."maintenance'
        verbose_name = "Onderhoudsmoment"
        verbose_name_plural = "Onderhoudsmomenten"

def format_integer(num):
    if num < 10:
        return f"00{num}"
    elif num < 100:
        return f"0{num}"
    else:
        return str(num)
