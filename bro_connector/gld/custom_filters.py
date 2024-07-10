from admin_auto_filters.filters import AutocompleteFilter
from django.contrib import admin


class GLDFilter(AutocompleteFilter):
    title = "groundwater level dossier"
    field_name = "groundwater_level_dossier"
    is_placeholder_title = True

class ObservationFilter(AutocompleteFilter):
    title = "observation"
    field_name = "observation"
    is_placeholder_title = True

class TubeFilter(AutocompleteFilter):
    title = "groundwater monitoring tube"
    field_name = "groundwater_monitoring_tube"
    is_placeholder_title = True

class PropertyFilterMixin:
    def _evaluate_property(self, queryset, property_name, value):
        filtered_ids = [
            obj.groundwater_level_dossier_id for obj in queryset if getattr(obj, property_name) == value
        ]
        return queryset.filter(groundwater_level_dossier_id__in=filtered_ids)

class CompletelyDeliveredFilter(admin.SimpleListFilter, PropertyFilterMixin):
    title = 'Fully Delivered'
    parameter_name = 'completely_delivered'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return self._evaluate_property(queryset, 'completely_delivered', True)
        elif self.value() == 'no':
            return self._evaluate_property(queryset, 'completely_delivered', False)
        return queryset

class HasOpenObservationFilter(admin.SimpleListFilter, PropertyFilterMixin):
    title = 'Active Measurements'
    parameter_name = 'has_open_observation'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return self._evaluate_property(queryset, 'has_open_observation', True)
        elif self.value() == 'no':
            return self._evaluate_property(queryset, 'has_open_observation', False)
        return queryset