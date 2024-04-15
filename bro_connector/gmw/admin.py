from django.contrib import admin
from django.contrib.gis.geos import GEOSGeometry
from django.db.models import fields
from main.management.tasks.xml_import import xml_import
from zipfile import ZipFile
import os
import reversion
from reversion_compare.helpers import patch_admin 
from django.db import models

from . import models as gmw_models
import main.management.tasks.gmw_actions as gmw_actions
from . import forms as gmw_forms


def _register(model, admin_class):
    admin.site.register(model, admin_class)


def get_searchable_fields(model_class):
    return [
        f.name
        for f in model_class._meta.fields
        if isinstance(f, (fields.CharField, fields.AutoField))
    ]


class InstantieAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "company_number",
        "color",
    )

    list_filter = (
        "name",
        "company_number",
    )


class EventsInline(admin.TabularInline):
    model = gmw_models.Event
    search_fields = get_searchable_fields(gmw_models.Event)
    fields = (
        "event_name",
        "event_date",
    )
    show_change_link = True

    readonly_fields = (
        "groundwater_monitoring_well_static",
        "groundwater_monitoring_well_dynamic",
        "groundwater_monitoring_tube_dynamic",
        "electrode_dynamic",
        "delivered_to_bro",
    )

    extra = 0
    max_num = 0


class GroundwaterMonitoringWellStaticAdmin(admin.ModelAdmin):
    form = gmw_forms.GroundwaterMonitoringWellStaticForm
    change_form_template = "admin\change_form_well.html"

    search_fields = ("groundwater_monitoring_well_static_id",)

    list_display = (
        "groundwater_monitoring_well_static_id",
        "bro_id",
        "delivery_accountable_party",
        "initial_function",
        "nitg_code",
        "well_code",
        "coordinates",
        "in_management",
    )

    list_filter = (
        "delivery_accountable_party",
        "bro_id",
        "nitg_code",
        "well_code",
        "in_management",
    )
    readonly_fields = ('lat', 'lon',)

    fieldsets = [
        (
            "",
            {
                "fields": [
                    "registration_object_type",
                    "bro_id",
                    "request_reference",
                    "delivery_accountable_party",
                    "delivery_responsible_party",
                    "quality_regime",
                    "under_privilege",
                    "delivery_context",
                    "construction_standard",
                    "initial_function",
                    "nitg_code",
                    "olga_code",
                    "well_code",
                    "monitoring_pdok_id",
                    "horizontal_positioning_method",
                    "local_vertical_reference_point",
                    "well_offset",
                    "vertical_datum",
                    "last_horizontal_positioning_date",
                    "in_management",
                ],
            },
        ),
        (
            "Coordinates",
            {
                "fields": ["x", "y", "lat", "lon"],
            },
        ),
        (
            "Construction Coordinates",
            {
                "fields": ["cx", "cy"],
            },
        ),
    ]

    inlines = (EventsInline,)

    actions = ["deliver_to_bro", "check_status"]

    def save_model(self, request, obj, form, change):
        # Haal de waarden van de afgeleide attributen op uit het formulier
        x = form.cleaned_data["x"]
        y = form.cleaned_data["y"]

        cx = form.cleaned_data["cx"]
        cy = form.cleaned_data["cy"]

        # Werk de waarden van de afgeleide attributen bij in het model
        obj.coordinates = GEOSGeometry(f"POINT ({x} {y})", srid=28992)
        if cx != "" and cy != "":
            obj.construction_coordinates = GEOSGeometry(
                f"POINT ({cx} {cy})", srid=28992
            )

        # Sla het model op
        obj.save()

    @admin.action(description="Deliver GMW to BRO")
    def deliver_to_bro(self, request, queryset):
        for well in queryset:
            gmw_actions.check_and_deliver(well)

    @admin.action(description="Check GMW status from BRO")
    def check_status(self, request, queryset):
        for well in queryset:
            gmw_actions.check_status(well)


class GroundwaterMonitoringWellDynamicAdmin(admin.ModelAdmin):
    form = gmw_forms.GroundwaterMonitoringWellDynamicForm
    search_fields = ("groundwater_monitoring_well_dynamic_id", "__str__")

    list_display = (
        "groundwater_monitoring_well_dynamic_id",
        "groundwater_monitoring_well_static",
        "date_from",
        "date_till",
        "number_of_standpipes",
        "owner",
        "well_head_protector",
        "ground_level_position",
        "deliver_gld_to_bro",
    )

    list_filter = ("groundwater_monitoring_well_static", "owner")

    readonly_fields = ["number_of_standpipes", "deliver_gld_to_bro"]


class GroundwaterMonitoringTubeStaticAdmin(admin.ModelAdmin):
    form = gmw_forms.GroundwaterMonitoringTubeStaticForm

    list_display = (
        "groundwater_monitoring_tube_static_id",
        "groundwater_monitoring_well_static",
        "tube_number",
        "tube_type",
        "number_of_geo_ohm_cables",
        "tube_material",
        "screen_length",
        "sock_material",
        "sediment_sump_present",
        "sediment_sump_length",
        "deliver_gld_to_bro",
    )
    list_filter = ("groundwater_monitoring_well_static", "deliver_gld_to_bro")

    readonly_fields = ["number_of_geo_ohm_cables"]

    actions = ["deliver_gld_to_true"]

    def deliver_gld_to_true(self, request, queryset):
        for obj in queryset:
            with reversion.create_revision():
                obj.deliver_gld_to_bro = True
                obj.save()
                reversion.set_comment(
                    "Set deliver_gld_to_bro to True by manual action."
                )

    deliver_gld_to_true.short_description = "Deliver GLD to True"


class GroundwaterMonitoringTubeDynamicAdmin(admin.ModelAdmin):
    form = gmw_forms.GroundwaterMonitoringTubeDynamicForm
    search_fields = ("groundwater_monitoring_tube_static_id", "__str__")
    list_display = (
        "groundwater_monitoring_tube_dynamic_id",
        "groundwater_monitoring_tube_static",
        "date_from",
        "date_till",
        "tube_top_diameter",
        "variable_diameter",
        "tube_status",
        "tube_top_position",
        "plain_tube_part_length",
    )
    list_filter = ("groundwater_monitoring_tube_static",)


class GeoOhmCableAdmin(admin.ModelAdmin):
    form = gmw_forms.GeoOhmCableForm

    list_display = (
        "geo_ohm_cable_id",
        "groundwater_monitoring_tube_static",
        "cable_number",
    )
    list_filter = ("groundwater_monitoring_tube_static_id",)


class ElectrodeStaticAdmin(admin.ModelAdmin):
    form = gmw_forms.ElectrodeStaticForm

    list_display = (
        "electrode_static_id",
        "geo_ohm_cable",
        "electrode_number",
        "electrode_packing_material",
        "electrode_position",
    )
    list_filter = ("electrode_static_id", "geo_ohm_cable")


class ElectrodeDynamicAdmin(admin.ModelAdmin):
    form = gmw_forms.ElectrodeDynamicForm
    search_fields = ("electrode_dynamic_id", "__str__")

    list_display = (
        "electrode_dynamic_id",
        "electrode_static",
        "date_from",
        "date_till",
        "electrode_status",
    )
    list_filter = ("electrode_dynamic_id", "electrode_static")


class EventAdmin(admin.ModelAdmin):
    form = gmw_forms.EventForm

    list_display = (
        "change_id",
        "event_name",
        "event_date",
        "groundwater_monitoring_well_static",
        "groundwater_monitoring_well_dynamic",
        "groundwater_monitoring_tube_dynamic",
        "electrode_dynamic",
    )
    list_filter = (
        "change_id",
        "groundwater_monitoring_well_static",
        "event_name",
        "event_date",
    )
    ordering = ['-change_id'] 
    autocomplete_fields = (
        "groundwater_monitoring_well_static",
        "groundwater_monitoring_well_dynamic",
        "groundwater_monitoring_tube_dynamic",
        "electrode_dynamic",
    )


class PictureAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.BinaryField: {"widget": gmw_forms.BinaryFileInput()},
    }

    list_display = (
        "groundwater_monitoring_well_static",
        "recording_date",
    )
    list_filter = (
        "groundwater_monitoring_well_static",
        "recording_date",
    )


class MaintenancePartyAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "surname",
        "function",
        "organisation",
    )

    search_fields = get_searchable_fields(gmw_models.MaintenanceParty)


class MaintenanceAdmin(admin.ModelAdmin):
    list_display = (
        "kind_of_maintenance",
        "groundwater_monitoring_well_static",
        "reporter",
        "execution_date",
        "execution_by",
    )
    list_filter = (
        "kind_of_maintenance",
        "groundwater_monitoring_well_static",
        "execution_date",
        "reporter",
        "execution_by",
    )


class XMLImportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created",
        "file",
        "checked",
        "imported",
    )

    actions = [
        "update_database",
    ]

    def save_model(self, request, obj, form, change):
        try:
            originele_constructie_import = models.XMLImport.objects.get(id=obj.id)
            file = originele_constructie_import.file
        except models.XMLImport.DoesNotExist:
            originele_constructie_import = None
            file = None

        if obj.file != file and file is not None:
            # If a new csv is set into the ConstructieImport row.
            obj.imported = False
            obj.checked = False
            obj.report = (
                obj.report + f"\nswitched the csv file from {file} to {obj.file}."
            )
            super(XMLImportAdmin, self).save_model(request, obj, form, change)

        else:
            super(XMLImportAdmin, self).save_model(request, obj, form, change)

    def update_database(self, request, QuerySet):
        for object in QuerySet:
            if str(object.file).endswith("xml"):
                print("Handling XML file")
                (completed, message) = xml_import.import_xml(object.file, ".")
                object.checked = True
                object.imported = completed
                object.report += message
                object.save()

            elif str(object.file).endswith("zip"):
                print("Handling ZIP file")
                # First unpack the zip
                with ZipFile(object.file, "r") as zip:
                    zip.printdir()
                    zip.extractall(path=f"./{object.name}/")

                # Remove constructies/ and .zip from the filename
                file_name = str(object.file)[13:-4]
                print(file_name)

                path = f"."

                for file in os.listdir(path):
                    if file.endswith("csv"):
                        print(
                            f"Bulk import of filetype of {file} not yet supported not yet supported."
                        )
                        object.report += (
                            f"\n UNSUPPORTED FILE TYPE: {file} is not supported."
                        )
                        object.save()
                        pass

                    elif file.endswith("xml"):
                        (completed, message) = xml_import.import_xml(file, path)
                        object.checked = True
                        object.imported = completed
                        object.report += message
                        object.save()

                    else:
                        object.report += (
                            f"\n UNSUPPORTED FILE TYPE: {file} is not supported."
                        )
                        object.save()


class GmwSyncLogAdmin(admin.ModelAdmin):
    list_display = (
        "date_modified",
        "last_changed",
        "bro_id",
        "process_status",
        "comments",
    )
    list_filter = ("bro_id",)


_register(
    gmw_models.GroundwaterMonitoringWellStatic, GroundwaterMonitoringWellStaticAdmin
)
_register(
    gmw_models.GroundwaterMonitoringWellDynamic, GroundwaterMonitoringWellDynamicAdmin
)
_register(
    gmw_models.GroundwaterMonitoringTubeStatic, GroundwaterMonitoringTubeStaticAdmin
)
_register(
    gmw_models.GroundwaterMonitoringTubeDynamic, GroundwaterMonitoringTubeDynamicAdmin
)
_register(gmw_models.GeoOhmCable, GeoOhmCableAdmin)
_register(gmw_models.ElectrodeStatic, ElectrodeStaticAdmin)
_register(gmw_models.ElectrodeDynamic, ElectrodeDynamicAdmin)
_register(gmw_models.Event, EventAdmin)
_register(gmw_models.Picture, PictureAdmin)
_register(gmw_models.MaintenanceParty, MaintenancePartyAdmin)
_register(gmw_models.Maintenance, MaintenanceAdmin)
_register(gmw_models.gmw_registration_log, GmwSyncLogAdmin)
_register(gmw_models.Instantie, InstantieAdmin)

patch_admin(gmw_models.GroundwaterMonitoringWellStatic)
patch_admin(gmw_models.GroundwaterMonitoringWellDynamic)
patch_admin(gmw_models.GroundwaterMonitoringTubeStatic)
patch_admin(gmw_models.GroundwaterMonitoringTubeDynamic)
patch_admin(gmw_models.GeoOhmCable)
patch_admin(gmw_models.ElectrodeStatic)
patch_admin(gmw_models.ElectrodeDynamic)
patch_admin(gmw_models.Event)
patch_admin(gmw_models.Picture)
patch_admin(gmw_models.MaintenanceParty)
patch_admin(gmw_models.Maintenance)
patch_admin(gmw_models.gmw_registration_log)
patch_admin(gmw_models.Instantie)