from django.contrib import admin
from django import forms
from django.contrib.gis.geos import GEOSGeometry

import os

from . import models

from main.settings.base import gmw_SETTINGS
from . import forms

def _register(model, admin_class):
    admin.site.register(model, admin_class)

class GroundwaterMonitoringWellStaticAdmin(admin.ModelAdmin):

    form = forms.GroundwaterMonitoringWellStaticForm

    list_display = (
        "groundwater_monitoring_well_static_id",
        "registration_object_type",
        "bro_id",
        "request_reference",
        "delivery_accountable_party",
        "delivery_responsible_party",
        "quality_regime",
        "under_privilege",
        "delivery_context",
        "construction_standard",
        "initial_function",
        "nitg_code",
        "olga_code",
        "well_code",
        "monitoring_pdok_id",
        "coordinates",
        "reference_system",
        "horizontal_positioning_method",
        "local_vertical_reference_point",
        "well_offset",
        "vertical_datum",
        "last_horizontal_positioning_date",
        "construction_coordinates",
        "in_management",
    )

    list_filter = ("delivery_accountable_party", "nitg_code", "in_management")

    fieldsets = [
        ('', {
            'fields': [        
                "registration_object_type",
                "bro_id",
                "request_reference",
                "delivery_accountable_party",
                "delivery_responsible_party",
                "quality_regime",
                "under_privilege",
                "delivery_context",
                "construction_standard",
                "initial_function",
                "nitg_code",
                "olga_code",
                "well_code",
                "monitoring_pdok_id",
                "horizontal_positioning_method",
                "local_vertical_reference_point",
                "well_offset",
                "vertical_datum",
                "last_horizontal_positioning_date",
                "in_management",
                        ],
        }),
        ('Coordinates', {
            'fields': ['x', 'y'],
        }),
        ('Construction Coordinates', {
            'fields': ['cx', 'cy'],
        }),
    ]

    def save_model(self, request, obj, form, change):
        # Haal de waarden van de afgeleide attributen op uit het formulier
        x = form.cleaned_data['x']
        y = form.cleaned_data['y']

        cx = form.cleaned_data['cx']
        cy = form.cleaned_data['cy']

        # Werk de waarden van de afgeleide attributen bij in het model
        obj.coordinates = GEOSGeometry(f"POINT ({x} {y})", srid=28992)
        if cx != '' and cy != '':
            obj.construction_coordinates = GEOSGeometry(f"POINT ({cx} {cy})", srid=28992)

        # Sla het model op
        obj.save()

class GroundwaterMonitoringWellDynamicAdmin(admin.ModelAdmin):

    form = forms.GroundwaterMonitoringWellDynamicForm

    list_display = (
        "groundwater_monitoring_well_dynamic_id",
        "groundwater_monitoring_well",
        "number_of_standpipes",
        "ground_level_stable",
        "well_stability",
        "owner",
        "maintenance_responsible_party",
        "well_head_protector",
        "deliver_gld_to_bro",
        "ground_level_position",
        "ground_level_positioning_method",
    )
    list_filter = ("groundwater_monitoring_well", "deliver_gld_to_bro", "owner")


class GroundwaterMonitoringTubesStaticAdmin(admin.ModelAdmin):

    form = forms.GroundwaterMonitoringTubesStaticForm
    
    list_display = (
        "groundwater_monitoring_tube_static_id",
        "groundwater_monitoring_well",
        "deliver_gld_to_bro",
        "tube_number",
        "tube_type",
        "artesian_well_cap_present",
        "sediment_sump_present",
        "number_of_geo_ohm_cables",
        "tube_material",
        "screen_length",
        "sock_material",
        "sediment_sump_length",
    )
    list_filter = ("deliver_gld_to_bro",)

class GroundwaterMonitoringTubesDynamicAdmin(admin.ModelAdmin):

    form = forms.GroundwaterMonitoringTubesDynamicForm
    
    list_display = (
        "groundwater_monitoring_tube_dynamic_id",
        "groundwater_monitoring_tube_static_id",
        "tube_top_diameter",
        "variable_diameter",
        "tube_status",
        "tube_top_position",
        "tube_top_positioning_method",
        "tube_packing_material",
        "glue",
        "plain_tube_part_length",
        "inserted_part_diameter",
        "inserted_part_length",
        "inserted_part_material",
    )
    list_filter = ("groundwater_monitoring_tube_static_id",)

class GeoOhmCableAdmin(admin.ModelAdmin):

    form = forms.GeoOhmCableForm
    
    list_display = (
        "geo_ohm_cable_id",
        "groundwater_monitoring_tube_static_id",
        "cable_number",
    )
    list_filter = ("groundwater_monitoring_tube_static_id",)

class ElectrodeStaticAdmin(admin.ModelAdmin):

    form = forms.ElectrodeStaticForm
    
    list_display = (
        "electrode_static_id",
        "geo_ohm_cable_id",
        "electrode_packing_material",
        "electrode_position",
    )
    list_filter = ("electrode_static_id",)

class ElectrodeDynamicAdmin(admin.ModelAdmin):

    form = forms.ElectrodeDynamicForm
    
    list_display = (
        "electrode_dynamic_id",
        "electrode_static_id",
        "electrode_number",
        "electrode_status",
    )
    list_filter = ("electrode_dynamic_id",)

class EventAdmin(admin.ModelAdmin):

    form = forms.EventForm
    
    list_display = (
        "change_id",
        "event_name",
        "event_date",
        "groundwater_monitoring_well_static",
        "groundwater_monitoring_well_tube_dynamic",
        "electrode_dynamic",
    )
    list_filter = ("change_id",)

class PictureAdmin(admin.ModelAdmin):

    list_display = (

    )
    list_filter = (
        "groundwater_monitoring_well",
        "recording_date",
    )

class MaintenancePartyAdmin(admin.ModelAdmin):

    list_display = (

    )
    list_filter = (
        'organisation',
        'postal_code',
        'function',
    )

class MaintenanceAdmin(admin.ModelAdmin):

    list_display = (

    )
    list_filter = (
        'kind_of_maintenance',
        'groundwater_monitoring_well',
        'execution_date',
        'reporter',
    )

# _register(models.GroundwaterMonitoringTubes, GroundwaterMonitoringTubesAdmin)
_register(models.GroundwaterMonitoringWellStatic, GroundwaterMonitoringWellStaticAdmin)
_register(models.GroundwaterMonitoringWellDynamic, GroundwaterMonitoringWellDynamicAdmin)
_register(models.GroundwaterMonitoringTubesStatic, GroundwaterMonitoringTubesStaticAdmin)
_register(models.GroundwaterMonitoringTubesDynamic, GroundwaterMonitoringTubesDynamicAdmin)
_register(models.GeoOhmCable, GeoOhmCableAdmin)
_register(models.ElectrodeStatic, ElectrodeStaticAdmin)
_register(models.ElectrodeDynamic, ElectrodeDynamicAdmin)
_register(models.Event, EventAdmin)
_register(models.Picture, PictureAdmin)
_register(models.MaintenanceParty, MaintenancePartyAdmin)
_register(models.Maintenance, MaintenanceAdmin)