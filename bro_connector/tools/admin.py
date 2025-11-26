import datetime
import os
import tempfile
from zipfile import ZipFile

from django.contrib import admin, messages
from django.db import models
from django.db.models import fields
from main.management.tasks.xml_import import xml_import
from reversion_compare.helpers import patch_admin

from . import models as tools_models


def _register(model, admin_class):
    admin.site.register(model, admin_class)


def get_searchable_fields(model_class: models.Model) -> list[str]:
    return [
        f.name
        for f in model_class._meta.fields
        if isinstance(f, (fields.CharField | fields.AutoField))
    ]


class BroImportAdmin(admin.ModelAdmin):
    search_fields = get_searchable_fields(tools_models.BroImport)

    list_display = (
        "id",
        "handler",
        "bro_type",
        "kvk_number",
        "file_name",
        "import_date",
    )

    list_filter = (
        "bro_type",
        "kvk_number",
        "validated",
        "executed",
    )

    readonly_fields = [
        "file_name",
        "import_date",
        "created_date",
        "report",
        "validated",
        "executed",
    ]

    actions = ["update_import"]

    def save_model(self, request, obj, form, change):
        # Save the object first
        super().save_model(request, obj, form, change)

        # Check if validated is False, and add a warning message
        if not obj.validated:
            messages.warning(
                request,
                f'De BRO Import"{obj}" is aangemaakt maar is niet valide. Bekijk de rapportage voor verdere acties.',
            )

        else:
            messages.success(request, f'De BRO Import "{obj}" is succesvol uitgevoerd.')

    @admin.action(description="Importeer waardes opnieuw uit de BRO")
    def update_import(self, request, queryset):
        for obj in queryset:
            obj.import_date = datetime.datetime.now()
            obj.save()


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
            old_file = originele_constructie_import.file
        except tools_models.XMLImport.DoesNotExist:
            old_file = None

        print(obj.file.path)

        # call super so file is saved
        super().save_model(request, obj, form, change)

        # If file changed (or new object)
        if obj.file and obj.file != old_file:
            # Reset flags
            obj.imported = False
            obj.checked = False
            if old_file:
                obj.report = (
                    obj.report or ""
                ) + f"\nSwitched the file from {old_file} to {obj.file}."
            else:
                obj.report = (obj.report or "") + f"\nUploaded new file {obj.file}."

            self._process_import(obj)

    def _process_import(self, obj):
        """Handle XML/ZIP files"""
        file_full_path = obj.file.path
        file_name = os.path.basename(file_full_path)
        file_dir = os.path.dirname(file_full_path)
        print(file_full_path, file_name, file_dir)

        if file_full_path.endswith(".xml"):
            completed, message = xml_import.import_xml(file_name, file_dir)
            obj.checked = True
            obj.imported = completed
            obj.report = (obj.report or "") + message
            obj.save()

        elif file_full_path.endswith(".zip"):
            with tempfile.TemporaryDirectory() as temp_dir:
                with ZipFile(file_full_path, "r") as zipf:
                    zipf.extractall(path=temp_dir)

                # Process extracted files
                for extracted_file in os.listdir(temp_dir):
                    extracted_path = os.path.join(temp_dir, extracted_file)

                    if extracted_file.endswith(".xml"):
                        extracted_name = os.path.basename(extracted_path)
                        completed, message = xml_import.import_xml(
                            extracted_name, temp_dir
                        )
                        obj.checked = True
                        obj.imported = completed
                        obj.report = (obj.report or "") + message
                        obj.save()
                    else:
                        obj.report = (
                            (obj.report or "")
                            + f"\nUNSUPPORTED FILE TYPE: {extracted_file} is not supported."
                        )
                        obj.save()
        else:
            obj.report = (
                obj.report or ""
            ) + f"\nUNSUPPORTED FILE TYPE: {file_name} is not supported."
            obj.save()

    def update_database(self, request, queryset):
        for obj in queryset:
            self._process_import(obj)


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
    autocomplete_fields = ["groundwater_monitoring_tube", "responsible_party"]
    readonly_fields = ["report", "validated", "executed"]

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
            messages.success(request, f'The GMN Import "{obj}" was added successfully.')


_register(tools_models.BroImport, BroImportAdmin)
_register(tools_models.XMLImport, XMLImportAdmin)
_register(tools_models.GLDImport, GLDImportAdmin)
_register(tools_models.GMNImport, GMNImportAdmin)
patch_admin(tools_models.BroImport)
patch_admin(tools_models.XMLImport)
patch_admin(tools_models.GLDImport)
patch_admin(tools_models.GMNImport)
