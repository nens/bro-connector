from django.db import models
from django.contrib.gis.db import models as geo_models
from .choices import *


class GroundwaterMonitoringWellStatic(models.Model):
    groundwater_monitoring_well_static_id = models.AutoField(primary_key=True)
    registration_object_type = models.CharField(max_length=256, blank=True, null=True)
    bro_id = models.CharField(max_length=15, blank=True, null=True)
    request_reference = models.CharField(max_length=255, blank=True, null=True)
    delivery_accountable_party = models.IntegerField(blank=True, null=True)
    delivery_responsible_party = models.IntegerField(blank=True, null=True)
    quality_regime = models.CharField(max_length=256, blank=True, null=True)
    under_privilege = models.CharField(max_length=256, blank=True, null=True)
    delivery_context = models.CharField(
        choices=DELIVERYCONTEXT,
        max_length=200,
        blank=True, null=True
    ) 
    construction_standard = models.CharField(
        choices=CONSTRUCTIONSTANDARD,
        max_length=200,
        blank=True, null=True
    ) 
    initial_function = models.CharField(
        choices=INITIALFUNCTION,
        max_length=200,
        blank=True, null=True
    ) 
    nitg_code = models.CharField(max_length=256, blank=True, null=True)
    olga_code = models.CharField(max_length=256, blank=True, null=True)
    well_code = models.CharField(max_length=256, blank=True, null=True)
    monitoring_pdok_id = models.IntegerField(blank=True, null=True)
    coordinates = geo_models.PointField(srid=28992, blank=True, null=True, editable=False)  # This field type is a guess.
    reference_system = models.CharField(max_length=256, blank=True, null=True)
    horizontal_positioning_method = models.CharField(
        choices=HORIZONTALPOSITIONINGMETHOD,
        max_length=200,
        blank=True, null=True
    ) 
    local_vertical_reference_point = models.CharField(
        choices=LOCALVERTICALREFERENCEPOINT,
        max_length=200,
        blank=True, null=True
    ) 
    well_offset = models.DecimalField(max_digits=6, decimal_places=3, blank=True, null=True)
    vertical_datum = models.CharField(
        choices=VERTICALDATUM,
        max_length=200,
        blank=True, null=True
    ) 

    # Added for additional wells that are not owned by the user
    in_management = models.BooleanField(null=True, blank=True, default=True, editable=True)

    # Added for GMW delivery
    deliver_gmw_to_bro = models.BooleanField(blank=True, default=False) # Should information of this well be delivered to the BRO
    complete_bro = models.BooleanField(blank=True, default=False) # Is the data in the table complete as required for the BRO
    

    # Customization fields
    last_horizontal_positioning_date = models.DateField(blank=True, null=True)
    construction_coordinates = geo_models.PointField(srid=28992, blank=True, null=True, editable=False)  # This field type is a guess.
    
    def x(self):
            return self.coordinates.x

    def y(self):
        return self.coordinates.y
    
    def cx(self):
        return self.construction_coordinates.x
    
    def cy(self):
        return self.construction_coordinates.y
    
    def __str__(self):
        return(str(self.bro_id))

    class Meta:
        managed = True
        db_table = 'gmw"."groundwater_monitoring_well_static'
        verbose_name = "Grondwatermonitoring Put - Statische gegevens"
        verbose_name_plural = "Grondwatermonitoring Putten - Statische gegevens"

class GroundwaterMonitoringWellDynamic(models.Model):
    groundwater_monitoring_well_dynamic_id = models.AutoField(primary_key=True)
    groundwater_monitoring_well = models.ForeignKey('GroundwaterMonitoringWellStatic', on_delete = models.CASCADE, null = True, blank = True)
    number_of_standpipes = models.IntegerField(blank=True, null=True)
    ground_level_stable = models.CharField(max_length=254, null=True, blank=True)
    well_stability = models.CharField(
        choices=WELLSTABILITY,
        max_length=200,
        blank=True, null=True
    ) 
    owner = models.IntegerField(blank=True, null=True)
    maintenance_responsible_party = models.IntegerField(blank=True, null=True)
    well_head_protector = models.CharField(
        choices=WELLHEADPROTECTOR,
        max_length=200,
        blank=True, null=True
    ) 
    deliver_gld_to_bro = models.BooleanField(blank=False, default=False)
    ground_level_position = models.DecimalField(
        max_digits=6, decimal_places=3, blank=True, null=True
    )
    ground_level_positioning_method = models.CharField(
        choices=GROUNDLEVELPOSITIONINGMETHOD,
        max_length=200,
        blank=True, null=True
    ) 


    # CUSTOMIZATION FIELDS
    well_head_protector_subtype = models.CharField(
        max_length=254, 
        choices=WELLHEADPROTECTOR_SUBTYPES,
        null=True,
        blank=True
    )
    lock = models.CharField(
        max_length=254, 
        choices=LOCKS,
        null=True,
        blank=True
    )
    key = models.CharField(max_length=254, blank=True, null=True)
    place = models.CharField(max_length=254, null=True, blank=True)
    street = models.CharField(max_length=254, null=True, blank=True)
    location_description = models.CharField(max_length=254, null=True, blank=True)
    label = models.CharField(
        max_length=254, 
        choices=LABELS,
        null=True,
        blank=True
    )
    foundation = models.CharField(
        max_length=254, 
        choices=FOUNDATIONS,
        null=True,
        blank=True
    )
    collision_protection = models.CharField(
        max_length=254, 
        choices=COLLISION_PROTECTION_TYPES,
        null=True,
        blank=True
    )
    remark = models.TextField(
        blank=True, null=True
    )

    def __str__(self):
        return(str(self.groundwater_monitoring_well.bro_id))


    class Meta:
        managed = True
        db_table = 'gmw"."groundwater_monitoring_well_dynamic'
        verbose_name = "Grondwatermonitoring Put - Dynamische gegevens"
        verbose_name_plural = "Grondwatermonitoring Putten - Dynamische gegevens"



class GroundwaterMonitoringTubesStatic(models.Model):
    groundwater_monitoring_tube_static_id = models.AutoField(primary_key=True)
    groundwater_monitoring_well = models.ForeignKey('GroundwaterMonitoringWellStatic', on_delete = models.CASCADE, null = True, blank = True)
    deliver_gld_to_bro = models.BooleanField(blank=True, default=False)
    tube_number = models.IntegerField(blank=True, null=True)
    tube_type = models.CharField(
        choices=TUBETYPE,
        max_length=200,
        blank=True, null=True
    ) 
    artesian_well_cap_present = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    sediment_sump_present = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    number_of_geo_ohm_cables = models.IntegerField(blank=True, null=True)
    tube_material = models.CharField(
        choices=TUBEMATERIAL,
        max_length=200,
        blank=True, null=True
    ) 
    screen_length = models.DecimalField(
        max_digits=6, decimal_places=3, blank=True, null=True
    )
    sock_material = models.CharField(
        choices=SOCKMATERIAL,
        max_length=200,
        blank=True, null=True
    ) 
    sediment_sump_length = models.DecimalField(
        max_digits=6, decimal_places=3, blank=True, null=True
    )

    @property
    def screen_top_position(self):
        return self.tube_top_position - self.plain_tube_part_length
    
    @property
    def screen_bottom_position(self):
        return self.tube_top_position - (self.plain_tube_part_length + self.groundwater_monitoring_tube_static.screen_length)

    def __str__(self):

        try:
            well = str(self.groundwater_monitoring_well.bro_id)
        except:
            well = 'Onbekend'

        return('{}, tube {}'.format(well , self.tube_number))

    class Meta:
        managed = True
        db_table = 'gmw"."groundwater_monitoring_tubes_static'
        verbose_name = "Grondwatermonitoring Filter - Statische gegevens"
        verbose_name_plural = "Grondwatermonitoring Filters - Statische gegevens"


class GroundwaterMonitoringTubesDynamic(models.Model):
    groundwater_monitoring_tube_dynamic_id = models.AutoField(primary_key=True)
    groundwater_monitoring_tube_static = models.ForeignKey('GroundwaterMonitoringTubesStatic', on_delete = models.CASCADE, null = True, blank = True)
    tube_top_diameter = models.IntegerField(blank=True, null=True)
    variable_diameter = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    tube_status = models.CharField(
        choices=TUBESTATUS,
        max_length=200,
        blank=True, null=True
    ) 
    tube_top_position = models.DecimalField(
        max_digits=6, decimal_places=3, blank=True, null=True
    )
    tube_top_positioning_method = models.CharField(
        choices=TUBETOPPOSITIONINGMETHOD,
        max_length=200,
        blank=True, null=True
    ) 
    tube_packing_material = models.CharField(
        choices=TUBEPACKINGMATERIAL,
        max_length=200,
        blank=True, null=True
    ) 
    glue = models.CharField(
        choices=GLUE,
        max_length=200,
        blank=True, null=True
    ) 
    plain_tube_part_length = models.DecimalField(
        max_digits=6, decimal_places=3, blank=True, null=True
    )
    inserted_part_diameter =  models.DecimalField(
        max_digits=6, decimal_places=3, blank=True, null=True
    ) # This field type is a guess.
    inserted_part_length =  models.DecimalField(
        max_digits=6, decimal_places=3, blank=True, null=True
    ) # This field type is a guess.
    inserted_part_material = models.CharField(
        max_length=200,
        blank=True, null=True
    ) 

    def __str__(self):

        try:
            well = str(self.groundwater_monitoring_well.bro_id)
        except:
            well = 'Onbekend'

        return('{}, tube {}'.format(well , self.groundwater_monitoring_tube_static.tube_number))

    class Meta:
        managed = True
        db_table = 'gmw"."groundwater_monitoring_tubes_dynamic'
        verbose_name = "Grondwatermonitoring Filter - Dynamische gegevens"
        verbose_name_plural = "Grondwatermonitoring Filters - Dynamische gegevens"

class GeoOhmCable(models.Model):
    geo_ohm_cable_id = models.AutoField(primary_key=True)
    groundwater_monitoring_tube_static = models.ForeignKey('GroundwaterMonitoringTubesStatic', on_delete = models.CASCADE, null = True, blank = True)
    cable_number = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return(str(self.geo_ohm_cable_id))

    @property
    def electrode_count(self):
        return ElectrodeStatic.objects.filter(geo_ohm_cable = self).count()

    class Meta:
        managed = True
        db_table = 'gmw"."geo_ohm_cable_static'
        verbose_name = "Geo Ohm Kabel"
        verbose_name_plural = "Geo Ohm Kabels"

class ElectrodeStatic(models.Model):
    electrode_static_id = models.AutoField(primary_key=True)
    geo_ohm_cable = models.ForeignKey('GeoOhmCable', on_delete = models.CASCADE, null = True, blank = True)
    electrode_packing_material = models.CharField(
        choices=ELECTRODEPACKINGMATERIAL,
        max_length=200,
        blank=True, null=True
    ) 
    electrode_position = models.CharField(
        max_length=200,
        blank=True, null=True
    ) 

    def __str__(self):
        return(str(self.electrode_static_id))


    class Meta:
        managed = True
        db_table = 'gmw"."electrodes_static'
        verbose_name = "Electrode - Statische gegevens"
        verbose_name_plural = "Electrodes - Statische gegevens"

class ElectrodeDynamic(models.Model):
    electrode_dynamic_id = models.AutoField(primary_key=True)
    electrode_static = models.ForeignKey('ElectrodeStatic', on_delete = models.CASCADE, null = True, blank = True)
    electrode_number = models.IntegerField(blank=True, null=True) # Is het niet gek dat dit nummer in de dynamic staat? Aanpassen zal voor problemen zorgen in de toekomst met FRD.
    electrode_status = models.CharField(
        choices=ELECTRODESTATUS,
        max_length=200,
        blank=True, null=True
    ) 

    def __str__(self):
        return(str(self.electrode_static.electrode_static_id))


    class Meta:
        managed = True
        db_table = 'gmw"."electrodes_dynamic'
        verbose_name = "Electrode - Dynamische gegevens"
        verbose_name_plural = "Electrodes - Dynamische gegevens"

class Event(models.Model):
    change_id = models.AutoField(primary_key=True)
    event_name =  models.CharField(
        choices=EVENTNAME,
        max_length=200,
        blank=True, null=True
    ) 
    event_date = models.CharField(max_length=254, blank=True, null=True)
    groundwater_monitoring_well_static = models.ForeignKey('GroundwaterMonitoringWellStatic', on_delete = models.CASCADE, null = True, blank = True)
    groundwater_monitoring_well_dynamic = models.ForeignKey('GroundwaterMonitoringWellDynamic', on_delete = models.CASCADE, null = True, blank = True)
    groundwater_monitoring_well_tube_dynamic = models.ForeignKey('GroundwaterMonitoringTubesDynamic', on_delete = models.CASCADE, null = True, blank = True)   
    electrode_dynamic = models.ForeignKey('ElectrodeDynamic', on_delete = models.CASCADE, null = True, blank = True)
    delivered_to_bro = models.BooleanField(blank = True, default = False)


    def __str__(self):
        return(str(self.change_id))


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
    object_id_accountable_party = models.CharField(max_length=254, null=True, blank=True)

    class Meta:
        db_table = 'aanlevering"."gmw_registration_log'
        verbose_name = "GMW Synchronisatie Log"
        verbose_name_plural = "GMW Synchronisatie Logs"


class Picture(models.Model):
    picture_id = models.AutoField(primary_key=True)
    groundwater_monitoring_well = models.ForeignKey('GroundwaterMonitoringWellStatic', on_delete = models.CASCADE, null = True, blank = True)
    recording_date = models.DateField(blank=True, null=True)
    picture = models.CharField(max_length=254, null=True, blank=True)
    description = models.CharField(max_length=254, null=True, blank=True)

    class Meta:
        db_table = 'gmw"."pictures'
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

    class Meta:
        db_table = 'gmw"."maintenance_party'
        verbose_name = 'Onderhoudsteam'
        verbose_name_plural = 'Onderhoudsteams'

class Maintenance(models.Model):
    maintenance_id = models.AutoField(primary_key=True)
    groundwater_monitoring_well = models.ForeignKey('GroundwaterMonitoringWellStatic', on_delete = models.CASCADE, null = True, blank = True)
    groundwater_monitoring_tube = models.ForeignKey('GroundwaterMonitoringTubesStatic', on_delete = models.CASCADE, null = True, blank = True)
    notification_date = models.DateField(blank=True, null=True)
    kind_of_maintenance = models.CharField(
        max_length=254, choices=''
    )
    description = models.CharField(max_length=254, null=True, blank=True)
    picture = models.ForeignKey('Picture', on_delete = models.CASCADE, null = True, blank = True)
    reporter = models.IntegerField(blank=True, null=True) # Maintenance_party_id 
    execution_date = models.DateField(blank=True, null=True)
    execution_by = models.IntegerField(blank=True, null=True) # Maintenance_party_id

    class Meta:
        db_table = 'gmw"."maintenance'
        verbose_name = 'Onderhoudsmoment'
        verbose_name_plural = 'Onderhoudsmomenten'