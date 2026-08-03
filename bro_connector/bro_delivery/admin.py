from django.contrib import admin

from bro_delivery.models import FRDMessage, GLDMessage, GMNMessage, GMWMessage


class MessageAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "registration_type",
        "request_type",
        "quality_regime",
        "status",
        "bro_id",
        "brostar_task_url",
        "date_created",
        "date_modified",
    ]
    list_filter = ["status", "registration_type", "request_type", "quality_regime"]
    search_fields = ["bro_id", "brostar_task_id", "registration_type"]
    readonly_fields = [
        "status",
        "bro_id",
        "bro_errors",
        "brostar_task_id",
        "brostar_task_url",
        "date_created",
        "date_modified",
    ]
    fieldsets = [
        (
            "Bericht",
            {
                "fields": [
                    "registration_type",
                    "request_type",
                    "quality_regime",
                    "bro_project",
                    "metadata",
                    "sourcedocument_data",
                ]
            },
        ),
        (
            "BROSTAR status",
            {
                "fields": [
                    "status",
                    "bro_id",
                    "brostar_task_id",
                    "brostar_task_url",
                    "bro_errors",
                ],
                "classes": ["collapse"],
            },
        ),
        (
            "Tijdstempels",
            {
                "fields": ["date_created", "date_modified"],
                "classes": ["collapse"],
            },
        ),
    ]


@admin.register(GMWMessage)
class GMWMessageAdmin(MessageAdmin):
    list_display = ["groundwater_monitoring_well"] + MessageAdmin.list_display
    fieldsets = [
        (
            "Grondwatermonitoringput",
            {"fields": ["groundwater_monitoring_well"]},
        ),
    ] + MessageAdmin.fieldsets


@admin.register(GLDMessage)
class GLDMessageAdmin(MessageAdmin):
    list_display = ["groundwater_level_dossier"] + MessageAdmin.list_display
    fieldsets = [
        (
            "Grondwaterstandsdossier",
            {"fields": ["groundwater_level_dossier"]},
        ),
    ] + MessageAdmin.fieldsets


@admin.register(FRDMessage)
class FRDMessageAdmin(MessageAdmin):
    list_display = ["formation_resistance_dossier"] + MessageAdmin.list_display
    fieldsets = [
        (
            "Formatieweerstandsdossier",
            {"fields": ["formation_resistance_dossier"]},
        ),
    ] + MessageAdmin.fieldsets


@admin.register(GMNMessage)
class GMNMessageAdmin(MessageAdmin):
    list_display = ["groundwater_monitoring_net"] + MessageAdmin.list_display
    fieldsets = [
        (
            "Grondwatermonitoringnet",
            {"fields": ["groundwater_monitoring_net"]},
        ),
    ] + MessageAdmin.fieldsets
