from admin_auto_filters.filters import AutocompleteFilter


class TubeFilter(AutocompleteFilter):
    template = "admin/autocomplete_filter.html"
    title = "Filter"
    field_name = "groundwater_monitoring_tube"
    is_placeholder_title = True