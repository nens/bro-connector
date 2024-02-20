from django.contrib import admin
from django.db.models import fields
from .models import *
from reversion_compare.helpers import patch_admin

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
        "object_id_accountable_party",
        "quality_regime",
    )
    list_filter = (
        "object_id_accountable_party",
    )

class InstrumentConfigurationAdmin(admin.ModelAdmin):

    list_display = (
        "id",
    )
    list_filter = (

    )

class ElectromagneticMeasurementMethodAdmin(admin.ModelAdmin):

    list_display = (
        "id",
    )
    list_filter = (

    )

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
    )

    search_fields = get_searchable_fields(GeoOhmMeasurementMethod)


class CalculatedFormationresistanceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "responsible_party",
        "electromagnetic_measurement_method",
        "geo_ohm_measurement_method"
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
        "datetime"
    )
    list_filter = (
        "measurement_configuration",
    )

class GMWElectrodeReferenceAdmin(admin.ModelAdmin):

    list_display = (
        "id",
    )
    list_filter = (

    )

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

    list_display = (
    "id",)
    
    list_filter = (

    )

class FormationresistanceSeriesAdmin(admin.ModelAdmin):

    list_display = (
        "id",
    )
    list_filter = (

    )

class ElectromagneticRecordAdmin(admin.ModelAdmin):

    list_display = (
        "id",
    )
    list_filter = (

    )

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
        "synced",
        "frd",
        "process_status",
        "delivery_id"
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
_register(FrdSyncLog,FrdSyncLogAdmin)

# Voorbeeld voor offerte
patch_admin(FormationResistanceDossier)
patch_admin(GeoOhmMeasurementValue)
patch_admin(GeoOhmMeasurementMethod)