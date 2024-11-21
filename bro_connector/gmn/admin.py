from django.contrib import admin
from .models import (
    GroundwaterMonitoringNet,
    Subgroup,
    MeasuringPointSubgroup,
    MeasuringPoint,
    IntermediateEvent,
    gmn_bro_sync_log
)
from main.management.tasks.gmn_sync import sync_gmn
from reversion_compare.helpers import patch_admin
from .forms import GroundwaterMonitoringNetForm, SubgroupForm
from main.utils.frd_fieldform import FieldFormGenerator as FRD_FieldFormGenerator
from main.utils.gld_fieldform import FieldFormGenerator as GLD_FieldFormGenerator


def _register(model, admin_class):
    admin.site.register(model, admin_class)

class MeasuringPointSubgroupInline(admin.TabularInline):
    model = MeasuringPointSubgroup
    fiels = (
        "measuring_point",
        "subgroup",
    )
    readonly_fields = (
        "measuring_point",
        "subgroup",
    )
    extra = 1

class MeasuringPointsInline(admin.TabularInline):
    model = MeasuringPoint
    fields = (
        "subgroup",
        "groundwater_monitoring_tube",
        "code",
    )
    readonly_fields = (
        "subgroup",
        "groundwater_monitoring_tube",
        "code",
    )

    extra = 0
    max_num = 0
    ordering = ("subgroup", "groundwater_monitoring_tube",)

class GroundwaterMonitoringNetAdmin(admin.ModelAdmin):
    form = GroundwaterMonitoringNetForm
    list_display = (
        "id",
        "gmn_bro_id",
        "name",
        "measuring_point_count",
        "groundwater_aspect",
        "start_date_monitoring",
        "deliver_to_bro",
        "removed_from_BRO",
    )
    list_filter = (
        "gmn_bro_id",
        "name",
        "monitoring_purpose",
        "groundwater_aspect",
        "deliver_to_bro",
    )

    inlines = (MeasuringPointsInline,)


    actions = ["deliver_to_bro", "check_status", "generate_frd_fieldform", "generate_gld_fieldform"]

    @admin.action(description="Deliver GMN to BRO")
    def deliver_to_bro(self, request, queryset):
        sync_gmn(queryset)

    @admin.action(description="Check GMN status from BRO")
    def check_status(self, request, queryset):
        sync_gmn(queryset, check_only=True)

    @admin.action(description="Generate FRD FieldForm")
    def generate_frd_fieldform(self, request, queryset):
        generator = FRD_FieldFormGenerator()
        generator.inputfields = ["weerstand", "opmerking"]
        generator.monitoringnetworks=queryset
        generator.generate()

    @admin.action(description="Generate GLD FieldForm")
    def generate_gld_fieldform(self, request, queryset):
        generator = GLD_FieldFormGenerator()
        generator.monitoringnetworks=queryset
        generator.generate()


class SubgroupAdmin(admin.ModelAdmin):
    form = SubgroupForm
    list_display = (
        "gmn",
        "name",
        "code",
    )
    list_filter = (
        "gmn",
        "name",
    )

    inlines = (MeasuringPointSubgroupInline,)

class MeasuringPointAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "gmn",
        "list_subgroups",
        "groundwater_monitoring_tube",
        "synced_to_bro",
        "removed_from_BRO_gmn",
    )
    list_filter = (
        "gmn",
        "subgroup",
        "code",
    )
    inlines = (MeasuringPointSubgroupInline,)

class IntermediateEventAdmin(admin.ModelAdmin):
    list_display = (
        "gmn",
        "measuring_point",
        "event_type",
        "event_date",
        "synced_to_bro",
        "deliver_to_bro",
    )
    list_filter = (
        "gmn",
        "measuring_point",
        "event_type",
        "event_date",
        "synced_to_bro",
        "deliver_to_bro",
    )


class gmn_bro_sync_logAdmin(admin.ModelAdmin):
    list_display = (
        "gmn_bro_id",
        "date_modified",
        "last_changed",
        "event_type",
        "process_status",
        "measuringpoint",
        "comments",
    )
    list_filter = (
        "object_id_accountable_party",
        "gmn_bro_id",
    )

    readonly_fields = (
        "date_modified",
        "event_type",
        "gmn_bro_id",
        "object_id_accountable_party",
        "validation_status",
        "delivery_id",
        "delivery_type",
        "delivery_status",
        "delivery_status_info",
        "comments",
        "last_changed",
        "corrections_applied",
        "timestamp_end_registration",
        "quality_regime",
        "file",
        "process_status",
        "measuringpoint"
    )


_register(GroundwaterMonitoringNet, GroundwaterMonitoringNetAdmin)
_register(MeasuringPoint, MeasuringPointAdmin)
_register(IntermediateEvent, IntermediateEventAdmin)
_register(gmn_bro_sync_log, gmn_bro_sync_logAdmin)
_register(Subgroup, SubgroupAdmin)

patch_admin(GroundwaterMonitoringNet)
patch_admin(Subgroup)
patch_admin(MeasuringPoint)
patch_admin(IntermediateEvent)
patch_admin(gmn_bro_sync_log)