from django.contrib import admin
from .models import *

def _register(model, admin_class):
    admin.site.register(model, admin_class)


class GroundwaterMonitoringNetAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "gmn_bro_id",
        "name",
        "measuring_point_count",
        "quality_regime",
        "delivery_context",
        "monitoring_purpose",
        "groundwater_aspect",
        "start_date_monitoring",
        "deliver_to_bro",
        "removed_from_BRO"
    )
    list_filter = (
        "gmn_bro_id",
        "name",
        "quality_regime",
        "delivery_context",
        "monitoring_purpose",
        "groundwater_aspect",
        "deliver_to_bro",
    )


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
        "event_type",
        "event_date",
        "synced_to_bro",
        "deliver_to_bro",
    )
    list_filter = (
        "gmn",
        "event_type",
        "event_date",
        "synced_to_bro",
        "deliver_to_bro",
    )

class gmn_bro_sync_logAdmin(admin.ModelAdmin):
    list_display = (
        "object_id_accountable_party",
        "event_type",
        "gmn_bro_id",
        "process_status",
        "measuringpoint",
    )
    list_filter = (
        "object_id_accountable_party",
        "gmn_bro_id",  
    )

_register(GroundwaterMonitoringNet, GroundwaterMonitoringNetAdmin)
_register(MeasuringPoint, MeasuringPointAdmin)
_register(IntermediateEvent, IntermediateEventAdmin)
_register(gmn_bro_sync_log, gmn_bro_sync_logAdmin)