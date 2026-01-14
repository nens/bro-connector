"""User-facing messages and error message catalog.

Centralizes all user-facing messages for consistency and easy internationalization.
"""

import i18n


def t_(key, **kwargs):
    """Translate message key with optional formatting."""
    return i18n.t(key, **kwargs)


# Error and alert messages for users (translation keys)
class ErrorMessages:
    """Error message keys for translations via i18n.t."""

    DATA_LOAD_FAILED = "general.error_data_load_failed"
    NO_WELLS_SELECTED = "general.error_no_wells_selected"
    NO_SERIES_DATA = "general.error_no_series_data"
    NO_LOCATIONS = "general.error_no_locations"
    QC_ANALYSIS_FAILED = "general.error_qc_analysis_failed"
    QC_ALL_OBSERVATIONS_CHECKED = "general.error_all_observations_checked"
    NO_MODEL_ERROR = "general.error_no_model"
    EXPORT_FAILED = "general.error_export_failed"
    DATABASE_ERROR = "general.error_database_error"
    RULESET_LOAD_ERROR = "general.error_ruleset_load_error"
    NO_QC_RESULT = "general.error_no_qc_result"
    NO_WELL_CONFIGURATION_DATA = "general.error_no_well_configuration_data"
    NO_PLOT_DATA = "general.error_no_plot_data"
    NO_DATA_SELECTION = "general.no_data_selection"
    NO_SERIES = "general.no_series"
    CORRECTIONS_COMMIT_FAILED = "general.error_corrections_commit_failed"
    CORRECTIONS_RESET_FAILED = "general.error_corrections_reset_failed"


class SuccessMessages:
    """Success message keys for translations via i18n.t."""

    RULESET_LOADED = "general.success_loaded_ruleset"
    TIMESERIES_LOADED_FROM_PASTASTORE = "general.success_loaded_timeseries_pastastore"
    TRAVAL_RUN_SUCCESS = "general.success_traval_run"
    EXPORT_SUCCESS = "general.success_export_db"
    CORRECTIONS_COMMITTED = "general.success_corrections_committed"
    CORRECTIONS_RESET = "general.success_corrections_reset"
