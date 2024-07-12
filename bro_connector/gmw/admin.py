from django.contrib import admin
from django.contrib.gis.geos import GEOSGeometry
from django.db.models import fields
import reversion
from reversion_compare.helpers import patch_admin 
import logging

from django.db import models

from . import models as gmw_models
import main.management.tasks.gmw_actions as gmw_actions
from . import forms as gmw_forms
from gmn.models import MeasuringPoint
from gmw.custom_filters import (
    WellFilter,
    WellDynamicFilter,
    TubeFilter,
    TubeDynamicFilter,
)
import main.utils.validators_admin as validators_admin
from main.utils.fieldform import FieldFormGenerator


logger = logging.getLogger(__name__)


def _register(model, admin_class):
    admin.site.register(model, admin_class)


def get_searchable_fields(model_class):
    return [
        f.name
        for f in model_class._meta.fields
        if isinstance(f, (fields.CharField, fields.AutoField))
    ]


class EventsInline(admin.TabularInline):
    model = gmw_models.Event
    search_fields = get_searchable_fields(gmw_models.Event)
    fields = (
        "event_name",
        "event_date",
    )
    show_change_link = True

    readonly_fields = (
        "groundwater_monitoring_well_static",
        "groundwater_monitoring_well_dynamic",
        "groundwater_monitoring_tube_dynamic",
        "electrode_dynamic",
        "delivered_to_bro",
    )

    extra = 0
    max_num = 0


class GroundwaterMonitoringWellStaticAdmin(admin.ModelAdmin):
    form = gmw_forms.GroundwaterMonitoringWellStaticForm
    change_form_template = "admin\change_form_well.html"

    search_fields = ("groundwater_monitoring_well_static_id", "well_code", "bro_id")

    list_display = (
        "groundwater_monitoring_well_static_id",
        "bro_id",
        "delivery_accountable_party",
        "initial_function",
        "nitg_code",
        "well_code",
        "coordinates",
        "in_management",
    )

    list_filter = (
        "delivery_accountable_party",
        "bro_id",
        "nitg_code",
        "well_code",
        "in_management",
    )
    readonly_fields = ('lat', 'lon',)

    fieldsets = [
        (
            "",
            {
                "fields": [
                    "registration_object_type",
                    "project",
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
                    "complete_bro",
                ],
            },
        ),
        (
            "Coordinates",
            {
                "fields": ["x", "y", "lat", "lon"],
            },
        ),
        (
            "Construction Coordinates",
            {
                "fields": ["cx", "cy"],
            },
        ),
    ]

    inlines = (EventsInline,)

    actions = ["deliver_to_bro", "check_status", "generate_fieldform"]

    def save_model(self, request, obj, form, change):
        # Haal de waarden van de afgeleide attributen op uit het formulier

        
        x = form.cleaned_data["x"]   
        y = form.cleaned_data["y"]
        
        cx = form.cleaned_data["cx"]
        cy = form.cleaned_data["cy"]

        # Werk de waarden van de afgeleide attributen bij in het model
        obj.coordinates = GEOSGeometry(f"POINT ({x} {y})", srid=28992)
        if cx != "" and cy != "":
            obj.construction_coordinates = GEOSGeometry(
                f"POINT ({cx} {cy})", srid=28992
            )   

        # Als er een put is met het obj id
        originele_put = gmw_models.GroundwaterMonitoringWellStatic.objects.filter(groundwater_monitoring_well_static_id=obj.groundwater_monitoring_well_static_id).first()
        
        # x- & y-coördinate check within dutch boundaries EPSG:28992
        (valid, message) = validators_admin.x_within_netherlands(obj)
        if valid is False:
            self.message_user(request, message, level="WARNING")
            if originele_put is not None:
                obj.coordinates[0] = originele_put.coordinates[0]
            else:
                obj.coordinates[0] = -999

        (valid, message) = validators_admin.y_within_netherlands(obj)
        if valid is False:
            self.message_user(request, message, level="WARNING")
            if originele_put is not None:
                obj.coordinates[1] = originele_put.coordinates[1]
            else:
                obj.coordinates[1] = -999
        
        # test if new coordinate is within distance from previous coordinates
        if originele_put is not None:          
            # .coordinates consist of x [0] and y [1]   
            (valid, message) = validators_admin.validate_x_coordinaat(obj)
            if valid is False:
                self.message_user(request, message, level="ERROR")
                obj.coordinates[0] = originele_put.coordinates[0]
            
            (valid, message) = validators_admin.validate_y_coordinaat(obj)
            if valid is False:
                self.message_user(request, message, level="ERROR")
                obj.coordinates[1] = originele_put.coordinates[1]


        
        # Sla het model op
        obj.save()

    @admin.action(description="Deliver GMW to BRO")
    def deliver_to_bro(self, request, queryset):
        for well in queryset:
            gmw_actions.check_and_deliver(well)

    @admin.action(description="Check GMW status from BRO")
    def check_status(self, request, queryset):
        for well in queryset:
            gmw_actions.check_status(well)

    @admin.action(description="Generate FRD FieldForm")
    def generate_fieldform(self, request, queryset):
        generator = FieldFormGenerator()
        generator.inputfields = ["weerstand", "opmerking"]
        generator.wells=queryset
        generator.generate()


class GroundwaterMonitoringWellDynamicAdmin(admin.ModelAdmin):
    form = gmw_forms.GroundwaterMonitoringWellDynamicForm
    search_fields = (
        "groundwater_monitoring_well_dynamic_id", "groundwater_monitoring_well_static__groundwater_monitoring_well_static_id",
        "groundwater_monitoring_well_static__bro_id", 
        "date_from", "groundwater_monitoring_well_static__well_code"
    )

    list_display = (
        "groundwater_monitoring_well_dynamic_id",
        "groundwater_monitoring_well_static",
        "date_from",
        "date_till",
        "number_of_standpipes",
        "owner",
        "well_head_protector",
        "ground_level_position",
        "deliver_gld_to_bro",
    )

    list_filter = (WellFilter, "owner")

    readonly_fields = ["number_of_standpipes", "deliver_gld_to_bro"]


    def save_model(self, request, obj, form, change):
        try:
            originele_meetpuntgeschiedenis = gmw_models.GroundwaterMonitoringWellDynamic.objects.get(
                groundwater_monitoring_well_static_id=obj.groundwater_monitoring_well_static_id
            )
        except:  # noqa: E722
            logger.exception("Bare except")
            originele_meetpuntgeschiedenis = None

        (valid, message) = validators_admin.validate_surface_height_ahn(obj)
        if valid is False:
            self.message_user(request, message, level="ERROR")
            if originele_meetpuntgeschiedenis is not None:
                obj.ground_level_position = originele_meetpuntgeschiedenis.ground_level_position

        obj.save()


class GroundwaterMonitoringTubeStaticAdmin(admin.ModelAdmin):
    form = gmw_forms.GroundwaterMonitoringTubeStaticForm

    search_fields = (
        "groundwater_monitoring_tube_static_id", "groundwater_monitoring_well_static__groundwater_monitoring_well_static_id",
        "groundwater_monitoring_well_static__bro_id", 
        "tube_number", "groundwater_monitoring_well_static__well_code"
    )


    list_display = (
        "groundwater_monitoring_tube_static_id",
        "groundwater_monitoring_well_static",
        "tube_number",
        "tube_type",
        "number_of_geo_ohm_cables",
        "tube_material",
        "screen_length",
        "sock_material",
        "sediment_sump_present",
        "sediment_sump_length",
        "deliver_gld_to_bro",
        "in_monitoring_net",
    )
    list_filter = (WellFilter, "deliver_gld_to_bro")

    readonly_fields = ["number_of_geo_ohm_cables", "in_monitoring_net"]

    actions = ["deliver_gld_to_true"]

    def in_monitoring_net(self, obj):
        return len(MeasuringPoint.objects.filter(
            groundwater_monitoring_tube = obj
        )) > 0

    def deliver_gld_to_true(self, request, queryset):
        for obj in queryset:
            with reversion.create_revision():
                obj.deliver_gld_to_bro = True
                obj.save()
                reversion.set_comment(
                    "Set deliver_gld_to_bro to True by manual action."
                )

    deliver_gld_to_true.short_description = "Deliver GLD to True"


class GroundwaterMonitoringTubeDynamicAdmin(admin.ModelAdmin):
    form = gmw_forms.GroundwaterMonitoringTubeDynamicForm
    search_fields = (
        "groundwater_monitoring_tube_dynamic_id", "groundwater_monitoring_tube_static__groundwater_monitoring_well_static__groundwater_monitoring_well_static_id",
        "groundwater_monitoring_tube_static__groundwater_monitoring_well_static__bro_id",
        "groundwater_monitoring_tube_static__tube_number", "date_from",
        "groundwater_monitoring_tube_static__groundwater_monitoring_well_static__well_code"
    )
    list_display = (
        "groundwater_monitoring_tube_dynamic_id",
        "groundwater_monitoring_tube_static",
        "date_from",
        "date_till",
        "tube_top_diameter",
        "variable_diameter",
        "tube_status",
        "tube_top_position",
        "plain_tube_part_length",
    )
    list_filter = (TubeFilter,)

    readonly_fields =["screen_top_position", "screen_bottom_position"]

    def save_model(self, request, obj, form, change):
        try:
            originele_filtergeschiedenis = gmw_models.GroundwaterMonitoringTubeDynamic.objects.get(
                groundwater_monitoring_tube_dynamic_id=obj.groundwater_monitoring_tube_dynamic_id
            )
        except:  # noqa: E722
            message = "Er bestaat geen historie voor het filter"
            self.message_user(request, message, level="ERROR")
            originele_filtergeschiedenis = None

        # TODO validate_logger_depth_filter
        
        (valid, message) = validators_admin.validate_reference_height(obj)
        if valid is False:
            self.message_user(request, message, level="ERROR")
            if originele_filtergeschiedenis is not None:
                obj.screen_top_position = originele_filtergeschiedenis.screen_top_position

        (valid, message) = validators_admin.validate_reference_height_ahn(obj)
        if valid is False:
            self.message_user(request, message, level="ERROR")

        obj.save()

class GeoOhmCableAdmin(admin.ModelAdmin):
    form = gmw_forms.GeoOhmCableForm

    list_display = (
        "geo_ohm_cable_id",
        "groundwater_monitoring_tube_static",
        "cable_number",
        # "electrode_count",
    )

    readonly_fields =["electrode_count"]

    list_filter = (WellFilter,)


class ElectrodeStaticAdmin(admin.ModelAdmin):
    form = gmw_forms.ElectrodeStaticForm

    list_display = (
        "electrode_static_id",
        "geo_ohm_cable",
        "electrode_number",
        "electrode_packing_material",
        "electrode_position",
    )
    list_filter = ("electrode_static_id", "geo_ohm_cable")


class ElectrodeDynamicAdmin(admin.ModelAdmin):
    form = gmw_forms.ElectrodeDynamicForm
    search_fields = (
        "electrode_dynamic_id", "electrode_static__geo_ohm_cable__groundwater_monitoring_tube_static__groundwater_monitoring_well_static__groundwater_monitoring_well_static_id",
        "electrode_static__geo_ohm_cable__groundwater_monitoring_tube_static__groundwater_monitoring_well_static__bro_id", 
        "date_from", "electrode_static__geo_ohm_cable__groundwater_monitoring_tube_static__groundwater_monitoring_well_static__well_code"
    )

    list_display = (
        "electrode_dynamic_id",
        "electrode_static",
        "date_from",
        "date_till",
        "electrode_status",
    )
    list_filter = ("electrode_dynamic_id", "electrode_static")


class EventAdmin(admin.ModelAdmin):
    form = gmw_forms.EventForm

    list_display = (
        "change_id",
        "event_name",
        "groundwater_monitoring_well_static",
        "groundwater_monitoring_well_dynamic",
        "groundwater_monitoring_tube_dynamic",
        "electrode_dynamic",
    )
    list_filter = (
        "change_id",
        WellFilter,
        "event_name",
    )
    ordering = ['-change_id'] 
    autocomplete_fields = (
        "groundwater_monitoring_well_static",
        "groundwater_monitoring_well_dynamic",
        "groundwater_monitoring_tube_dynamic",
        "electrode_dynamic",
    )


class PictureAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.BinaryField: {"widget": gmw_forms.BinaryFileInput()},
    }

    list_display = (
        "groundwater_monitoring_well_static",
        "recording_date",
    )
    list_filter = (
        WellFilter,
        "recording_date",
    )


class MaintenancePartyAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "surname",
        "function",
        "organisation",
    )

    search_fields = get_searchable_fields(gmw_models.MaintenanceParty)


class MaintenanceAdmin(admin.ModelAdmin):
    list_display = (
        "kind_of_maintenance",
        "groundwater_monitoring_well_static",
        "reporter",
        "execution_date",
        "execution_by",
    )
    list_filter = (
        "kind_of_maintenance",
        WellFilter,
        "execution_date",
        "reporter",
        "execution_by",
    )


class GmwSyncLogAdmin(admin.ModelAdmin):
    list_display = (
        "date_modified",
        "last_changed",
        "bro_id",
        "event_type",
        "process_status",
        "comments",
    )
    list_filter = ("bro_id",)

    readonly_fields = (
        "date_modified",
        "bro_id",
        "event_id",
        "validation_status",
        "delivery_id",
        "delivery_type",
        "delivery_status",
        "comments",
        "last_changed",
        "corrections_applied",
        "quality_regime",
        "file",
        "process_status",
        "object_id_accountable_party"
    )


_register(
    gmw_models.GroundwaterMonitoringWellStatic, GroundwaterMonitoringWellStaticAdmin
)
_register(
    gmw_models.GroundwaterMonitoringWellDynamic, GroundwaterMonitoringWellDynamicAdmin
)
_register(
    gmw_models.GroundwaterMonitoringTubeStatic, GroundwaterMonitoringTubeStaticAdmin
)
_register(
    gmw_models.GroundwaterMonitoringTubeDynamic, GroundwaterMonitoringTubeDynamicAdmin
)
_register(gmw_models.GeoOhmCable, GeoOhmCableAdmin)
_register(gmw_models.ElectrodeStatic, ElectrodeStaticAdmin)
_register(gmw_models.ElectrodeDynamic, ElectrodeDynamicAdmin)
_register(gmw_models.Event, EventAdmin)
_register(gmw_models.Picture, PictureAdmin)
_register(gmw_models.MaintenanceParty, MaintenancePartyAdmin)
_register(gmw_models.Maintenance, MaintenanceAdmin)
_register(gmw_models.gmw_registration_log, GmwSyncLogAdmin)

patch_admin(gmw_models.GroundwaterMonitoringWellStatic)
patch_admin(gmw_models.GroundwaterMonitoringWellDynamic)
patch_admin(gmw_models.GroundwaterMonitoringTubeStatic)
patch_admin(gmw_models.GroundwaterMonitoringTubeDynamic)
patch_admin(gmw_models.GeoOhmCable)
patch_admin(gmw_models.ElectrodeStatic)
patch_admin(gmw_models.ElectrodeDynamic)
patch_admin(gmw_models.Event)
patch_admin(gmw_models.Picture)
patch_admin(gmw_models.MaintenanceParty)
patch_admin(gmw_models.Maintenance)
patch_admin(gmw_models.gmw_registration_log)