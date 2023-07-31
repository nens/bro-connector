from django.contrib import admin
from django.contrib import messages
from django.utils.translation import ngettext
from django import forms
from django.contrib.gis.geos import GEOSGeometry, LineString, Point


import os

from . import models
from bro_connector_gld.settings.base import GLD_AANLEVERING_SETTINGS

def _register(model, admin_class):
    admin.site.register(model, admin_class)


class DeliveredLocationsForm(forms.ModelForm):
    x = forms.CharField(required=True)
    y = forms.CharField(required=True)

    class Meta:
        model = models.DeliveredLocations
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Wijs de waarde toe aan het initial attribuut van het veld
        if self.instance.coordinates:
            self.fields['x'].initial = self.instance.x
            self.fields['y'].initial =  self.instance.y


class DeliveredLocationsAdmin(admin.ModelAdmin):

    form = DeliveredLocationsForm

    list_display = (
        "location_id",
        "groundwater_monitoring_well_id",
        "coordinates",
        "referencesystem",
        "horizontal_positioning_method",
    )


    fieldsets = [
        ('', {
            'fields': ['groundwater_monitoring_well', 
                       'referencesystem',
                        'horizontal_positioning_method',               
                       ],
        }),
        ('Coordinates', {
            'fields': ['x', 'y'],
        }),
    ]

    def save_model(self, request, obj, form, change):
        # Haal de waarden van de afgeleide attributen op uit het formulier
        x = form.cleaned_data['x']
        y = form.cleaned_data['y']

        # Werk de waarden van de afgeleide attributen bij in het model
        obj.coordinates = GEOSGeometry(f"POINT ({x} {y})", srid=28992)

        # Sla het model op
        obj.save()


class DeliveredVerticalPositionsAdmin(admin.ModelAdmin):

    list_display = (
        "vertical_position_id",
        "groundwater_monitoring_well_id",
        "local_vertical_reference_point",
        "offset",
        "vertical_datum",
        "ground_level_position",
        "ground_level_positioning_method",
    )


class GroundwaterMonitoringTubesAdmin(admin.ModelAdmin):

    list_display = (
        "groundwater_monitoring_tube_id",
        "groundwater_monitoring_well_id",
        "tube_number",
        "tube_type",
        "artesian_well_cap_present",
        "sediment_sump_present",
        "number_of_geo_ohm_cables",
        "tube_top_diameter",
        "variable_diameter",
        "tube_status",
        "tube_top_position",
        "tube_top_positioning_method",
        "tube_packing_material",
        "tube_material",
        "glue",
        "screen_length",
        "sock_material",
        "plain_tube_part_length",
        "sediment_sump_length",
        "deliver_to_bro",
    )
    list_filter = ("deliver_to_bro",)


class GroundwaterMonitoringWellsAdmin(admin.ModelAdmin):

    list_display = (
        "groundwater_monitoring_well_id",
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
        "number_of_standpipes",
        "ground_level_stable",
        "well_stability",
        "nitg_code",
        "olga_code",
        "well_code",
        "owner",
        "maintenance_responsible_party",
        "well_head_protector",
        "well_construction_date",
        "well_removal_date",
        "monitoring_pdok_id",
        "delivered_to_bro",
    )
    list_filter = ("well_construction_date", "delivered_to_bro")

_register(models.DeliveredLocations, DeliveredLocationsAdmin)
_register(models.DeliveredVerticalPositions, DeliveredVerticalPositionsAdmin)
_register(models.GroundwaterMonitoringTubes, GroundwaterMonitoringTubesAdmin)
_register(models.GroundwaterMonitoringWells, GroundwaterMonitoringWellsAdmin)