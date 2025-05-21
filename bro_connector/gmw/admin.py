from django.contrib import admin, messages
from django.contrib.gis.geos import GEOSGeometry
from django.db.models import fields
import reversion
from reversion_compare.helpers import patch_admin
import logging


from . import models as gmw_models
from gld.models import GroundwaterLevelDossier
import gmw.management.tasks.gmw_actions as gmw_actions
from . import forms as gmw_forms
from gmn.models import MeasuringPoint
from gmw.custom_filters import (
    WellFilter,
    TubeFilter,
    EventTypeFilter,
)
import main.utils.validators_admin as validators_admin
from main.utils.frd_fieldform import FieldFormGenerator

from .bro_validators import (
    validate_well_static,
    validate_well_dynamic,
    validate_tube_static,
    validate_tube_dynamic,
    validate_geo_ohm_cable,
    validate_electrode,
)
from .bro_validators.well_validation import WellValidation


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
    show_change_link = True
    search_fields = get_searchable_fields(gmw_models.Event)
    fields = (
        "event_name",
        "event_date",
        "delivered_to_bro",
        "bro_actions",
    )

    ordering = ["event_date"]
    readonly_fields = ["delivered_to_bro", "bro_actions"]

    extra = 0
    max_num = 0

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.in_management is False:
            return (
                "event_name",
                "event_date",
                "delivered_to_bro",
                "bro_actions",
            )
        return []

    def has_add_permission(self, request, obj=None):
        if obj and obj.in_management is False:
            return False
        return True

    def has_change_permission(self, request, obj=None):
        if obj and obj.in_management is False:
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        if obj and obj.in_management is False:
            return False
        return True


class PicturesInline(admin.TabularInline):
    model = gmw_models.Picture
    form = gmw_forms.PictureForm

    fields = ("picture", "recording_datetime", "description")

    ordering = ["-recording_datetime"]
    readonly_fields = []

    extra = 1
    max_num = None

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.in_management is False:
            return ("picture", "recording_datetime", "description")
        return []

    def has_add_permission(self, request, obj=None):
        if obj and obj.in_management is False:
            return False
        return True

    def has_change_permission(self, request, obj=None):
        if obj and obj.in_management is False:
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        if obj and obj.in_management is False:
            return False
        return True


class WellDynamicInline(admin.TabularInline):
    model = gmw_models.GroundwaterMonitoringWellDynamic
    show_change_link = True
    search_fields = get_searchable_fields(gmw_models.GroundwaterMonitoringWellDynamic)
    fields = (
        "date_from",
        "date_till",
        "well_head_protector",
        "ground_level_position",
        "ground_level_positioning_method",
        "number_of_standpipes",
        "comment",
    )
    ordering = ["date_from"]
    readonly_fields = ["date_from", "date_till", "number_of_standpipes", "comment"]

    extra = 0
    max_num = 0

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.in_management is False:
            return (
                "date_from",
                "date_till",
                "well_head_protector",
                "ground_level_position",
                "ground_level_positioning_method",
                "number_of_standpipes",
                "comment",
            )
        return []

    def has_add_permission(self, request, obj=None):
        if obj and obj.in_management is False:
            return False
        return True

    def has_change_permission(self, request, obj=None):
        if obj and obj.in_management is False:
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        if obj and obj.in_management is False:
            return False
        return True


class WellStaticInline(admin.TabularInline):
    model = gmw_models.GroundwaterMonitoringWellStatic
    show_change_link = True
    search_fields = get_searchable_fields(gmw_models.GroundwaterMonitoringWellStatic)
    fields = (
        "internal_id",
        "bro_id",
    )
    readonly_fields = ["bro_id"]

    extra = 0
    max_num = 0


class TubeStaticInline(admin.TabularInline):
    model = gmw_models.GroundwaterMonitoringTubeStatic
    show_change_link = True
    search_fields = get_searchable_fields(gmw_models.GroundwaterMonitoringTubeStatic)
    fields = (
        "deliver_gld_to_bro",
        "tube_number",
        "tube_type",
        "number_of_geo_ohm_cables",
        "bro_actions",
        "report",
    )
    ordering = ["tube_number"]
    readonly_fields = [
        "tube_number",
        "number_of_geo_ohm_cables",
        "bro_actions",
        "report",
    ]

    extra = 0
    max_num = 0

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.in_management is False:
            return (
                "deliver_gld_to_bro",
                "tube_number",
                "tube_type",
                "number_of_geo_ohm_cables",
                "bro_actions",
                "report",
            )
        return []

    def has_add_permission(self, request, obj=None):
        if obj and obj.in_management is False:
            return False
        return True

    def has_change_permission(self, request, obj=None):
        if obj and obj.in_management is False:
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        if obj and obj.in_management is False:
            return False
        return True


class TubeDynamicInline(admin.TabularInline):
    model = gmw_models.GroundwaterMonitoringTubeDynamic
    search_fields = get_searchable_fields(gmw_models.GroundwaterMonitoringWellDynamic)
    fields = (
        "date_from",
        "date_till",
        "tube_top_diameter",
        "tube_top_position",
        "tube_top_positioning_method",
        "tube_status",
        "comment",
    )
    show_change_link = True

    readonly_fields = ["date_from", "date_till", "comment"]

    extra = 0
    max_num = 0


class GeoOhmCableInline(admin.TabularInline):
    model = gmw_models.GeoOhmCable
    search_fields = get_searchable_fields(gmw_models.GeoOhmCable)
    fields = (
        "cable_number",
        "bro_actions",
        "electrode_count",
    )
    show_change_link = True

    readonly_fields = [
        "cable_number",
        "bro_actions",
        "electrode_count",
    ]

    extra = 0
    max_num = 0


class ElectrodeInline(admin.TabularInline):
    model = gmw_models.Electrode
    search_fields = get_searchable_fields(gmw_models.Electrode)
    fields = (
        "electrode_number",
        "electrode_status",
        "bro_actions",
    )
    show_change_link = True

    readonly_fields = [
        "electrode_number",
        "electrode_status",
        "bro_actions",
    ]

    ordering = ["electrode_number"]

    extra = 0
    max_num = 0


class GLDInline(admin.TabularInline):
    model = GroundwaterLevelDossier
    search_fields = get_searchable_fields(GroundwaterLevelDossier)
    fields = (
        "gld_bro_id",
        "groundwater_monitoring_net",
        "research_start_date",
        "research_last_date",
        "research_last_correction",
    )
    show_change_link = True

    readonly_fields = [
        "gld_bro_id",
        "research_start_date",
        "research_last_date",
        "research_last_correction",
    ]

    extra = 0
    max_num = 0


class GroundwaterMonitoringWellStaticAdmin(admin.ModelAdmin):
    form = gmw_forms.GroundwaterMonitoringWellStaticForm
    change_form_template = r"admin\change_form_well.html"

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
    readonly_fields = (
        "lat",
        "lon",
        "report",
        "complete_bro",
        "bro_actions",
        "bro_loket_link",
    )

    fieldsets = [
        (
            "",
            {
                "fields": [
                    "well_code",
                    "internal_id",
                    "bro_id",
                    "bro_loket_link",
                    "delivery_accountable_party",
                    "delivery_responsible_party",
                    "in_management",
                    "deliver_gmw_to_bro",
                    "complete_bro",
                    "quality_regime",
                    "nitg_code",
                    "olga_code",
                    "project",
                    "delivery_context",
                    "construction_standard",
                    "initial_function",
                    "monitoring_pdok_id",
                    "horizontal_positioning_method",
                    "local_vertical_reference_point",
                    "well_offset",
                    "vertical_datum",
                    "last_horizontal_positioning_date",
                    "report",
                    "bro_actions",
                    "x",
                    "y",
                    "lat",
                    "lon",
                ],
            },
        ),
    ]

    inlines = (
        PicturesInline,
        WellDynamicInline,
        TubeStaticInline,
        EventsInline,
    )

    actions = ["deliver_to_bro", "check_status", "generate_fieldform"]

    def save_model(
        self, request, obj: gmw_models.GroundwaterMonitoringWellStatic, form, change
    ):
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
        originele_put = gmw_models.GroundwaterMonitoringWellStatic.objects.filter(
            groundwater_monitoring_well_static_id=obj.groundwater_monitoring_well_static_id
        ).first()

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

        well_checker = WellValidation()
        if obj.groundwater_monitoring_well_static_id:
            is_valid, report = well_checker.well_complete(obj)

            # Update complete_bro and bro_actions in the static object based on validation
            obj.complete_bro = is_valid
            obj.bro_actions = report
        else:
            is_valid = True

        # If not valid, show a warning in the admin interface
        if not is_valid:
            messages.warning(
                request,
                "Er zijn nog acties vereist om het BRO Compleet te maken",
            )

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
        generator.wells = queryset
        generator.generate()


class GroundwaterMonitoringWellDynamicAdmin(admin.ModelAdmin):
    form = gmw_forms.GroundwaterMonitoringWellDynamicForm
    search_fields = (
        "groundwater_monitoring_well_dynamic_id",
        "groundwater_monitoring_well_static__groundwater_monitoring_well_static_id",
        "groundwater_monitoring_well_static__bro_id",
        "date_from",
        "groundwater_monitoring_well_static__well_code",
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

    # inlines = (WellStaticInline,)

    def save_model(
        self, request, obj: gmw_models.GroundwaterMonitoringWellDynamic, form, change
    ):
        try:
            originele_meetpuntgeschiedenis = gmw_models.GroundwaterMonitoringWellDynamic.objects.get(
                groundwater_monitoring_well_dynamic_id=obj.groundwater_monitoring_well_dynamic_id
            )
        except:  # noqa: E722
            logger.exception("Bare except")
            originele_meetpuntgeschiedenis = None

        (valid, message) = validators_admin.validate_surface_height_ahn(obj)
        if valid is False:
            self.message_user(request, message, level="ERROR")
            if originele_meetpuntgeschiedenis is not None:
                obj.ground_level_position = (
                    originele_meetpuntgeschiedenis.ground_level_position
                )

        # test if object is bro_complete
        is_valid, report = validate_well_dynamic(obj)

        # Update complete_bro and bro_actions based on validation
        obj.complete_bro = is_valid
        obj.bro_actions = report

        # If not valid, show a warning in the admin interface
        if not is_valid:
            messages.warning(
                request, "Er zijn nog acties vereist om het BRO Compleet te maken"
            )

        obj.save()


class GroundwaterMonitoringTubeStaticAdmin(admin.ModelAdmin):
    form = gmw_forms.GroundwaterMonitoringTubeStaticForm

    search_fields = (
        "groundwater_monitoring_tube_static_id",
        "groundwater_monitoring_well_static__groundwater_monitoring_well_static_id",
        "groundwater_monitoring_well_static__bro_id",
        "tube_number",
        "groundwater_monitoring_well_static__well_code",
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

    readonly_fields = ["number_of_geo_ohm_cables", "in_monitoring_net", "report"]

    inlines = (
        TubeDynamicInline,
        GeoOhmCableInline,
        GLDInline,
    )

    actions = ["deliver_gld_to_true"]

    def in_monitoring_net(self, obj):
        return len(MeasuringPoint.objects.filter(groundwater_monitoring_tube=obj)) > 0

    def deliver_gld_to_true(self, request, queryset):
        for obj in queryset:
            with reversion.create_revision():
                obj.deliver_gld_to_bro = True
                obj.save()
                reversion.set_comment(
                    "Set deliver_gld_to_bro to True by manual action."
                )

    deliver_gld_to_true.short_description = "Deliver GLD to True"

    def save_model(
        self, request, obj: gmw_models.GroundwaterMonitoringTubeStatic, form, change
    ):
        # test if object is bro_complete
        is_valid, report = validate_tube_static(obj)
        obj.bro_actions = report

        # If not valid, show a warning in the admin interface
        if not is_valid:
            messages.warning(
                request, "Er zijn nog acties vereist om het BRO Compleet te maken"
            )

        obj.save()

        # Update complete_bro and bro_actions based on validation
        well = obj.groundwater_monitoring_well_static
        well.complete_bro = is_valid
        well.save()


class GroundwaterMonitoringTubeDynamicAdmin(admin.ModelAdmin):
    form = gmw_forms.GroundwaterMonitoringTubeDynamicForm
    search_fields = (
        "groundwater_monitoring_tube_dynamic_id",
        "groundwater_monitoring_tube_static__groundwater_monitoring_well_static__groundwater_monitoring_well_static_id",
        "groundwater_monitoring_tube_static__groundwater_monitoring_well_static__bro_id",
        "groundwater_monitoring_tube_static__tube_number",
        "date_from",
        "groundwater_monitoring_tube_static__groundwater_monitoring_well_static__well_code",
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

    readonly_fields = ["screen_top_position", "screen_bottom_position"]

    def save_model(
        self, request, obj: gmw_models.GroundwaterMonitoringTubeDynamic, form, change
    ):
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
                obj.screen_top_position = (
                    originele_filtergeschiedenis.screen_top_position
                )

        (valid, message) = validators_admin.validate_reference_height_ahn(obj)
        if valid is False:
            self.message_user(request, message, level="ERROR")

        is_valid, report = validate_tube_dynamic(obj)
        obj.bro_actions = report

        # If not valid, show a warning in the admin interface
        if not is_valid:
            messages.warning(
                request, "Er zijn nog acties vereist om het BRO Compleet te maken"
            )
        obj.save()


class GeoOhmCableAdmin(admin.ModelAdmin):
    form = gmw_forms.GeoOhmCableForm

    list_display = (
        "geo_ohm_cable_id",
        "groundwater_monitoring_tube_static",
        "cable_number",
        # "electrode_count",
    )

    list_filter = (TubeFilter,)

    readonly_fields = ["electrode_count"]

    inlines = (ElectrodeInline,)

    def save_model(self, request, obj: gmw_models.GeoOhmCable, form, change):
        is_valid, report = validate_geo_ohm_cable(obj)
        obj.bro_actions = report

        # If not valid, show a warning in the admin interface
        if not is_valid:
            messages.warning(
                request, "Er zijn nog acties vereist om het BRO Compleet te maken"
            )
        obj.save()


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

    search_fields = get_searchable_fields(gmw_models.Electrode)


class EventAdmin(admin.ModelAdmin):
    form = gmw_forms.EventForm

    list_display = (
        "change_id",
        "event_name",
        "event_date",
        "groundwater_monitoring_well_static",
        "groundwater_monitoring_well_dynamic",
    )
    list_filter = (
        "change_id",
        WellFilter,
        "event_name",
    )
    ordering = ["-change_id"]
    autocomplete_fields = (
        "groundwater_monitoring_well_static",
        "groundwater_monitoring_well_dynamic",
        "groundwater_monitoring_tube_dynamic",
        "electrodes",
    )

    def save_model(self, request, obj: gmw_models.Event, form, change):
        valid = True

        if obj.event_name == "constructie":
            print(obj.electrodes)
            report_e = ""
            valid_e = True
            for electrode in obj.electrodes.all():
                val_e, rep_e = validate_electrode(electrode)
                if not val_e:
                    report_e += rep_e
                    valid_e = val_e

            valid_td, report_td = True, ""
            valid_ts, report_ts = True, ""

            dynamic = obj.groundwater_monitoring_tube_dynamic.first()
            if dynamic:
                val_ts, rep_ts = validate_tube_static(
                    dynamic.groundwater_monitoring_tube_static
                )
                report_ts = ""
                if not val_ts:
                    report_ts += rep_ts
                    valid_ts = val_ts

            else:
                report_td = "Valid\n"
                report_ts = "Valid\n"

            for tube in obj.groundwater_monitoring_tube_dynamic.all():
                val_td, rep_td = validate_tube_dynamic(tube)
                report_td = ""
                if not val_td:
                    report_td += rep_td
                    valid_td = val_td

            valid_wd, report_wd = validate_well_dynamic(
                obj.groundwater_monitoring_well_dynamic
            )
            valid_ws, report_ws = validate_well_static(
                obj.groundwater_monitoring_well_static
            )

            if (
                not valid_e
                or not valid_td
                or not valid_ts
                or not valid_wd
                or not valid_ws
            ):
                valid = False
                report = f"Electrode:\n{report_e}\nTube Dynamic:\n{report_td}\nTube Static:\n{report_ts}\nWell Dynamic:\n{report_wd}\nWell Static:\n{report_ws}"

        obj.bro_actions = report
        obj.complete_bro = valid

        # If not valid, show a warning in the admin interface
        if not valid:
            messages.warning(
                request, "Er zijn nog acties vereist om het BRO Compleet te maken"
            )
        obj.save()


class PictureAdmin(admin.ModelAdmin):
    list_display = (
        "groundwater_monitoring_well_static",
        "recording_datetime",
        "image_tag",
    )
    list_filter = (
        WellFilter,
        "recording_datetime",
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
    list_filter = (
        "bro_id",
        EventTypeFilter,
        "process_status",
        "comments",
    )

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
        "object_id_accountable_party",
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
_register(gmw_models.Electrode, ElectrodeStaticAdmin)
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
patch_admin(gmw_models.Electrode)
patch_admin(gmw_models.Event)
patch_admin(gmw_models.Picture)
patch_admin(gmw_models.MaintenanceParty)
patch_admin(gmw_models.Maintenance)
patch_admin(gmw_models.gmw_registration_log)
