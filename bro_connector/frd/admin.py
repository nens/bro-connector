from django.contrib import admin
from django.db.models import fields
from .models import *
from reversion_compare.helpers import patch_admin
from main.management.commands.frd_sync_to_bro import FRDSync


def _register(model: models.Model, admin_class: admin.ModelAdmin):
    admin.site.register(model, admin_class)


def get_searchable_fields(model_class):
    return [
        f.name
        for f in model_class._meta.fields
        if isinstance(f, (fields.CharField, fields.AutoField))
    ]


class FormationResistanceDossierAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "frd_bro_id",
        "groundwater_monitoring_tube",
        "delivery_accountable_party",
        "assessment_type",
        "quality_regime",
        "deliver_to_bro",
    )
    list_filter = (
        "frd_bro_id",
        "groundwater_monitoring_tube",
        "delivery_accountable_party",
        "deliver_to_bro",
    )

    actions = ["deliver_to_bro", "check_status"]

    @admin.action(description="Deliver FRD to BRO")
    def deliver_to_bro(self, request, queryset):
        syncer = FRDSync()
        syncer.handle(queryset)
    
    @admin.action(description="Check FRD status from BRO")
    def check_status(self, request, queryset):
        syncer = FRDSync()
        syncer.handle(queryset, check_only=True)



class InstrumentConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "formation_resistance_dossier",
        "electromagnetic_measurement_method",
    )
    list_filter = (
        "id",
        "formation_resistance_dossier",
        "electromagnetic_measurement_method",
    )


class ElectromagneticMeasurementMethodAdmin(admin.ModelAdmin):
    list_display = ("id",)
    list_filter = ()


class GeoOhmMeasurementMethodAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "measurement_date",
        "measuring_responsible_party",
        "measuring_procedure",
        "assessment_procedure",
    )

    list_filter = (
        "measuring_responsible_party",
        "measuring_procedure",
        "assessment_procedure",
        "measurement_date",
    )


class CalculatedFormationresistanceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "responsible_party",
        "electromagnetic_measurement_method",
        "geo_ohm_measurement_method",
    )
    list_filter = (
        "responsible_party",
        "electromagnetic_measurement_method",
        "geo_ohm_measurement_method",
    )


class GeoOhmMeasurementValueAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "formationresistance",
        "measurement_configuration",
        "datetime",
    )
    list_filter = (
        "measurement_configuration",
        "datetime",
    )


class GMWElectrodeReferenceAdmin(admin.ModelAdmin):
    list_display = ("id",)
    list_filter = ()


class ElectrodePairAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "elektrode1",
        "elektrode2",
    )
    list_filter = (
        "elektrode1",
        "elektrode2",
    )


class MeasurementConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "bro_id",
        "configuration_name",
        "measurement_pair",
        "flowcurrent_pair",
    )
    list_filter = (
        "configuration_name",
        "measurement_pair",
        "flowcurrent_pair",
    )


class ElectromagneticSeriesAdmin(admin.ModelAdmin):
    list_display = ("id",)

    list_filter = ()


class FormationresistanceSeriesAdmin(admin.ModelAdmin):
    list_display = ("id",)
    list_filter = ()


class ElectromagneticRecordAdmin(admin.ModelAdmin):
    list_display = ("id",)
    list_filter = ()


class FormationresistanceRecordAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "series",
        "vertical_position",
        "formationresistance",
        "status_qualitycontrol",
    )
    list_filter = (
        "series",
        "vertical_position",
        "formationresistance",
        "status_qualitycontrol",
    )


class FrdSyncLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "event_type",
        "delivery_type",
        "synced",
        "frd",
        "process_status",
        "delivery_id",
    )
    list_filter = (
        "event_type",
        "synced",
        "process_status",
    )


_register(FormationResistanceDossier, FormationResistanceDossierAdmin)
_register(CalculatedFormationresistanceMethod, CalculatedFormationresistanceAdmin)
_register(InstrumentConfiguration, InstrumentConfigurationAdmin)
_register(ElectromagneticMeasurementMethod, ElectromagneticMeasurementMethodAdmin)
_register(GeoOhmMeasurementMethod, GeoOhmMeasurementMethodAdmin)
_register(GeoOhmMeasurementValue, GeoOhmMeasurementValueAdmin)
_register(GMWElectrodeReference, GMWElectrodeReferenceAdmin)
_register(ElectrodePair, ElectrodePairAdmin)
_register(MeasurementConfiguration, MeasurementConfigurationAdmin)
_register(FormationresistanceSeries, FormationresistanceSeriesAdmin)
_register(ElectromagneticSeries, ElectromagneticSeriesAdmin)
_register(ElectromagneticRecord, ElectromagneticRecordAdmin)
_register(FormationresistanceRecord, FormationresistanceRecordAdmin)
_register(FrdSyncLog, FrdSyncLogAdmin)

# Voorbeeld voor offerte
patch_admin(FormationResistanceDossier)
patch_admin(GeoOhmMeasurementValue)
patch_admin(GeoOhmMeasurementMethod)
patch_admin(CalculatedFormationresistanceMethod)
patch_admin(InstrumentConfiguration)
patch_admin(ElectromagneticMeasurementMethod)
patch_admin(GMWElectrodeReference)
patch_admin(ElectrodePair)
patch_admin(MeasurementConfiguration)
patch_admin(FormationresistanceSeries)
patch_admin(ElectromagneticSeries)
patch_admin(ElectromagneticRecord)
patch_admin(FormationresistanceRecord)
patch_admin(FrdSyncLog)
