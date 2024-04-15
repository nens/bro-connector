from django.db import models
import django.contrib.gis.db.models as geo_models
from .choices import *
import random


def get_color_value():
    # Generate random values for red, green, and blue components
    red = random.randint(0, 255)
    green = random.randint(0, 255)
    blue = random.randint(0, 255)

    # Convert decimal values to hexadecimal and format them
    color_code = "#{:02x}{:02x}{:02x}".format(red, green, blue)

    return color_code


class Instantie(models.Model):
    name = models.CharField(max_length=50, null=True, blank=True)
    company_number = models.IntegerField(blank=True)
    color = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        managed = True
        db_table = 'gmw"."instantie'
        verbose_name = "Instantie"
        verbose_name_plural = "Instanties"

    def __str__(self):
        if self.name:
            return self.name
        elif self.company_number:
            return self.company_number
        else:
            return self.id

    def save(self, *args, **kwargs):
        # Set a default color only if it's not already set
        if not self.color:
            self.color = get_color_value()
        super().save(*args, **kwargs)


class GroundwaterMonitoringWellStatic(models.Model):
    groundwater_monitoring_well_static_id = models.AutoField(primary_key=True)
    registration_object_type = models.CharField(max_length=256, blank=True, null=True)
    bro_id = models.CharField(max_length=15, blank=True, null=True)
    request_reference = models.CharField(max_length=255, blank=True, null=True)
    delivery_accountable_party = models.ForeignKey(
        Instantie,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="delivery_accountable_party",
    )
    delivery_responsible_party = models.ForeignKey(
        Instantie,
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

    def cx(self):
        return self.construction_coordinates.x

    def cy(self):
        return self.construction_coordinates.y

    def __str__(self):
        if self.bro_id:
            return str(self.bro_id)
        else:
            return str(self.groundwater_monitoring_well_static_id)

    def save(self, *args, **kwargs):
        # Call the parent class's save method
        super().save(*args, **kwargs)

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
    ground_level_stable = models.CharField(max_length=254, null=True, blank=True)
    well_stability = models.CharField(
        choices=WELLSTABILITY, max_length=200, blank=True, null=True
    )
    owner = models.IntegerField(blank=True, null=True)
    maintenance_responsible_party = models.IntegerField(blank=True, null=True)
    well_head_protector = models.CharField(
        choices=WELLHEADPROTECTOR, max_length=200, blank=True, null=True
    )
    ground_level_position = models.FloatField(blank=True, null=True)
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
    tube_number = models.IntegerField(blank=True, null=True)
    tube_type = models.CharField(
        choices=TUBETYPE, max_length=200, blank=True, null=True
    )
    artesian_well_cap_present = models.CharField(max_length=200, blank=True, null=True)
    sediment_sump_present = models.CharField(max_length=200, blank=True, null=True)
    tube_material = models.CharField(
        choices=TUBEMATERIAL, max_length=200, blank=True, null=True
    )
    screen_length = models.FloatField(blank=True, null=True)
    sock_material = models.CharField(
        choices=SOCKMATERIAL, max_length=200, blank=True, null=True
    )
    sediment_sump_length = models.FloatField(blank=True, null=True)

    @property
    def number_of_geo_ohm_cables(self):
        return GeoOhmCable.objects.filter(
            groundwater_monitoring_tube_static=self
        ).count()

    def __str__(self):
        well = f"{self.groundwater_monitoring_well_static.__str__()}"
        return f"{well}-{format_integer(self.tube_number)}"

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
    variable_diameter = models.CharField(max_length=200, blank=True, null=True)
    tube_status = models.CharField(
        choices=TUBESTATUS, max_length=200, blank=True, null=True
    )
    tube_top_position = models.FloatField(blank=True, null=True)
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
        blank=True, null=True
    )  # This field type is a guess.
    inserted_part_length = models.FloatField(
        blank=True, null=True
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
        return self.tube_top_position - self.plain_tube_part_length

    @property
    def screen_bottom_position(self):
        return self.screen_top_position - self.groundwater_monitoring_tube_static.screen_length
    
    @property
    def tube_bottom_position(self):
        if self.groundwater_monitoring_tube_static.sediment_sump_present:
            return self.screen_bottom_position 
        return self.screen_bottom_position - self.groundwater_monitoring_tube_static.sediment_sump_length

    def __str__(self):
        if self.date_till:
            till = self.date_till.date()
            return f"{self.groundwater_monitoring_tube_static.__str__()} ({self.date_from.date()} - {till})"

        return f"{self.groundwater_monitoring_tube_static.__str__()} ({self.date_from.date()} - Present)"

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
        return ElectrodeStatic.objects.filter(geo_ohm_cable=self).count()

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
    electrode_position = models.CharField(max_length=200, blank=True, null=True)
    electrode_number = models.IntegerField(blank=True, null=True)

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
        return str(self.electrode_static.electrode_static_id)

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
    event_date = models.CharField(max_length=254, blank=True, null=True)
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


class gmw_registration_log(models.Model):
    date_modified = models.CharField(max_length=254, null=True, blank=True)
    bro_id = models.CharField(max_length=254, null=True, blank=True)
    event_id = models.CharField(max_length=254, null=True, blank=True)
    validation_status = models.CharField(max_length=254, null=True, blank=True)
    levering_id = models.CharField(max_length=254, null=True, blank=True)
    levering_type = models.CharField(max_length=254, null=True, blank=True)
    levering_status = models.CharField(max_length=254, null=True, blank=True)
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

    def __str__(self):
        return f"{self.bro_id}-{self.levering_type}_log ({self.date_modified})"

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
    kind_of_maintenance = models.CharField(max_length=254, choices="")
    description = models.CharField(max_length=254, null=True, blank=True)
    picture = models.ForeignKey(
        Picture, on_delete=models.CASCADE, null=True, blank=True
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


class XMLImport(models.Model):
    id = models.AutoField(primary_key=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    file = models.FileField(upload_to=f"bulk", validators=[])
    report = models.TextField(
        help_text="process description",
        blank=True,
        null=True,
    )
    checked = models.BooleanField(
        help_text="checked",
        editable=False,
        default=False,
        blank=True,
        null=True,
    )
    imported = models.BooleanField(
        verbose_name="fully imported",
        default=False,
        editable=False,
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = "XML import"
        verbose_name_plural = "XML imports"


def format_integer(num):
    if num < 10:
        return f"00{num}"
    elif num < 100:
        return f"0{num}"
    else:
        return str(num)
