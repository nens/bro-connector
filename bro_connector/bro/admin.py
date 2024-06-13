from django.contrib import admin
from django.db.models import fields
from reversion_compare.helpers import patch_admin 
import logging
from . import forms as bro_forms
from . import models as bro_models


logger = logging.getLogger(__name__)


def _register(model, admin_class):
    admin.site.register(model, admin_class)


def get_searchable_fields(model_class):
    return [
        f.name
        for f in model_class._meta.fields
        if isinstance(f, (fields.CharField, fields.AutoField))
    ]


class CompanyAdmin(admin.ModelAdmin):
    form = bro_forms.CompanyForm

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

class BROProjectAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "project_number",
        "owner",
    )

    list_filter = (
        "owner",
        "project_number",
    )

_register(bro_models.Company, CompanyAdmin)
_register(bro_models.BROProject, BROProjectAdmin)

patch_admin(bro_models.Company)
patch_admin(bro_models.BROProject)
