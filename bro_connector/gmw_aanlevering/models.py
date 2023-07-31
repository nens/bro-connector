from django.db import models
from django.contrib.gis.db import models as geo_models


class DeliveredLocations(models.Model):
    location_id = models.AutoField(primary_key=True)
    groundwater_monitoring_well = models.ForeignKey('GroundwaterMonitoringWells', on_delete = models.CASCADE, null = True, blank = True)
    #groundwater_monitoring_well_id = models.IntegerField(blank=True, null=True)
    coordinates = geo_models.PointField(srid=28992, blank=True, null=True, editable=False)  # This field type is a guess.
    referencesystem = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    horizontal_positioning_method = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.

    def x(self):
        return self.coordinates.x

    def y(self):
        return self.coordinates.y

    class Meta:
        managed = True
        db_table = 'gmw"."delivered_locations'
        verbose_name_plural = "Delivered locations"


class DeliveredVerticalPositions(models.Model):
    vertical_position_id = models.AutoField(primary_key=True)
    groundwater_monitoring_well = models.ForeignKey('GroundwaterMonitoringWells', on_delete = models.CASCADE, null = True, blank = True)
    #groundwater_monitoring_well_id = models.IntegerField(blank=True, null=True)
    local_vertical_reference_point = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    offset = models.DecimalField(max_digits=6, decimal_places=3, blank=True, null=True)
    vertical_datum = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    ground_level_position = models.DecimalField(
        max_digits=6, decimal_places=3, blank=True, null=True
    )
    ground_level_positioning_method = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.

    class Meta:
        managed = True
        db_table = 'gmw"."delivered_vertical_positions'
        verbose_name_plural = "Delivered vertical positions"


class GroundwaterMonitoringWells(models.Model):
    groundwater_monitoring_well_id = models.AutoField(primary_key=True)
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
    number_of_standpipes = models.IntegerField(blank=True, null=True)
    ground_level_stable = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    well_stability = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    nitg_code = models.CharField(max_length=256, blank=True, null=True)
    olga_code = models.CharField(max_length=256, blank=True, null=True)
    well_code = models.CharField(max_length=256, blank=True, null=True)
    owner = models.IntegerField(blank=True, null=True)
    maintenance_responsible_party = models.IntegerField(blank=True, null=True)
    well_head_protector = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    well_construction_date = models.DateField(blank=True, null=True)
    well_removal_date = models.DateField(blank=True, null=True)
    monitoring_pdok_id = models.IntegerField(blank=True, null=True)
    delivered_to_bro = models.BooleanField(blank=False, default=False)

    def __str__(self):
        return(self.bro_id)


    class Meta:
        managed = True
        db_table = 'gmw"."groundwater_monitoring_wells'
        verbose_name_plural = "Groundwater monitoring wells"


class GroundwaterMonitoringTubes(models.Model):
    groundwater_monitoring_tube_id = models.IntegerField(primary_key=True)
    groundwater_monitoring_well = models.ForeignKey('GroundwaterMonitoringWells', on_delete = models.CASCADE, null = True, blank = True)
    #groundwater_monitoring_well_id = models.IntegerField(blank=True, null=True)
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
    tube_material = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    glue = models.TextField(blank=True, null=True)  # This field type is a guess.
    screen_length = models.DecimalField(
        max_digits=6, decimal_places=3, blank=True, null=True
    )
    sock_material = models.TextField(
        blank=True, null=True
    )  # This field type is a guess.
    plain_tube_part_length = models.DecimalField(
        max_digits=6, decimal_places=3, blank=True, null=True
    )
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
        db_table = 'gmw"."groundwater_monitoring_tubes'
        verbose_name_plural = "Groundwater monitoring tubes"

