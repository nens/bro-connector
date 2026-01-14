import logging

import numpy as np
import pandas as pd
from dash import Dash, Input, Output, State, no_update
from dash.exceptions import PreventUpdate

from gwdatalens.app.constants import ColumnNames, ConfigDefaults, UnitConversion
from gwdatalens.app.exceptions import (
    EmptyResultError,
    QueryError,
    TimeSeriesError,
)
from gwdatalens.app.messages import ErrorMessages, SuccessMessages, t_
from gwdatalens.app.src.components import (
    ids,
)
from gwdatalens.app.src.components.overview_chart import plot_obs
from gwdatalens.app.src.components.tab_corrections import plot_well_cross_section
from gwdatalens.app.src.data.data_manager import DataManager
from gwdatalens.app.src.services import TimeSeriesService, WellService
from gwdatalens.app.src.utils import log_callback
from gwdatalens.app.src.utils.callback_helpers import (
    AlertBuilder,
    CallbackResponse,
    EmptyFigure,
    dataframe_to_records,
    extract_trigger_id,
    get_callback_context,
)
from gwdatalens.app.validators import validate_not_empty

logger = logging.getLogger(__name__)


def register_correction_callbacks(app: Dash, data: DataManager):
    # Initialize services once per registration
    ts_service = TimeSeriesService(data.db)
    well_service = WellService(data.db)

    @app.callback(
        Output(ids.CORRECTION_SERIES_CHART, "figure"),
        Input(ids.CORRECTIONS_DROPDOWN_SELECTOR, "value"),
        State(ids.CORRECTIONS_DROPDOWN_SELECTOR, "value"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def plot_corrections_time_series(
        value: int | None, value_state: int | None
    ) -> dict:
        """Plot time series for selected well.

        Parameters
        ----------
        value : str or None
            The internal ID of a monitoring location. If None, returns
            empty figure indicating no selection.

        Returns
        -------
        dict
            Plot figure or empty figure message
        """
        if value is None and value_state is None:
            return EmptyFigure.no_selection()
        if value is None and value_state is not None:
            value = value_state

        try:
            names = well_service.get_tubes_for_location(value)
            validate_not_empty(names, context="tubes for location")
            wids = well_service.get_tube_ids_from_names(names)

            if not wids or not ts_service.check_if_wells_have_data(wids):
                return EmptyFigure.no_data()

            return plot_obs(wids, data, plot_manual_obs=True)
        except EmptyResultError:
            logger.warning("No tubes found for location %s", value)
            return EmptyFigure.with_message(t_(ErrorMessages.NO_LOCATIONS))
        except QueryError as e:
            logger.error(
                "Database query failed for location %s: %s", value, e, exc_info=True
            )
            return EmptyFigure.with_message(t_(ErrorMessages.DATABASE_ERROR))
        except Exception as e:
            logger.error(
                "Unexpected error plotting corrections time series: %s",
                e,
                exc_info=True,
            )
            return EmptyFigure.with_message(t_(ErrorMessages.DATA_LOAD_FAILED))

    @app.callback(
        Output(ids.WELL_CONFIGURATION_PLOT, "figure"),
        Output(ids.CORRECTIONS_TUBE_TABLE, "data"),
        Input(ids.CORRECTIONS_DROPDOWN_SELECTOR, "value"),
        State(ids.CORRECTIONS_DROPDOWN_SELECTOR, "value"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def plot_well_configuration(
        value: int | None, value_state: int | None
    ) -> tuple[dict, list[dict]]:
        """Plot well configuration and tube metadata.

        Parameters
        ----------
        value : str or None
            The internal ID of a monitoring location. If None, returns
            empty figure and no data.

        Returns
        -------
        tuple
            (figure, table_data) where figure shows cross-section plot
            and table_data shows tube metadata
        """
        if value is None and value_state is None:
            return (
                CallbackResponse()
                .add_figure(
                    EmptyFigure.with_message(t_(ErrorMessages.NO_WELLS_SELECTED))
                )
                .add(no_update)
                .build()
            )
        if value is None and value_state is not None:
            value = value_state

        try:
            df = well_service.get_well_configuration(value)
            validate_not_empty(df, context="well configuration")

            table_data = dataframe_to_records(df.reset_index())
            return (
                CallbackResponse()
                .add_figure(plot_well_cross_section(df))
                .add(table_data)
                .build()
            )
        except EmptyResultError:
            logger.exception("No well configuration data for location %s", value)
            well_display = value if value is not None else "?"
            return (
                CallbackResponse()
                .add_figure(
                    EmptyFigure.with_message(
                        t_(ErrorMessages.NO_WELL_CONFIGURATION_DATA, well=well_display)
                    )
                )
                .add([])
                .build()
            )
        except QueryError as e:
            logger.exception("Database query failed for location %s: %s", value, e)
            return (
                CallbackResponse()
                .add_figure(EmptyFigure.with_message(t_(ErrorMessages.DATABASE_ERROR)))
                .add([])
                .build()
            )
        except Exception as e:
            logger.exception("Unexpected error plotting well configuration: %s", e)
            return (
                CallbackResponse()
                .add_figure(
                    EmptyFigure.with_message(t_(ErrorMessages.DATA_LOAD_FAILED))
                )
                .add([])
                .build()
            )

    # Callback 1: Update well dropdowns and handle clear button
    @app.callback(
        Output(ids.CORRECTIONS_WELL1_DROPDOWN, "options"),
        Output(ids.CORRECTIONS_WELL2_DROPDOWN, "options"),
        Output(ids.CORRECTIONS_WELL1_DROPDOWN, "value"),
        Output(ids.CORRECTIONS_WELL2_DROPDOWN, "value"),
        Input(ids.CORRECTIONS_DROPDOWN_SELECTOR, "value"),
        Input(ids.CORRECTIONS_CLEAR_SELECTION_BUTTON, "n_clicks"),
        State(ids.CORRECTIONS_WELL1_DROPDOWN, "value"),
        State(ids.CORRECTIONS_WELL2_DROPDOWN, "value"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def update_well_dropdowns(wid, _clear_clicks, _well1_val, _well2_val, **kwargs):
        """Update well selection dropdowns when location selected or clear clicked.

        Parameters
        ----------
        wid : str or None
            The internal id of the selected location.
        _clear_clicks : int
            Number of clicks on clear button.
        well1_val : str or None
            Current value of well1 dropdown.
        well2_val : str or None
            Current value of well2 dropdown.

        Returns
        -------
        tuple
            Options for both dropdowns and values.
        """
        ctx_obj = get_callback_context(**kwargs)
        if not ctx_obj.triggered:
            raise PreventUpdate

        trigger_id = extract_trigger_id(ctx_obj, parse_json=False)

        if trigger_id == ids.CORRECTIONS_CLEAR_SELECTION_BUTTON:
            if wid is None:
                return [], [], None, None

            options = well_service.get_tubes_as_dropdown_options(wid)
            return options, options, None, None

        if wid is None:
            return [], [], None, None

        options = well_service.get_tubes_as_dropdown_options(wid)
        return options, options, None, None

    # Callback 2: Fetch and merge observations when wells are selected

    @app.callback(
        Output(ids.CORRECTIONS_OBSERVATIONS_TABLE_1, "data"),
        Output(ids.CORRECTIONS_OBSERVATIONS_TABLE_2, "data"),
        Output(ids.CORRECTIONS_ORIGINAL_DATA_STORE, "data"),
        Input(ids.CORRECTIONS_WELL1_DROPDOWN, "value"),
        Input(ids.CORRECTIONS_WELL2_DROPDOWN, "value"),
        Input(ids.CORRECTIONS_RESET_TRIGGER_STORE, "data"),
        Input(ids.CORRECTIONS_COMMIT_TRIGGER_STORE, "data"),
        State(ids.CORRECTIONS_WELL1_DROPDOWN, "value"),
        State(ids.CORRECTIONS_WELL2_DROPDOWN, "value"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def load_observations(
        well1_id,
        well2_id,
        reset_trigger,
        commit_trigger,
        state_well1_id,
        state_well2_id,
        **kwargs,
    ):
        """Load observations from selected well(s) into separate aligned tables.

        Loads observations from one or two wells. When two wells are selected,
        observations are aligned by datetime (outer join) so both tables show
        the same timestamp rows. Handles reset and commit triggers by reloading
        fresh data from the database.

        Parameters
        ----------
        well1_id : str or None
            The internal id of the first well.
        well2_id : str or None
            The internal id of the second well.
        reset_trigger : dict or None
            Trigger from reset button.
        commit_trigger : dict or None
            Trigger from commit button.
        state_well1_id : str or None
            Current state of first well dropdown (for reload context).
        state_well2_id : str or None
            Current state of second well dropdown (for reload context).

        Returns
        -------
        tuple
            (table1_data, table2_data, original_data_store)
        """
        ctx_obj = get_callback_context(**kwargs)
        if not ctx_obj.triggered:
            return [], [], None

        trigger_id = extract_trigger_id(ctx_obj, parse_json=False)

        # Handle reset or commit triggers - reload fresh data from database
        if (trigger_id == ids.CORRECTIONS_RESET_TRIGGER_STORE and reset_trigger) or (
            trigger_id == ids.CORRECTIONS_COMMIT_TRIGGER_STORE and commit_trigger
        ):
            well1_id = state_well1_id
            well2_id = state_well2_id

        # If neither well is selected, clear tables
        if well1_id is None and well2_id is None:
            return [], [], None

        # If same well selected twice, treat as single well
        if well1_id == well2_id and well1_id is not None:
            well2_id = None

        try:
            obs_dict = {}

            for wid, key in [(well1_id, "table1"), (well2_id, "table2")]:
                if wid is None:
                    continue
                obs = ts_service.get_series_for_observation_well(
                    wid, observation_type="controlemeting"
                )
                if obs is not None and not obs.empty:
                    obs = obs.loc[
                        :,
                        [
                            ColumnNames.FIELD_VALUE,
                            ColumnNames.CALCULATED_VALUE,
                            ColumnNames.INITIAL_CALCULATED_VALUE,
                            "correction_reason",
                            "measurement_tvp_id",
                        ],
                    ].dropna(
                        how="all",
                        subset=[ColumnNames.FIELD_VALUE, ColumnNames.CALCULATED_VALUE],
                    )
                    obs.index.name = "datetime"
                    obs_dict[key] = obs

            # If no data loaded, return empty
            if not obs_dict:
                return [], [], None

            obs1 = obs_dict.get("table1")
            obs2 = obs_dict.get("table2")

            # Align indices using outer join so both tables show same datetimes
            if obs1 is not None and obs2 is not None:
                all_datetimes = obs1.index.union(obs2.index)
                obs1 = obs1.reindex(all_datetimes)
                obs2 = obs2.reindex(all_datetimes)

            table1_data = (
                _prepare_observation_table_data(obs1) if obs1 is not None else []
            )
            table2_data = (
                _prepare_observation_table_data(obs2) if obs2 is not None else []
            )

            original_data = {
                "table1": table1_data,
                "table2": table2_data,
                "timestamp": pd.Timestamp.now().isoformat(),
            }

            return table1_data, table2_data, original_data

        except TimeSeriesError as e:
            logger.exception("Error loading observations: %s", e)
            return [], [], None

    # Callback 2b: Enable/disable commit and reset buttons based on dropdown selections
    @app.callback(
        Output(ids.CORRECTIONS_COMMIT_BUTTON, "disabled"),
        Output(ids.CORRECTIONS_RESET_BUTTON, "disabled"),
        Input(ids.CORRECTIONS_WELL1_DROPDOWN, "value"),
        Input(ids.CORRECTIONS_WELL2_DROPDOWN, "value"),
        Input(ids.CORRECTIONS_OBSERVATIONS_TABLE_1, "data"),
        Input(ids.CORRECTIONS_OBSERVATIONS_TABLE_2, "data"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def enable_correction_buttons(well1_id, well2_id, table1_data, table2_data):
        """Enable commit and reset buttons when wells selected and data is available.

        Parameters
        ----------
        well1_id : str or None
            The internal id of the first well.
        well2_id : str or None
            The internal id of the second well.
        table1_data : list or None
            Data from observation table 1.
        table2_data : list or None
            Data from observation table 2.

        Returns
        -------
        tuple
            (commit_disabled, reset_disabled) boolean values
        """
        # Enable buttons only if at least one well is selected and has data
        has_well_selected = well1_id is not None or well2_id is not None
        has_data = (table1_data and len(table1_data) > 0) or (
            table2_data and len(table2_data) > 0
        )

        # Both commit and reset buttons enabled if well selected and data available
        buttons_disabled = not (has_well_selected and has_data)

        return buttons_disabled, buttons_disabled

    # Callback 3: Track edits and manage button states
    @app.callback(
        Output(ids.CORRECTIONS_OBSERVATIONS_TABLE_1, "style_data_conditional"),
        Output(ids.CORRECTIONS_OBSERVATIONS_TABLE_2, "style_data_conditional"),
        Input(ids.CORRECTIONS_OBSERVATIONS_TABLE_1, "data"),
        Input(ids.CORRECTIONS_OBSERVATIONS_TABLE_2, "data"),
        State(ids.CORRECTIONS_ORIGINAL_DATA_STORE, "data"),
        State(ids.CORRECTIONS_EDIT_HISTORY_STORE, "data"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def track_edits(table1_data, table2_data, original_data, _edit_history):
        """Track edits in both observation tables and apply visual styling.

        Compares current table data with original data to identify edited cells.
        Applies yellow background (#fff3cd) to edited cells and greyed-out styling
        to empty alignment placeholder rows.

        Parameters
        ----------
        table1_data : list[dict]
            Current data from table 1.
        table2_data : list[dict]
            Current data from table 2.
        original_data : dict
            Original data store with table1/table2 keys.
        edit_history : dict
            Edit history from CORRECTIONS_EDIT_HISTORY_STORE.

        Returns
        -------
        tuple
            (style_table1, style_table2) where each is a list of dicts
            for style_data_conditional.
        """
        style_table1 = []
        style_table2 = []

        def _normalize_value(val, col):
            """Normalize values for comparison.

            - Treat empty strings and whitespace as None
            - For numeric columns (calculated_value, field_value, corrected_value),
              cast string numbers to float when possible
            - Leave comments as-is but trim whitespace for emptiness checks
            """
            if val is None:
                return None
            # Empty string or whitespace -> None
            if isinstance(val, str) and val.strip() == "":
                return None

            if col in {
                ColumnNames.CALCULATED_VALUE,
                ColumnNames.FIELD_VALUE,
                "corrected_value",
            }:
                # Consider NaN as None
                try:
                    # If already numeric, keep
                    if isinstance(val, (int, float)):
                        return val if not pd.isna(val) else None
                    # Try parsing string number
                    parsed = float(str(val))
                    return parsed
                except TypeError:
                    # Non-parsable -> treat as None
                    return None

            if col == "comment":
                # Normalize whitespace-only comments to None
                return val.strip() if isinstance(val, str) else val

            return val

        def _equal_values(a, b, col):
            na = _normalize_value(a, col)
            nb = _normalize_value(b, col)
            # Treat None/NaN equivalently
            if na is None and (nb is None or pd.isna(nb)):
                return True
            if nb is None and (na is None or pd.isna(na)):
                return True
            # Numeric tolerance (optional): exact compare is fine for edited cells
            return na == nb

        if not original_data:
            return style_table1, style_table2

        original_table1 = original_data.get("table1", [])
        original_table2 = original_data.get("table2", [])

        def is_empty_row(row):
            """Check if a row is an alignment placeholder (all editable cols empty)."""
            calculated_val = row.get(ColumnNames.CALCULATED_VALUE)
            field_val = row.get(ColumnNames.FIELD_VALUE)
            corrected_val = row.get("corrected_value")
            comment_val = row.get("comment", "")

            # Treat empty strings like None for emptiness check
            def empty(val, col):
                n = _normalize_value(val, col)
                return n is None or pd.isna(n)

            return (
                empty(calculated_val, ColumnNames.CALCULATED_VALUE)
                and empty(field_val, ColumnNames.FIELD_VALUE)
                and empty(corrected_val, "corrected_value")
                and (
                    comment_val is None
                    or (isinstance(comment_val, str) and comment_val.strip() == "")
                )
            )

        # Track edits and empty rows in table 1
        if table1_data and original_table1:
            for row_idx, current_row in enumerate(table1_data):
                # Check if this is an empty alignment placeholder row
                if is_empty_row(current_row):
                    # Grey out the entire row and disable interactions
                    style_table1.append(
                        {
                            "if": {"row_index": row_idx},
                            "backgroundColor": "#f0f0f0",
                            "color": "#999999",
                            "opacity": 0.6,
                            "pointerEvents": "none",
                            "cursor": "not-allowed",
                        }
                    )
                elif row_idx < len(original_table1):
                    original_row = original_table1[row_idx]
                    # Check each editable column for edits
                    for col in [
                        ColumnNames.CALCULATED_VALUE,
                        ColumnNames.FIELD_VALUE,
                        "corrected_value",
                        "comment",
                    ]:
                        current_val = current_row.get(col)
                        original_val = original_row.get(col)
                        # Compare normalized values to determine actual edits
                        if not _equal_values(current_val, original_val, col):
                            style_table1.append(
                                {
                                    "if": {
                                        "row_index": row_idx,
                                        "column_id": col,
                                    },
                                    "backgroundColor": "#fff3cd",
                                }
                            )

        # Track edits and empty rows in table 2
        if table2_data and original_table2:
            for row_idx, current_row in enumerate(table2_data):
                # Check if this is an empty alignment placeholder row
                if is_empty_row(current_row):
                    # Grey out the entire row and disable interactions
                    style_table2.append(
                        {
                            "if": {"row_index": row_idx},
                            "backgroundColor": "#f0f0f0",
                            "color": "#999999",
                            "opacity": 0.6,
                            "pointerEvents": "none",
                            "cursor": "not-allowed",
                        }
                    )
                elif row_idx < len(original_table2):
                    original_row = original_table2[row_idx]
                    # Check each editable column for edits
                    for col in [
                        ColumnNames.CALCULATED_VALUE,
                        ColumnNames.FIELD_VALUE,
                        "corrected_value",
                        "comment",
                    ]:
                        current_val = current_row.get(col)
                        original_val = original_row.get(col)
                        # Compare normalized values to determine actual edits
                        if not _equal_values(current_val, original_val, col):
                            style_table2.append(
                                {
                                    "if": {
                                        "row_index": row_idx,
                                        "column_id": col,
                                    },
                                    "backgroundColor": "#fff3cd",
                                }
                            )

        return style_table1, style_table2

    # Callback 4: Commit or reset corrections (single callback handling both operations)
    @app.callback(
        Output(ids.ALERT_STATUS_CORRECTIONS, "data"),
        Output(ids.CORRECTIONS_COMMIT_TRIGGER_STORE, "data"),
        Output(ids.CORRECTIONS_RESET_TRIGGER_STORE, "data"),
        Input(ids.CORRECTIONS_COMMIT_BUTTON, "n_clicks"),
        Input(ids.CORRECTIONS_RESET_BUTTON, "n_clicks"),
        State(ids.CORRECTIONS_OBSERVATIONS_TABLE_1, "data"),
        State(ids.CORRECTIONS_OBSERVATIONS_TABLE_2, "data"),
        State(ids.CORRECTIONS_ORIGINAL_DATA_STORE, "data"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def commit_or_reset_corrections(
        _commit_clicks, _reset_clicks, table1_data, table2_data, original_data, **kwargs
    ):
        """Commit or reset corrections based on which button was clicked.

        This callback handles both commit and reset operations, using callback_context
        to determine which button triggered the callback.

        Parameters
        ----------
        _commit_clicks : int
            Number of times commit button clicked.
        _reset_clicks : int
            Number of times reset button clicked.
        table1_data : list
            Current table 1 data with edits.
        table2_data : list
            Current table 2 data with edits.
        original_data : dict
            Original data with table1/table2 keys.

        Returns
        -------
        tuple
            (alert_data, commit_trigger, reset_trigger)
        """
        ctx_obj = get_callback_context(**kwargs)

        if not ctx_obj.triggered:
            return no_update, no_update, no_update

        # Determine which button was clicked
        trigger_id = ctx_obj.triggered_id

        if trigger_id == ids.CORRECTIONS_COMMIT_BUTTON:
            return _handle_commit_corrections(table1_data, table2_data, original_data)
        elif trigger_id == ids.CORRECTIONS_RESET_BUTTON:
            return _handle_reset_corrections(table1_data, table2_data, original_data)

        return no_update, no_update, no_update

    def _handle_commit_corrections(table1_data, table2_data, original_data):
        """Handle committing corrections to the database.

        Parameters
        ----------
        table1_data : list
            Current table 1 data with edits.
        table2_data : list
            Current table 2 data with edits.
        original_data : dict
            Original data with table1/table2 keys.

        Returns
        -------
        tuple
            (alert_data, commit_trigger, no_update)
        """
        if not original_data or (not table1_data and not table2_data):
            return (
                CallbackResponse()
                .add(AlertBuilder.no_alert())
                .add(no_update)
                .add(no_update)
                .build()
            )

        def _normalize_value(val, col):
            """Normalize values for comparison."""
            if val is None:
                return None
            if isinstance(val, str) and val.strip() == "":
                return None
            if col in {
                ColumnNames.CALCULATED_VALUE,
                ColumnNames.FIELD_VALUE,
                "corrected_value",
            }:
                try:
                    if isinstance(val, (int, float)):
                        return val if not pd.isna(val) else None
                    parsed = float(str(val))
                    return parsed
                except Exception:
                    return None
            if col == "comment":
                return val.strip() if isinstance(val, str) else val
            return val

        def _equal_values(a, b, col):
            na = _normalize_value(a, col)
            nb = _normalize_value(b, col)
            if na is None and (nb is None or pd.isna(nb)):
                return True
            if nb is None and (na is None or pd.isna(na)):
                return True
            return na == nb

        try:
            corrections_to_save = []
            original_table1 = original_data.get("table1", [])
            original_table2 = original_data.get("table2", [])

            # Collect corrections from table 1
            if table1_data and original_table1:
                for row_idx, current_row in enumerate(table1_data):
                    if row_idx < len(original_table1):
                        original_row = original_table1[row_idx]
                        # Check if corrected_value or comment changed
                        corrected_changed = not _equal_values(
                            current_row.get("corrected_value"),
                            original_row.get("corrected_value"),
                            "corrected_value",
                        )
                        comment_changed = not _equal_values(
                            current_row.get("comment"),
                            original_row.get("comment"),
                            "comment",
                        )

                        if corrected_changed or comment_changed:
                            # Only save if corrected_value is provided
                            corrected_val = _normalize_value(
                                current_row.get("corrected_value"), "corrected_value"
                            )
                            if corrected_val is not None:
                                corrections_to_save.append(
                                    {
                                        "measurement_tvp_id": current_row[
                                            "measurement_tvp_id"
                                        ],
                                        "original_calculated_value": _normalize_value(
                                            original_row.get(
                                                ColumnNames.CALCULATED_VALUE
                                            ),
                                            ColumnNames.CALCULATED_VALUE,
                                        ),
                                        "corrected_value": corrected_val,
                                        "comment": current_row.get("comment", ""),
                                    }
                                )

            # Collect corrections from table 2
            if table2_data and original_table2:
                for row_idx, current_row in enumerate(table2_data):
                    if row_idx < len(original_table2):
                        original_row = original_table2[row_idx]
                        # Check if corrected_value or comment changed
                        corrected_changed = not _equal_values(
                            current_row.get("corrected_value"),
                            original_row.get("corrected_value"),
                            "corrected_value",
                        )
                        comment_changed = not _equal_values(
                            current_row.get("comment"),
                            original_row.get("comment"),
                            "comment",
                        )

                        if corrected_changed or comment_changed:
                            # Only save if corrected_value is provided
                            corrected_val = _normalize_value(
                                current_row.get("corrected_value"), "corrected_value"
                            )
                            if corrected_val is not None:
                                corrections_to_save.append(
                                    {
                                        "measurement_tvp_id": current_row[
                                            "measurement_tvp_id"
                                        ],
                                        "original_calculated_value": _normalize_value(
                                            original_row.get(
                                                ColumnNames.CALCULATED_VALUE
                                            ),
                                            ColumnNames.CALCULATED_VALUE,
                                        ),
                                        "corrected_value": corrected_val,
                                        "comment": current_row.get("comment", ""),
                                    }
                                )

            if len(corrections_to_save) == 0:
                return (
                    CallbackResponse()
                    .add(AlertBuilder.no_alert())
                    .add(no_update)
                    .add(no_update)
                    .build()
                )

            # Save corrections to database
            corrections_df = pd.DataFrame(corrections_to_save)
            ts_service.save_correction(corrections_df)

            # Prepare trigger store data to reload fresh data
            trigger_data = {
                "original": original_data,
                "timestamp": pd.Timestamp.now().isoformat(),
            }

            alert = AlertBuilder.success(
                t_(
                    SuccessMessages.CORRECTIONS_COMMITTED,
                    count=len(corrections_to_save),
                )
            )

            return (
                CallbackResponse().add(alert).add(trigger_data).add(no_update).build()
            )

        except Exception as e:
            logger.error("Error committing corrections", exc_info=True)
            alert = AlertBuilder.danger(
                t_(ErrorMessages.CORRECTIONS_COMMIT_FAILED, error=str(e))
            )
            return CallbackResponse().add(alert).add(no_update).add(no_update).build()

    def _handle_reset_corrections(table1_data, table2_data, original_data):
        """Handle resetting corrections in the database.

        Parameters
        ----------
        table1_data : list
            Current table 1 data.
        table2_data : list
            Current table 2 data.
        original_data : dict
            Original data from store.

        Returns
        -------
        tuple
            (alert_data, no_update, reset_trigger)
        """
        if not table1_data and not table2_data:
            return (
                CallbackResponse()
                .add(AlertBuilder.no_alert())
                .add(no_update)
                .add(no_update)
                .build()
            )

        try:
            corrections_to_reset = []

            # Collect corrections to reset from table 1
            if table1_data:
                for row in table1_data:
                    # Only reset if value_to_be_corrected is not null
                    # (meaning it was corrected)
                    if row.get(
                        ColumnNames.INITIAL_CALCULATED_VALUE
                    ) is not None and not pd.isna(
                        row.get(ColumnNames.INITIAL_CALCULATED_VALUE)
                    ):
                        corrections_to_reset.append(
                            {
                                "measurement_tvp_id": row["measurement_tvp_id"],
                                ColumnNames.INITIAL_CALCULATED_VALUE: row[
                                    ColumnNames.INITIAL_CALCULATED_VALUE
                                ],
                            }
                        )

            # Collect corrections to reset from table 2
            if table2_data:
                for row in table2_data:
                    # Only reset if value_to_be_corrected is not null
                    # (meaning it was corrected)
                    if row.get(
                        ColumnNames.INITIAL_CALCULATED_VALUE
                    ) is not None and not pd.isna(
                        row.get(ColumnNames.INITIAL_CALCULATED_VALUE)
                    ):
                        corrections_to_reset.append(
                            {
                                "measurement_tvp_id": row["measurement_tvp_id"],
                                ColumnNames.INITIAL_CALCULATED_VALUE: row[
                                    ColumnNames.INITIAL_CALCULATED_VALUE
                                ],
                            }
                        )

            if len(corrections_to_reset) == 0:
                return (
                    CallbackResponse()
                    .add(AlertBuilder.no_alert())
                    .add(no_update)
                    .add(no_update)
                    .build()
                )

            # Reset corrections in database
            corrections_df = pd.DataFrame(corrections_to_reset)
            ts_service.reset_correction(corrections_df)

            # Prepare trigger store data to reload fresh data
            trigger_data = {
                "original": original_data,
                "timestamp": pd.Timestamp.now().isoformat(),
            }

            alert = AlertBuilder.success(
                t_(SuccessMessages.CORRECTIONS_RESET, count=len(corrections_to_reset))
            )

            return (
                CallbackResponse().add(alert).add(no_update).add(trigger_data).build()
            )

        except Exception as e:
            logger.error("Error resetting corrections", exc_info=True)
            alert = AlertBuilder.danger(
                t_(ErrorMessages.CORRECTIONS_RESET_FAILED, error=str(e))
            )
            return CallbackResponse().add(alert).add(no_update).add(no_update).build()

    # Callback: Calculate groundwater level conversions
    @app.callback(
        Output(ids.CORRECTIONS_OBSERVATION_CM_INPUT, "value"),
        Output(ids.CORRECTIONS_OBSERVATION_MNAP_INPUT, "value"),
        Input(ids.CORRECTIONS_BKB_INPUT, "value"),
        Input(ids.CORRECTIONS_OBSERVATION_CM_INPUT, "value"),
        Input(ids.CORRECTIONS_OBSERVATION_MNAP_INPUT, "value"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def calculate_groundwater_level(bkb, obs_cm, obs_mnap, **kwargs):
        """Calculate groundwater level conversions between cm and m NAP.

        Formula: BKB (m NAP) - Observation (cm) / 100 = Observation (m NAP)

        Parameters
        ----------
        bkb : float or None
            Top of tube elevation in m NAP.
        obs_cm : float or None
            Observation in cm below top of tube.
        obs_mnap : float or None
            Observation in m NAP.

        Returns
        -------
        tuple
            (obs_cm, obs_mnap) - updated values based on which field changed
        """
        ctx_obj = get_callback_context(**kwargs)
        if not ctx_obj.triggered:
            return no_update, no_update

        trigger_id = extract_trigger_id(ctx_obj, parse_json=False)

        # If BKB changed and we have one of the observation values, recalculate
        if trigger_id == ids.CORRECTIONS_BKB_INPUT:
            if bkb is not None:
                if obs_cm is not None:
                    # Recalculate m NAP from cm
                    new_mnap = bkb - (obs_cm * UnitConversion.CM_TO_M)
                    return no_update, round(new_mnap, 4)
                elif obs_mnap is not None:
                    # Recalculate cm from m NAP
                    new_cm = (bkb - obs_mnap) * UnitConversion.M_TO_CM
                    return round(new_cm, 2), no_update
            return no_update, no_update

        # If observation in cm changed, calculate m NAP
        elif trigger_id == ids.CORRECTIONS_OBSERVATION_CM_INPUT:
            if bkb is not None and obs_cm is not None:
                new_mnap = bkb - (obs_cm * UnitConversion.CM_TO_M)
                return no_update, round(new_mnap, 4)
            return no_update, no_update

        # If observation in m NAP changed, calculate cm
        elif trigger_id == ids.CORRECTIONS_OBSERVATION_MNAP_INPUT:
            if bkb is not None and obs_mnap is not None:
                new_cm = (bkb - obs_mnap) * UnitConversion.M_TO_CM
                return round(new_cm, 2), no_update
            return no_update, no_update

        return no_update, no_update


def _prepare_observation_table_data(obs_df):
    """Prepare observation DataFrame for table display."""
    try:
        validate_not_empty(obs_df, context="observation data for table")
    except EmptyResultError:
        return []

    table_df = obs_df.reset_index()

    # Display original calculated value when correction exists
    current_calculated = table_df[ColumnNames.CALCULATED_VALUE]
    table_df[ColumnNames.CALCULATED_VALUE] = np.where(
        table_df[ColumnNames.INITIAL_CALCULATED_VALUE].notna(),
        table_df[ColumnNames.INITIAL_CALCULATED_VALUE],
        current_calculated,
    )

    # Show corrected value if it exists; blank otherwise
    table_df[ColumnNames.CORRECTED_VALUE] = np.where(
        table_df[ColumnNames.INITIAL_CALCULATED_VALUE].notna(),
        current_calculated,
        np.nan,
    )

    # Show correction reason in comment column if it exists
    table_df[ColumnNames.COMMENT] = table_df[ColumnNames.CORRECTION_REASON].fillna("")

    # Format datetime
    table_df[ColumnNames.DATETIME] = table_df[ColumnNames.DATETIME].dt.strftime(
        ConfigDefaults.DATETIME_FORMAT
    )

    # Select columns for display
    return table_df[
        [
            ColumnNames.DATETIME,
            ColumnNames.FIELD_VALUE,
            ColumnNames.CALCULATED_VALUE,
            ColumnNames.CORRECTED_VALUE,
            ColumnNames.COMMENT,
            ColumnNames.MEASUREMENT_TVP_ID,
            ColumnNames.INITIAL_CALCULATED_VALUE,
        ]
    ].to_dict("records")
