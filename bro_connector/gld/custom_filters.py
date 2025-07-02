from admin_auto_filters.filters import AutocompleteFilter
from django.contrib.admin import SimpleListFilter
from django.contrib import admin
from bro.models import Organisation


class GLDFilter(AutocompleteFilter):
    title = "GLD"
    field_name = "groundwater_level_dossier"
    is_placeholder_title = True


class ObservationFilter(AutocompleteFilter):
    title = "Observatie"
    field_name = "observation"
    is_placeholder_title = True


class OrganisationFilter(SimpleListFilter):
    title = "Organisatie"
    parameter_name = "responsible_party"

    def lookups(self, request, model_admin):
        # Autocomplete-like filtering is trickier; for now, just do simple lookups
        return [(org.pk, org.name) for org in Organisation.objects.all()]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                observation_metadata__responsible_party__id=self.value()
            )
        return queryset


class TubeFilter(AutocompleteFilter):
    title = "Filter"
    field_name = "groundwater_monitoring_tube"
    is_placeholder_title = True


class PropertyFilterMixin:
    def _evaluate_property(self, queryset, property_name, value):
        filtered_ids = [
            obj.groundwater_level_dossier_id
            for obj in queryset
            if getattr(obj, property_name) == value
        ]
        return queryset.filter(groundwater_level_dossier_id__in=filtered_ids)


class CompletelyDeliveredFilter(admin.SimpleListFilter, PropertyFilterMixin):
    title = "Volledig geleverd"
    parameter_name = "completely_delivered"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Yes"),
            ("no", "No"),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return self._evaluate_property(queryset, "completely_delivered", True)
        elif self.value() == "no":
            return self._evaluate_property(queryset, "completely_delivered", False)
        return queryset


class HasOpenObservationFilter(admin.SimpleListFilter, PropertyFilterMixin):
    title = "Actieve metingen"
    parameter_name = "has_open_observation"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Yes"),
            ("no", "No"),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return self._evaluate_property(queryset, "has_open_observation", True)
        elif self.value() == "no":
            return self._evaluate_property(queryset, "has_open_observation", False)
        return queryset
