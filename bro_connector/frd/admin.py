from django.contrib import admin
from .models import *

def _register(model, admin_class):
    admin.site.register(model, admin_class)


class FormationResistanceDossierAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "frd_bro_id",
        "object_id_accountable_party",
        "quality_regime",
    )
    list_filter = (
        "id",
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
    )
    list_filter = (

    )

class GeoOhmMeasurementValueAdmin(admin.ModelAdmin):

    list_display = (
        "id",
    )
    list_filter = (

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
    )
    list_filter = (

    )

class MeasurementConfigurationAdmin(admin.ModelAdmin):

    list_display = (
        "id",
    )
    list_filter = (

    )

class ElectromagneticSeriesAdmin(admin.ModelAdmin):

    list_display = (
        "id",
    )
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
    )
    list_filter = (

    )

_register(FormationResistanceDossier, FormationResistanceDossierAdmin)
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