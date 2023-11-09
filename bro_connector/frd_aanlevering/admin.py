from django.contrib import admin
from .models import *

def _register(model, admin_class):
    admin.site.register(model, admin_class)


class FormationResistanceDossierAdmin(admin.ModelAdmin):

    list_display = (
        "id",
    )
    list_filter = (

    )

_register(FormationResistanceDossier, FormationResistanceDossierAdmin)