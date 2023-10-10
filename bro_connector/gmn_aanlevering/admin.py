from django.contrib import admin
from . import models

def _register(model, admin_class):
    admin.site.register(model, admin_class)


class GroundwaterMonitoringNetAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "broid_gmn",
        "name",
        "measuring_point_count",
        "quality_regime",
        "delivery_context",
        "monitoring_purpose",
        "groundwater_aspect",
        "start_date_monitoring",
    )
    list_filter = (
        "broid_gmn",
        "name",
    )

class MeasuringPointAdmin(admin.ModelAdmin):

    list_display = (
        "gmn",
        "code",
        
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

_register(models.GroundwaterMonitoringNet, GroundwaterMonitoringNetAdmin)
_register(models.MeasuringPoint, MeasuringPointAdmin)
_register(models.IntermediateEvent, IntermediateEventAdmin)