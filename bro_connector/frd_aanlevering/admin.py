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

_register(GroundwaterMonitoringNet, GroundwaterMonitoringNetAdmin)