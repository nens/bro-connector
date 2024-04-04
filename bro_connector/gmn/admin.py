from django.contrib import admin
from .models import *
from main.management.tasks.gmn_sync import sync_gmn
from reversion_compare.helpers import patch_admin


def _register(model, admin_class):
    admin.site.register(model, admin_class)


class GroundwaterMonitoringNetAdmin(admin.ModelAdmin):
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

    actions = ["deliver_to_bro", "check_status"]

    @admin.action(description="Deliver GMN to BRO")
    def deliver_to_bro(self, request, queryset):
        sync_gmn(queryset)

    @admin.action(description="Check GMN status from BRO")
    def check_status(self, request, queryset):
        sync_gmn(queryset, check_only=True)


class MeasuringPointAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "gmn",
        "groundwater_monitoring_tube",
        "synced_to_bro",
        "removed_from_BRO_gmn",
    )
    list_filter = (
        "gmn",
        "code",
    )


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


_register(GroundwaterMonitoringNet, GroundwaterMonitoringNetAdmin)
_register(MeasuringPoint, MeasuringPointAdmin)
_register(IntermediateEvent, IntermediateEventAdmin)
_register(gmn_bro_sync_log, gmn_bro_sync_logAdmin)

patch_admin(GroundwaterMonitoringNet)
patch_admin(MeasuringPoint)
patch_admin(IntermediateEvent)
patch_admin(gmn_bro_sync_log)