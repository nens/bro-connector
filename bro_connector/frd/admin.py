import csv

from django.contrib import admin
from django.db.models import Model, fields
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from main.management.commands.frd_sync_to_bro import FRDSync
from reversion_compare.helpers import patch_admin

from .models import (
    CalculatedFormationresistanceMethod,
    ElectrodePair,
    ElectromagneticMeasurementMethod,
    ElectromagneticRecord,
    ElectromagneticSeries,
    FormationResistanceDossier,
    FormationresistanceRecord,
    FormationresistanceSeries,
    FrdSyncLog,
    GeoOhmMeasurementMethod,
    GeoOhmMeasurementValue,
    GMWElectrodeReference,
    InstrumentConfiguration,
    MeasurementConfiguration,
)


def Export_selected_items_to_csv(self, request, queryset):
    meta = self.model._meta
    field_names = [field.name for field in meta.fields]

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f"attachment; filename={meta}.csv"
    writer = csv.writer(response)

    writer.writerow(field_names)
    for obj in queryset:
        writer.writerow([getattr(obj, field) for field in field_names])

    return response


admin.site.add_action(Export_selected_items_to_csv)


class BroIdNullFilter(admin.SimpleListFilter):
    title = _("Met/Zonder BRO-ID")  # label in the sidebar
    parameter_name = "bro_id_null"

    def lookups(self, request, model_admin):
        return (
            ("yes", _("Geen BRO-ID")),
            ("no", _("Met BRO-ID")),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(bro_id__isnull=True)
        if self.value() == "no":
            return queryset.filter(bro_id__isnull=False)
        return queryset


def _register(model: Model, admin_class: admin.ModelAdmin):
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
        BroIdNullFilter,
    )

    autocomplete_fields = ["groundwater_monitoring_tube"]

    actions = ["deliver_to_bro", "check_status"]

    readonly_fields = [
        "frd_bro_id",
        "first_measurement",
        "most_recent_measurement",
        "closure_date",
    ]

    search_fields = [
        "frd_bro_id",
        "groundwater_monitoring_tube__groundwater_monitoring_well_static__well_code",
        "groundwater_monitoring_tube__groundwater_monitoring_well_static__bro_id",
        "groundwater_monitoring_tube__groundwater_monitoring_well_static__groundwater_monitoring_well_static_id",
    ]

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
        "formation_resistance_dossier",
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

    readonly_fields = (
        "synced",
        "date_modified",
        "bro_id",
        "event_type",
        "frd",
        "geo_ohm_measuring_method",
        "electomagnetic_method",
        "process_status",
        "comment",
        "xml_filepath",
        "delivery_status",
        "delivery_status_info",
        "delivery_id",
        "delivery_type",
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
