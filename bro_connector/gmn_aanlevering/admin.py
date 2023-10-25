from django.contrib import admin
from . import models

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
    )
    list_filter = (
        "gmn_bro_id",
        "name",
    )

class MeasuringPointAdmin(admin.ModelAdmin):

    list_display = (
        "code",
        "gmn",
        "groundwater_monitoring_tube", 
        
        
    )
    list_filter = (
        "gmn",
        "code",
    )

class IntermediateEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "gmn",
        "event_name",
        "event_date",   
    )
    list_filter = (
        "gmn",
        "event_name",
    )

class gmn_registration_logAdmin(admin.ModelAdmin):
    list_display = (
        "object_id_accountable_party",
        "gmn_bro_id",
        "process_status",
    )
    list_filter = (
        "object_id_accountable_party",
        "gmn_bro_id",  
    )

_register(models.GroundwaterMonitoringNet, GroundwaterMonitoringNetAdmin)
_register(models.MeasuringPoint, MeasuringPointAdmin)
_register(models.IntermediateEvent, IntermediateEventAdmin)
_register(models.gmn_registration_log, gmn_registration_logAdmin)