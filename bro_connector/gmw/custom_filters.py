from admin_auto_filters.filters import AutocompleteFilter
from django.contrib.admin import SimpleListFilter
from .models import Event


class EventTypeFilter(SimpleListFilter):
    title = "Event Type"  # Display name in the admin filter sidebar
    parameter_name = "event_type"  # The URL query parameter

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples, where each tuple contains a value for the query
        parameter and a human-readable name for the option.
        """
        event_names = Event.objects.values_list("event_name", flat=True).distinct()
        return [(event_name, event_name) for event_name in event_names]

    def queryset(self, request, queryset):
        """
        Filter the queryset based on the event_name that corresponds to event_id.
        """
        print(self.value())
        event_name = self.value()
        events = Event.objects.filter(event_name=event_name)
        ids = list(events.values_list("change_id", flat=True))
        print(ids)
        if self.value():  # if a filter option is selected
            return queryset.filter(event_id__in=ids)
        return queryset


class WellFilter(AutocompleteFilter):
    template = "admin/autocomplete_filter.html"
    title = "Put"
    field_name = "groundwater_monitoring_well_static"
    is_placeholder_title = True


class WellDynamicFilter(AutocompleteFilter):
    template = "admin/autocomplete_filter.html"
    title = "Putgeschiedenis"
    field_name = "groundwater_monitoring_well_dynamic"
    is_placeholder_title = True


class TubeFilter(AutocompleteFilter):
    template = "admin/autocomplete_filter.html"
    title = "Filter"
    field_name = "groundwater_monitoring_tube_static"
    is_placeholder_title = True


class TubeDynamicFilter(AutocompleteFilter):
    template = "admin/autocomplete_filter.html"
    title = "Filtergeschiedenis"
    field_name = "groundwater_monitoring_tube_dynamic"
    is_placeholder_title = True
