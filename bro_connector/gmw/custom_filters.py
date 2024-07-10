from admin_auto_filters.filters import AutocompleteFilter

class WellFilter(AutocompleteFilter):
    title = "Put"
    field_name = "groundwater_monitoring_well_static"
    is_placeholder_title = True

class WellDynamicFilter(AutocompleteFilter):
    title = "Putgeschiedenis"
    field_name = "groundwater_monitoring_well_dynamic"
    is_placeholder_title = True

class TubeFilter(AutocompleteFilter):
    title = "Filter"
    field_name = "groundwater_monitoring_tube_static"
    is_placeholder_title = True

class TubeDynamicFilter(AutocompleteFilter):
    title = "Filtergeschiedenis"
    field_name = "groundwater_monitoring_tube_dynamic"
    is_placeholder_title = True