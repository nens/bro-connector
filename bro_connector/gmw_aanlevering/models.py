from django.db import models
from django.contrib.gis.db import models as geo_models

class GroundwaterMonitoringWellStatic(models.Model):
    groundwater_monitoring_well_static_id = models.AutoField(primary_key=True)
    registration_object_type = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    bro_id = models.CharField(max_length=15, blank=True, null=True)
    request_reference = models.CharField(max_length=255, blank=True, null=True)
    delivery_accountable_party = models.IntegerField(blank=True, null=True)
    delivery_responsible_party = models.IntegerField(blank=True, null=True)
    quality_regime = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    under_privilege = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    delivery_context = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    construction_standard = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    initial_function = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    nitg_code = models.CharField(max_length=256, blank=True, null=True)
    olga_code = models.CharField(max_length=256, blank=True, null=True)
    well_code = models.CharField(max_length=256, blank=True, null=True)
    monitoring_pdok_id = models.IntegerField(blank=True, null=True)
    coordinates = geo_models.PointField(srid=28992, blank=True, null=True, editable=False)  # This field type is a guess.
    reference_system = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    horizontal_positioning_method = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    local_vertical_reference_point = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    well_offset = models.DecimalField(max_digits=6, decimal_places=3, blank=True, null=True)
    vertical_datum = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.

    def x(self):
            return self.coordinates.x

    def y(self):
        return self.coordinates.y
    
    def __str__(self):
        return(self.bro_id)


    class Meta:
        managed = True
        db_table = 'gmw"."groundwater_monitoring_well_static'
        verbose_name_plural = "Groundwater monitoring wells (Static)"

class GroundwaterMonitoringWellDynamic(models.Model):
    groundwater_monitoring_well_dynamic_id = models.AutoField(primary_key=True)
    groundwater_monitoring_well = models.ForeignKey('GroundwaterMonitoringWellStatic', on_delete = models.CASCADE, null = True, blank = True)
    number_of_standpipes = models.IntegerField(blank=True, null=True)
    ground_level_stable = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    well_stability = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    owner = models.IntegerField(blank=True, null=True)
    maintenance_responsible_party = models.IntegerField(blank=True, null=True)
    well_head_protector = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    delivered_to_bro = models.BooleanField(blank=False, default=False)
    ground_level_position = models.DecimalField(
        max_digits=6, decimal_places=3, blank=True, null=True
    )
    ground_level_positioning_method = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.

    def __str__(self):
        return(self.bro_id)


    class Meta:
        managed = True
        db_table = 'gmw"."groundwater_monitoring_well_dynamic'
        verbose_name_plural = "Groundwater monitoring wells (Dynamic)"



class GroundwaterMonitoringTubesStatic(models.Model):
    groundwater_monitoring_tube_static_id = models.AutoField(primary_key=True)
    groundwater_monitoring_well = models.ForeignKey('GroundwaterMonitoringWellStatic', on_delete = models.CASCADE, null = True, blank = True)
    deliver_to_bro = models.BooleanField(blank=True, default=False)
    tube_number = models.IntegerField(blank=True, null=True)
    tube_type = models.TextField(blank=True, null=True)  # This field type is a guess.
    artesian_well_cap_present = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    sediment_sump_present = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    number_of_geo_ohm_cables = models.IntegerField(blank=True, null=True)
    tube_material = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    screen_length = models.DecimalField(
        max_digits=6, decimal_places=3, blank=True, null=True
    )
    sock_material = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    sediment_sump_length = models.DecimalField(
        max_digits=6, decimal_places=3, blank=True, null=True
    )

    def __str__(self):

        try:
            well = str(self.groundwater_monitoring_well.bro_id)
        except:
            well = 'Onbekend'

        return('{}, tube {}'.format(well , self.tube_number))

    class Meta:
        managed = True
        db_table = 'gmw"."groundwater_monitoring_tubes_static'
        verbose_name_plural = "Groundwater monitoring tubes (Static)"


class GroundwaterMonitoringTubesDynamic(models.Model):
    groundwater_monitoring_tube_dynamic_id = models.AutoField(primary_key=True)
    groundwater_monitoring_tube_static = models.ForeignKey('GroundwaterMonitoringTubesStatic', on_delete = models.CASCADE, null = True, blank = True)
    tube_top_diameter = models.IntegerField(blank=True, null=True)
    variable_diameter = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    tube_status = models.TextField(blank=True, null=True)  # This field type is a guess.
    tube_top_position = models.DecimalField(
        max_digits=6, decimal_places=3, blank=True, null=True
    )
    tube_top_positioning_method = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    tube_packing_material = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    glue = models.TextField(blank=True, null=True)  # This field type is a guess.
    plain_tube_part_length = models.DecimalField(
        max_digits=6, decimal_places=3, blank=True, null=True
    )
    inserted_part_diameter =  models.DecimalField(
        max_digits=6, decimal_places=3, blank=True, null=True
    ) # This field type is a guess.
    inserted_part_length =  models.DecimalField(
        max_digits=6, decimal_places=3, blank=True, null=True
    ) # This field type is a guess.
    inserted_part_material = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.

    def __str__(self):

        try:
            well = str(self.groundwater_monitoring_well.bro_id)
        except:
            well = 'Onbekend'

        return('{}, tube {}'.format(well , self.tube_number))

    class Meta:
        managed = True
        db_table = 'gmw"."groundwater_monitoring_tubes_dynamic'
        verbose_name_plural = "Groundwater monitoring tubes (Dynamic)"

class GeoOhmCable(models.Model):
    geo_ohm_cable_id = models.AutoField(primary_key=True)
    groundwater_monitoring_tube_static = models.ForeignKey('GroundwaterMonitoringTubesStatic', on_delete = models.CASCADE, null = True, blank = True)
    cable_number = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return(self.geo_ohm_cable_id)


    class Meta:
        managed = True
        db_table = 'gmw"."geo_ohm_cable_static'
        verbose_name_plural = "Geo Ohm Cable"

class ElectrodeStatic(models.Model):
    electrode_static_id = models.AutoField(primary_key=True)
    geo_ohm_cable = models.ForeignKey('GeoOhmCable', on_delete = models.CASCADE, null = True, blank = True)
    electrode_packing_material = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    electrode_positioning = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.

    def __str__(self):
        return(self.electrode_static_id)


    class Meta:
        managed = True
        db_table = 'gmw"."electrodes_static'
        verbose_name_plural = "Electrodes (Static)"

class ElectrodeDynamic(models.Model):
    electrode_dynamic_id = models.AutoField(primary_key=True)
    electrode_static = models.ForeignKey('ElectrodeStatic', on_delete = models.CASCADE, null = True, blank = True)
    electrode_number = models.IntegerField(blank=True, null=True)
    electrode_status = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.

    def __str__(self):
        return(self.electrode_dynamic_id)


    class Meta:
        managed = True
        db_table = 'gmw"."electrodes_dynamic'
        verbose_name_plural = "Electrodes (Dynamic)"

class Event(models.Model):
    change_id = models.AutoField(primary_key=True)
    event_name =  models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    event_date = models.DateTimeField(blank=True, null=True)
    groundwater_monitoring_well_static = models.ForeignKey('GroundwaterMonitoringWellStatic', on_delete = models.CASCADE, null = True, blank = True)
    groundwater_monitoring_well_dynamic = models.ForeignKey('GroundwaterMonitoringWellDynamic', on_delete = models.CASCADE, null = True, blank = True)
    groundwater_monitoring_well_tube_dynamic = models.ForeignKey('GroundwaterMonitoringTubesDynamic', on_delete = models.CASCADE, null = True, blank = True)   
    electrode_dynamic = models.ForeignKey('ElectrodeDynamic', on_delete = models.CASCADE, null = True, blank = True)


    def __str__(self):
        return(self.change_id)


    class Meta:
        managed = True
        db_table = 'gmw"."event'
        verbose_name_plural = "Events"