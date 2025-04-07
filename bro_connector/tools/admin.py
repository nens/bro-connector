from reversion_compare.helpers import patch_admin
from django.db import models
from django.contrib import admin, messages
from django.db.models import fields
from main.management.tasks.xml_import import xml_import
from zipfile import ZipFile
import os
from . import models as tools_models
from main.management.tasks import (
    retrieve_historic_gmw,
    retrieve_historic_frd,
    retrieve_historic_gld,
    retrieve_historic_gmn,
    retrieve_historic_gar,
)
import datetime


def _register(model, admin_class):
    admin.site.register(model, admin_class)


def get_searchable_fields(model_class: models.Model) -> list[str]:
    return [
        f.name
        for f in model_class._meta.fields
        if isinstance(f, (fields.CharField, fields.AutoField))
    ]


def format_message(type: str, kvk: int, count: int, imported: int) -> dict:
    if type in ["gar", "gmn", "frd"]:
        return {"message": f"BRO type {type} not yet implemented.", "level": "WARNING"}
    elif count == 0:
        return {"message": f"No {type}-objects found for {kvk}.", "level": "ERROR"}
    elif count == imported:
        return {
            "message": f"All {type}-objects imported for {kvk}. ({imported})",
            "level": "SUCCESS",
        }
    elif imported == 0:
        return {
            "message": f"No {type}-objects imported for {kvk}. Found: {count} objects.",
            "level": "ERROR",
        }
    elif count > imported:
        return {
            "message": f"Imported {imported} out of {count} {type}-objects for {kvk}.",
            "level": "WARNING",
        }


class BroImporterAdmin(admin.ModelAdmin):
    search_fields = get_searchable_fields(tools_models.BroImporter)

    list_display = (
        "id",
        "bro_type",
        "kvk_number",
        "import_date",
    )

    list_filter = (
        "bro_type",
        "kvk_number",
    )

    readonly_fields = (
        "import_date",
        "created_date",
    )

    actions = ["update_import"]

    # IDEA: COULD ADD FEATURE TO IMPORT ONLY ONE ID.

    def save_model(self, request, obj, form, change):
        module_to_call = {
            "gmw": retrieve_historic_gmw,
            "gmn": retrieve_historic_gmn,
            "gld": retrieve_historic_gld,
            "frd": retrieve_historic_frd,
            "gar": retrieve_historic_gar,
        }

        import_info = module_to_call[obj.bro_type].run(kvk_number=obj.kvk_number)
        message_info = format_message(
            obj.bro_type,
            obj.kvk_number,
            import_info["ids_found"],
            import_info["imported"],
        )

        obj.import_date = datetime.datetime.now()
        self.message_user(request, message_info["message"], level=message_info["level"])
        obj.save()

    @admin.action(description="Re-import values from the BRO.")
    def update_import(self, request, queryset):
        pass


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
            originele_constructie_import = tools_models.XMLImport.objects.get(id=obj.id)
            file = originele_constructie_import.file
        except tools_models.XMLImport.DoesNotExist:
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
            app_dir = os.path.abspath(os.path.curdir)

            if str(object.file).endswith("xml"):
                print("Handling XML file")
                (completed, message) = xml_import.import_xml(object.file, app_dir)
                object.checked = True
                object.imported = completed
                object.report += message
                object.save()

            elif str(object.file).endswith("zip"):
                print("Handling ZIP file")
                # First unpack the zip
                with ZipFile(object.file, "r") as zip:
                    zip.printdir()
                    zip.extractall(path=app_dir)

                # Remove constructies/ and .zip from the filename
                file_name = str(object.file)[13:-4]
                print(file_name)

                for file in os.listdir(app_dir):
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
                        (completed, message) = xml_import.import_xml(file, app_dir)
                        object.checked = True
                        object.imported = completed
                        object.report += message
                        object.save()

                    else:
                        object.report += (
                            f"\n UNSUPPORTED FILE TYPE: {file} is not supported."
                        )
                        object.save()


class GLDImportAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "validated",
        "executed",
    )

    list_filter = (
        "validated",
        "executed",
    )

    def get_fields(self, request, obj=None):
        fields = [
            "file",
            "groundwater_monitoring_tube",
            "responsible_party",
            "observation_type",
            "field_value_unit",
            "status",
            "process_reference",
            "measurement_instrument_type",
            "air_pressure_compensation_type",
            "process_type",
            "evaluation_procedure",
        ]

        # Only show 'report' if it contains something
        if obj and obj.report and obj.report.strip():
            fields.append("report")

        return fields

    def save_model(self, request, obj, form, change):
        # Save the object first
        super().save_model(request, obj, form, change)

        # Check if validated is False, and add a warning message
        if not obj.validated:
            messages.warning(
                request,
                f'The GLD Import "{obj}" was added, but it has not been validated. Please review the report in the model.',
            )

        else:
            messages.success(request, f'The GLD Import "{obj}" was added successfully.')


class GMNImportAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "validated",
        "executed",
    )

    list_filter = (
        "validated",
        "executed",
    )

    def save_model(self, request, obj, form, change):
        # Save the object first
        super().save_model(request, obj, form, change)

        # Check if validated is False, and add a warning message
        if not obj.validated:
            messages.warning(
                request,
                f'The GMN Import "{obj}" was added, but an error occured. Please review the report in the model.',
            )

        else:
            messages.success(request, f'The GLD Import "{obj}" was added successfully.')


_register(tools_models.BroImporter, BroImporterAdmin)
_register(tools_models.XMLImport, XMLImportAdmin)
_register(tools_models.GLDImport, GLDImportAdmin)
_register(tools_models.GMNImport, GMNImportAdmin)
patch_admin(tools_models.BroImporter)
patch_admin(tools_models.XMLImport)
patch_admin(tools_models.GLDImport)
patch_admin(tools_models.GMNImport)
