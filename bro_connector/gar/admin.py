import logging

from django.contrib import admin
from django.db.models import fields
from gar.models import (
    Analyses,
    AnalysisProcesses,
    Combi,
    FieldMeasurements,
    FieldObservations,
    FieldSamples,
    GroundwaterCompositionResearches,
    LaboratoryAnalyses,
    StoffenGroepen,
    TypeColours,
    TypeColourStrengths,
    TypeParameterlijsten,
    TypeWaardebepalingsmethodes,
    TypeWaardebepalingstechnieken,
)
from reversion_compare.helpers import patch_admin

logger = logging.getLogger(__name__)


def _register(model, admin_class):
    admin.site.register(model, admin_class)


def get_searchable_fields(model_class):
    return [
        f.name
        for f in model_class._meta.fields
        if isinstance(f, (fields.CharField, fields.AutoField))
    ]


@admin.register(Analyses)
class AnalysesAdmin(admin.ModelAdmin):
    list_display = (
        "analysis_id",
        "analysis_process_id",
        "parameter_id",
        "analysis_measurement_value",
    )


@admin.register(AnalysisProcesses)
class AnalysisProcessesAdmin(admin.ModelAdmin):
    list_display = ("analysis_process_id", "laboratory_analysis_id", "analysis_date")


@admin.register(Combi)
class CombiAdmin(admin.ModelAdmin):
    list_display = (
        "prov",
        "monsteridentificatie",
        "meetobjectlokaalid",
        "meetpuntidentificatie",
        "resultaatdatum",
    )


@admin.register(FieldMeasurements)
class FieldMeasurementsAdmin(admin.ModelAdmin):
    list_display = (
        "field_measurement_id",
        "field_sample_id",
        "parameter_id",
        "field_measurement_value",
    )


@admin.register(FieldObservations)
class FieldObservationsAdmin(admin.ModelAdmin):
    list_display = (
        "field_observation_id",
        "field_sample_id",
        "primary_colour_id",
        "secondary_colour_id",
    )


@admin.register(FieldSamples)
class FieldSamplesAdmin(admin.ModelAdmin):
    list_display = (
        "field_sample_id",
        "groundwater_composition_research_id",
        "sampling_datetime",
        "sampling_operator",
    )


@admin.register(GroundwaterCompositionResearches)
class GroundwaterCompositionResearchesAdmin(admin.ModelAdmin):
    list_display = (
        "groundwater_composition_research_id",
        "groundwater_monitoring_tube_id",
        "local_id",
    )


@admin.register(LaboratoryAnalyses)
class LaboratoryAnalysesAdmin(admin.ModelAdmin):
    list_display = (
        "laboratory_analysis_id",
        "groundwater_composition_research_id",
        "responsible_laboratory",
    )


@admin.register(StoffenGroepen)
class StoffenGroepenAdmin(admin.ModelAdmin):
    list_display = (
        "stoffen_percelen_id",
        "cas_nummer",
        "parametercode",
        "stofgroep",
        "stofgroep_omschrijving",
    )


@admin.register(TypeColourStrengths)
class TypeColourStrengthsAdmin(admin.ModelAdmin):
    list_display = ("id", "omschrijving", "waarde", "d_begin", "d_status")


@admin.register(TypeColours)
class TypeColoursAdmin(admin.ModelAdmin):
    list_display = ("id", "description", "value", "startingtime", "status")


@admin.register(TypeParameterlijsten)
class TypeParameterlijstenAdmin(admin.ModelAdmin):
    list_display = (
        "parameter_id",
        "bro_id",
        "aquocode",
        "cas_nummer",
        "omschrijving",
        "eenheid",
        "hoedanigheid",
    )


@admin.register(TypeWaardebepalingsmethodes)
class TypeWaardebepalingsmethodesAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "code",
        "omschrijving",
        "groep",
        "d_begin",
        "d_status",
        "titel",
    )


@admin.register(TypeWaardebepalingstechnieken)
class TypeWaardebepalingstechniekenAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "omschrijving", "d_begin", "d_status")


patch_admin(Analyses)
patch_admin(AnalysisProcesses)
patch_admin(Combi)
patch_admin(FieldMeasurements)
patch_admin(FieldObservations)
patch_admin(FieldSamples)
patch_admin(GroundwaterCompositionResearches)
patch_admin(LaboratoryAnalyses)
patch_admin(StoffenGroepen)
patch_admin(TypeColourStrengths)
patch_admin(TypeColours)
patch_admin(TypeParameterlijsten)
patch_admin(TypeWaardebepalingsmethodes)
patch_admin(TypeWaardebepalingstechnieken)
