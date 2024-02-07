from django.contrib import admin
from django import forms
from django.contrib.gis.geos import GEOSGeometry
from django.db.models import fields
from main.management.tasks.xml_import import xml_import
from zipfile import ZipFile
import os

from django.db import models

from . import models as gmw_models

from main.settings.base import gmw_SETTINGS
from . import forms as gmw_forms


def _register(model, admin_class):
    admin.site.register(model, admin_class)


def get_searchable_fields(model_class):
    return [
        f.name
        for f in model_class._meta.fields
        if isinstance(f, (fields.CharField, fields.AutoField))
    ]


class GroundwaterMonitoringWellStaticAdmin(admin.ModelAdmin):
    

    form = gmw_forms.GroundwaterMonitoringWellStaticForm

    list_display = (
        "groundwater_monitoring_well_static_id",
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
        "coordinates",
        "reference_system",
        "horizontal_positioning_method",
        "local_vertical_reference_point",
        "well_offset",
        "vertical_datum",
        "last_horizontal_positioning_date",
        "construction_coordinates",
        "in_management",
    )

    list_filter = ("delivery_accountable_party", "nitg_code", "in_management")

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
                "fields": ["x", "y"],
            },
        ),
        (
            "Construction Coordinates",
            {
                "fields": ["cx", "cy"],
            },
        ),
    ]

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


class GroundwaterMonitoringWellDynamicAdmin(admin.ModelAdmin):

    form = gmw_forms.GroundwaterMonitoringWellDynamicForm

    list_display = (
        "groundwater_monitoring_well_dynamic_id",
        "groundwater_monitoring_well_static",
        "number_of_standpipes",
        "ground_level_stable",
        "well_stability",
        "owner",
        "maintenance_responsible_party",
        "well_head_protector",
        "deliver_gld_to_bro",
        "ground_level_position",
        "ground_level_positioning_method",
    )
    list_filter = ("groundwater_monitoring_well_static", "deliver_gld_to_bro", "owner")


class GroundwaterMonitoringTubesStaticAdmin(admin.ModelAdmin):

    form = gmw_forms.GroundwaterMonitoringTubesStaticForm

    list_display = (
        "groundwater_monitoring_tube_static_id",
        "groundwater_monitoring_well_static",
        "deliver_gld_to_bro",
        "tube_number",
        "tube_type",
        "artesian_well_cap_present",
        "sediment_sump_present",
        "number_of_geo_ohm_cables",
        "tube_material",
        "screen_length",
        "sock_material",
        "sediment_sump_length",
    )
    list_filter = ("deliver_gld_to_bro",)


class GroundwaterMonitoringTubesDynamicAdmin(admin.ModelAdmin):

    form = gmw_forms.GroundwaterMonitoringTubesDynamicForm

    list_display = (
        "groundwater_monitoring_tube_dynamic_id",
        "groundwater_monitoring_tube_static_id",
        "tube_top_diameter",
        "variable_diameter",
        "tube_status",
        "tube_top_position",
        "tube_top_positioning_method",
        "tube_packing_material",
        "glue",
        "plain_tube_part_length",
        "inserted_part_diameter",
        "inserted_part_length",
        "inserted_part_material",
    )
    list_filter = ("groundwater_monitoring_tube_static_id",)


class GeoOhmCableAdmin(admin.ModelAdmin):

    form = gmw_forms.GeoOhmCableForm

    list_display = (
        "geo_ohm_cable_id",
        "groundwater_monitoring_tube_static_id",
        "cable_number",
    )
    list_filter = ("groundwater_monitoring_tube_static_id",)


class ElectrodeStaticAdmin(admin.ModelAdmin):

    form = gmw_forms.ElectrodeStaticForm

    list_display = (
        "electrode_static_id",
        "geo_ohm_cable_id",
        "electrode_number",
        "electrode_packing_material",
        "electrode_position",
    )
    list_filter = ("electrode_static_id",)


class ElectrodeDynamicAdmin(admin.ModelAdmin):

    form = gmw_forms.ElectrodeDynamicForm

    list_display = (
        "electrode_dynamic_id",
        "electrode_static_id",
        "electrode_status",
    )
    list_filter = ("electrode_dynamic_id",)


class EventAdmin(admin.ModelAdmin):

    form = gmw_forms.EventForm

    list_display = (
        "change_id",
        "event_name",
        "event_date",
        "groundwater_monitoring_well_static",
        "groundwater_monitoring_tube_dynamic",
        "electrode_dynamic",
    )
    list_filter = ("change_id",)


class PictureAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.BinaryField: {'widget': gmw_forms.BinaryFileInput()},
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
        "organisation",
        "postal_code",
        "function",
    )
    list_filter = (
        "organisation",
        "postal_code",
        "function",
    )


class MaintenanceAdmin(admin.ModelAdmin):

    list_display = (
        "kind_of_maintenance",
        "groundwater_monitoring_well_static",
        "execution_date",
        "reporter",
    )
    list_filter = (
        "kind_of_maintenance",
        "groundwater_monitoring_well_static",
        "execution_date",
        "reporter",
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


# _register(models.GroundwaterMonitoringTubes, GroundwaterMonitoringTubesAdmin)
_register(gmw_models.GroundwaterMonitoringWellStatic, GroundwaterMonitoringWellStaticAdmin)
_register(
    gmw_models.GroundwaterMonitoringWellDynamic, GroundwaterMonitoringWellDynamicAdmin
)
_register(
    gmw_models.GroundwaterMonitoringTubeStatic, GroundwaterMonitoringTubesStaticAdmin
)
_register(
    gmw_models.GroundwaterMonitoringTubeDynamic, GroundwaterMonitoringTubesDynamicAdmin
)
_register(gmw_models.GeoOhmCable, GeoOhmCableAdmin)
_register(gmw_models.ElectrodeStatic, ElectrodeStaticAdmin)
_register(gmw_models.ElectrodeDynamic, ElectrodeDynamicAdmin)
_register(gmw_models.Event, EventAdmin)
_register(gmw_models.Picture, PictureAdmin)
_register(gmw_models.MaintenanceParty, MaintenancePartyAdmin)
_register(gmw_models.Maintenance, MaintenanceAdmin)
admin.site.register(gmw_models.gmw_registration_log)