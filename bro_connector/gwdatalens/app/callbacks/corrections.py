import logging

import numpy as np
import pandas as pd
from dash import Dash, Input, Output, State, no_update
from dash.exceptions import PreventUpdate
from gwdatalens.app.constants import UI, ColumnNames, ConfigDefaults, UnitConversion
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
        Input(ids.TIME_RANGE_STORE, "data"),
        Input(ids.CORRECTIONS_COMMIT_TRIGGER_STORE, "data"),
        Input(ids.CORRECTIONS_RESET_TRIGGER_STORE, "data"),
        State(ids.CORRECTIONS_DROPDOWN_SELECTOR, "value"),
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def plot_corrections_time_series(
        value: int | None,
        time_range: dict | None,
        _commit_trigger: dict | None,
        _reset_trigger: dict | None,
        value_state: int | None,
    ) -> dict:
        """Plot time series for selected well.

        Parameters
        ----------
        value : str or None
            The internal ID of a monitoring location. If None, returns
            empty figure indicating no selection.
        time_range : dict or None
            Global time-range store value with keys ``tmin`` and ``tmax``.

        Returns
        -------
        dict
            Plot figure or empty figure message
        """
        if value is None and value_state is None:
            return EmptyFigure.no_selection()
        if value is None and value_state is not None:
            value = value_state

        tmin = time_range.get("tmin") if time_range else None
        tmax = time_range.get("tmax") if time_range else None
        preset = time_range.get("preset") if time_range else None

        try:
            names = well_service.get_tubes_for_location(value)
            validate_not_empty(names, context="tubes for location")
            wids = well_service.get_tube_ids_from_names(names)

            if not wids or not ts_service.check_if_wells_have_data(wids):
                return EmptyFigure.no_data()

            return plot_obs(
                wids,
                data,
                plot_manual_obs=True,
                tmin=tmin,
                tmax=tmax,
                time_range_preset=preset,
            )
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
                return CallbackResponse().add([]).add([]).add(None).add(None).build()

            options = well_service.get_tubes_as_dropdown_options(wid)
            return (
                CallbackResponse().add(options).add(options).add(None).add(None).build()
            )

        if wid is None:
            return CallbackResponse().add([]).add([]).add(None).add(None).build()

        options = well_service.get_tubes_as_dropdown_options(wid)
        return CallbackResponse().add(options).add(options).add(None).add(None).build()

    @app.callback(
        Output(ids.CORRECTIONS_SHOW_QC_ONLY_SWITCH, "disabled"),
        Output(ids.CORRECTIONS_SHOW_QC_ONLY_SWITCH, "value"),
        Input(ids.CORRECTIONS_WELL1_DROPDOWN, "value"),
        Input(ids.CORRECTIONS_WELL2_DROPDOWN, "value"),
        Input(ids.TRAVAL_RESULT_FIGURE_STORE, "data"),
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def toggle_qc_only_switch_state(well1_id, well2_id, traval_result_figure_store):
        """Enable QC-only switch only when QC result exists for selected well(s)."""
        qc_result_wid = _extract_qc_result_wid(traval_result_figure_store)
        traval_result_df = (
            data.qc.traval_result
            if data is not None
            and getattr(data, "qc", None) is not None
            and getattr(data.qc, "traval_result", None) is not None
            else None
        )

        if traval_result_df is None or traval_result_df.empty or qc_result_wid is None:
            return True, False

        selected_wells = {wid for wid in [well1_id, well2_id] if wid is not None}
        if not selected_wells:
            return True, False

        if qc_result_wid in selected_wells:
            return False, no_update

        return True, False

    # Callback 2: Fetch and merge observations when wells are selected
    # OPTIMIZED: Only re-query DB when wells change; use cached data for date filtering
    @app.callback(
        Output(ids.CORRECTIONS_OBSERVATIONS_TABLE_1, "data"),
        Output(ids.CORRECTIONS_OBSERVATIONS_TABLE_2, "data"),
        Output(ids.CORRECTIONS_ORIGINAL_DATA_STORE, "data"),
        Input(ids.CORRECTIONS_WELL1_DROPDOWN, "value"),
        Input(ids.CORRECTIONS_WELL2_DROPDOWN, "value"),
        Input(ids.CORRECTIONS_RESET_TRIGGER_STORE, "data"),
        Input(ids.CORRECTIONS_COMMIT_TRIGGER_STORE, "data"),
        Input(ids.CORRECTIONS_DATE_RANGE_STORE, "data"),
        Input(ids.CORRECTIONS_SHOW_QC_ONLY_SWITCH, "value"),
        Input(ids.TIME_RANGE_STORE, "data"),
        State(ids.CORRECTIONS_WELL1_DROPDOWN, "value"),
        State(ids.CORRECTIONS_WELL2_DROPDOWN, "value"),
        State(ids.CORRECTIONS_ORIGINAL_DATA_STORE, "data"),
        State(ids.CORRECTIONS_EDIT_HISTORY_STORE, "data"),
        State(ids.TRAVAL_RESULT_FIGURE_STORE, "data"),
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
        date_range,
        show_qc_only,
        time_range,
        state_well1_id,
        state_well2_id,
        cached_original_data,
        edit_history,
        traval_result_figure_store,
        **kwargs,
    ):
        """Load observations from selected well(s) into separate aligned tables.

        OPTIMIZED: Detects trigger type and only queries DB when wells change.
        When only date_range changes (e.g., slider drag), uses cached data.
        Re-applies user edits to filtered results to prevent data loss.

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
        date_range : dict or None
            Date range filter with 'start' and 'end' keys.
        show_qc_only : bool or None
            Whether to show only rows with QC detection comments.
        state_well1_id : str or None
            Current state of first well dropdown (for reload context).
        state_well2_id : str or None
            Current state of second well dropdown (for reload context).
        cached_original_data : dict or None
            Previously cached full unfiltered data.
        edit_history : dict or None
            Persisted edits keyed by "table{N}:{datetime}".
        traval_result_figure_store : tuple | list | None
            Store payload containing QC result context with selected well id.

        Returns
        -------
        tuple
            (table1_data, table2_data, original_data_store)
        """
        ctx_obj = get_callback_context(**kwargs)
        if not ctx_obj.triggered:
            return CallbackResponse().add([]).add([]).add(None).build()

        trigger_id = extract_trigger_id(ctx_obj, parse_json=False)
        show_qc_only = bool(show_qc_only)

        def _reapply_edits(table_data, table_num, edit_history, well_key):
            """Re-apply persisted edits to table data by datetime key."""
            if not edit_history or not table_data:
                return table_data

            result = []
            for row in table_data:
                datetime_val = row.get("datetime")
                if not datetime_val:
                    result.append(row)
                    continue

                row_key = f"{well_key}:table{table_num}:{datetime_val}"
                row_edits = edit_history.get(row_key, {})

                if row_edits:
                    updated_row = dict(row)
                    updated_row.update(row_edits)
                    result.append(updated_row)
                else:
                    result.append(row)

            return result

        # --- OPTIMIZATION: Cache-only filtering path ---
        # If triggered by date-range/filter toggles and we have cached full data,
        # skip DB query.
        cache_only_triggers = {
            ids.CORRECTIONS_DATE_RANGE_STORE,
            ids.CORRECTIONS_SHOW_QC_ONLY_SWITCH,
        }
        if trigger_id in cache_only_triggers and cached_original_data:
            # If global time range changed, force DB reload instead of cache-only path
            current_global_tmin = time_range.get("tmin") if time_range else None
            current_global_tmax = time_range.get("tmax") if time_range else None
            cached_global_tmin = cached_original_data.get("global_tmin")
            cached_global_tmax = cached_original_data.get("global_tmax")
            if (
                current_global_tmin != cached_global_tmin
                or current_global_tmax != cached_global_tmax
            ):
                trigger_id = ids.TIME_RANGE_STORE

        if trigger_id in cache_only_triggers and cached_original_data:
            # Use cached full data and apply date filtering (no DB hit)
            table1_full = cached_original_data.get("table1_full", [])
            table2_full = cached_original_data.get("table2_full", [])
            well1_id = cached_original_data.get("well1_id")
            well2_id = cached_original_data.get("well2_id")
            well_key = f"{well1_id}:{well2_id}"

            table1_data = table1_full
            table2_data = table2_full

            if date_range:
                start_date = date_range.get("start")
                end_date = date_range.get("end")
                table1_data = _filter_by_date_range(table1_full, start_date, end_date)
                table2_data = _filter_by_date_range(table2_full, start_date, end_date)

            if show_qc_only:
                table1_data = _filter_to_effective_non_empty_comments(
                    table1_data,
                    table_num=1,
                    edit_history=edit_history,
                    well_key=well_key,
                )
                table2_data = _filter_to_effective_non_empty_comments(
                    table2_data,
                    table_num=2,
                    edit_history=edit_history,
                    well_key=well_key,
                )

            # Store UNEDITED filtered data as baseline for comparison
            updated_cache = dict(cached_original_data)
            updated_cache["table1_displayed"] = table1_data
            updated_cache["table2_displayed"] = table2_data

            # Re-apply persisted edits to filtered data for display
            table1_data = _reapply_edits(table1_data, 1, edit_history, well_key)
            table2_data = _reapply_edits(table2_data, 2, edit_history, well_key)

            return (
                CallbackResponse()
                .add(table1_data)
                .add(table2_data)
                .add(updated_cache)
                .build()
            )

        # --- DB QUERY: Well selection changed, reset, or commit ---
        # Handle reset or commit triggers - reload fresh data from database
        if (trigger_id == ids.CORRECTIONS_RESET_TRIGGER_STORE and reset_trigger) or (
            trigger_id == ids.CORRECTIONS_COMMIT_TRIGGER_STORE and commit_trigger
        ):
            well1_id = state_well1_id
            well2_id = state_well2_id
            # On reset/commit, clear edit history to avoid reapplying stale edits
            # after fresh data has been loaded from the backend.
            edit_history = {}
        else:
            # Well selection changed - clear edit history for new time series
            edit_history = {}

        # If neither well is selected, clear tables
        if well1_id is None and well2_id is None:
            return CallbackResponse().add([]).add([]).add(None).build()

        # If same well selected twice, treat as single well
        if well1_id == well2_id and well1_id is not None:
            well2_id = None

        well_key = f"{well1_id}:{well2_id}"

        try:
            obs_dict = {}
            global_tmin = time_range.get("tmin") if time_range else None
            global_tmax = time_range.get("tmax") if time_range else None
            qc_result_wid = _extract_qc_result_wid(traval_result_figure_store)
            traval_result_df = (
                data.qc.traval_result
                if data is not None
                and getattr(data, "qc", None) is not None
                and getattr(data.qc, "traval_result", None) is not None
                else None
            )

            for wid, key in [(well1_id, "table1"), (well2_id, "table2")]:
                if wid is None:
                    continue
                obs = ts_service.get_timeseries_for_observation_well(
                    wid,
                    observation_type=None,
                    tmin=global_tmin,
                    tmax=global_tmax,
                )
                if obs is not None and not obs.empty:
                    required_cols = [
                        ColumnNames.FIELD_VALUE,
                        ColumnNames.CALCULATED_VALUE,
                        ColumnNames.INITIAL_CALCULATED_VALUE,
                        ColumnNames.OBSERVATION_TYPE,
                        ColumnNames.CORRECTION_REASON,
                        ColumnNames.MEASUREMENT_TVP_ID,
                    ]

                    if data.db.value_column in obs.columns:
                        series_values = obs[data.db.value_column]
                    else:
                        series_values = pd.Series(np.nan, index=obs.index)

                    if ColumnNames.FIELD_VALUE not in obs.columns:
                        obs[ColumnNames.FIELD_VALUE] = series_values
                    if ColumnNames.CALCULATED_VALUE not in obs.columns:
                        obs[ColumnNames.CALCULATED_VALUE] = series_values
                    if ColumnNames.INITIAL_CALCULATED_VALUE not in obs.columns:
                        obs[ColumnNames.INITIAL_CALCULATED_VALUE] = np.nan
                    if ColumnNames.OBSERVATION_TYPE not in obs.columns:
                        obs[ColumnNames.OBSERVATION_TYPE] = None
                    if ColumnNames.CORRECTION_REASON not in obs.columns:
                        obs[ColumnNames.CORRECTION_REASON] = ""
                    if ColumnNames.MEASUREMENT_TVP_ID not in obs.columns:
                        obs[ColumnNames.MEASUREMENT_TVP_ID] = np.arange(
                            len(obs), dtype=int
                        )

                    if obs.index.has_duplicates:
                        dup_count = obs.index.duplicated().sum()
                        logger.warning(
                            "Dropping %s duplicate timestamps for wid %s",
                            dup_count,
                            wid,
                        )
                        obs = obs[~obs.index.duplicated(keep="first")]
                    obs = obs.loc[
                        :,
                        required_cols,
                    ].dropna(
                        how="all",
                        subset=[
                            ColumnNames.FIELD_VALUE,
                            ColumnNames.CALCULATED_VALUE,
                            ColumnNames.INITIAL_CALCULATED_VALUE,
                        ],
                    )
                    obs = _merge_traval_comments_into_observations(
                        obs,
                        wid=wid,
                        qc_result_wid=qc_result_wid,
                        traval_result_df=traval_result_df,
                    )
                    obs.index.name = "datetime"
                    obs_dict[key] = obs

            # If no data loaded, return empty
            if not obs_dict:
                return CallbackResponse().add([]).add([]).add(None).build()

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

            # Apply date range filtering if specified (on initial load)
            table1_filtered = table1_data
            table2_filtered = table2_data
            if date_range:
                start_date = date_range.get("start")
                end_date = date_range.get("end")
                table1_filtered = _filter_by_date_range(
                    table1_data, start_date, end_date
                )
                table2_filtered = _filter_by_date_range(
                    table2_data, start_date, end_date
                )

            if show_qc_only:
                table1_filtered = _filter_to_effective_non_empty_comments(
                    table1_filtered,
                    table_num=1,
                    edit_history=edit_history,
                    well_key=well_key,
                )
                table2_filtered = _filter_to_effective_non_empty_comments(
                    table2_filtered,
                    table_num=2,
                    edit_history=edit_history,
                    well_key=well_key,
                )

            # Precompute date range for efficient info text generation
            data_dates = []
            for row in table1_data + table2_data:
                if row.get("datetime"):
                    try:
                        data_dates.append(pd.to_datetime(row["datetime"]))
                    except Exception:
                        pass

            if data_dates:
                data_tmin = min(data_dates).date().isoformat()
                data_tmax = max(data_dates).date().isoformat()
            else:
                data_tmin = data_tmax = None

            # Store both full and filtered versions:
            # - "table1_full" / "table2_full": unfiltered for info text
            # - "table1_displayed" / "table2_displayed": UNEDITED baseline for
            #   comparison
            # - "data_tmin" / "data_tmax": precomputed date range to avoid
            #   recalculating on edits
            # - "well1_id" / "well2_id": track which time series this data belongs to
            original_data = {
                "table1_full": table1_data,
                "table2_full": table2_data,
                "table1_displayed": table1_filtered,  # UNEDITED baseline
                "table2_displayed": table2_filtered,  # UNEDITED baseline
                "data_tmin": data_tmin,
                "data_tmax": data_tmax,
                "global_tmin": global_tmin,
                "global_tmax": global_tmax,
                "well1_id": well1_id,
                "well2_id": well2_id,
                "timestamp": pd.Timestamp.now().isoformat(),
            }

            # Re-apply persisted edits to create the display version (edited)
            # The tables get the edited version, but original_data stores unedited
            # baseline
            table1_filtered = _reapply_edits(table1_filtered, 1, edit_history, well_key)
            table2_filtered = _reapply_edits(table2_filtered, 2, edit_history, well_key)

            return (
                CallbackResponse()
                .add(table1_filtered)
                .add(table2_filtered)
                .add(original_data)
                .build()
            )

        except TimeSeriesError as e:
            logger.exception("Error loading observations: %s", e)
            return CallbackResponse().add([]).add([]).add(None).build()

    # Callback 2b: Update info text on date range changes (lightweight, no DB query)
    @app.callback(
        Output(ids.CORRECTIONS_DATE_RANGE_INFO, "children"),
        Input(ids.CORRECTIONS_OBSERVATIONS_TABLE_1, "data"),
        Input(ids.CORRECTIONS_OBSERVATIONS_TABLE_2, "data"),
        Input(ids.CORRECTIONS_DATE_RANGE_STORE, "data"),
        State(ids.CORRECTIONS_ORIGINAL_DATA_STORE, "data"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def update_corrections_date_range_info(
        table1_data, table2_data, date_range, original_data, **kwargs
    ):
        """Update date range info text (lightweight, no DB queries).

        Calculates filtering statistics from in-memory data and displays
        info text about the current date range selection.

        Parameters
        ----------
        table1_data : list[dict]
            Filtered observations for table 1.
        table2_data : list[dict]
            Filtered observations for table 2.
        date_range : dict or None
            Date range filter with 'start' and 'end' keys.
        original_data : dict or None
            Cached data with 'table1_full'/'table2_full' (unfiltered) keys.

        Returns
        -------
        str
            Formatted info text for display.
        """
        if not original_data:
            return t_("general.select_wells_to_filter")

        # Get full unfiltered data for counts (NOT the displayed/filtered version)
        table1_full = original_data.get("table1_full", [])
        table2_full = original_data.get("table2_full", [])
        original_count = len(table1_full) + len(table2_full)
        filtered_count = len(table1_data or []) + len(table2_data or [])

        # Use precomputed date range from store (avoids expensive recalculation
        # on every table edit)
        data_tmin = original_data.get("data_tmin")
        data_tmax = original_data.get("data_tmax")

        # Generate info text based on applied date range
        if date_range:
            start_date = date_range.get("start")
            end_date = date_range.get("end")

            if start_date and end_date:
                info_text = t_(
                    "general.showing_filtered_range",
                    count=filtered_count,
                    total=original_count,
                    start=start_date,
                    end=end_date,
                )
            elif start_date:
                info_text = t_(
                    "general.showing_filtered_range",
                    count=filtered_count,
                    total=original_count,
                    start=start_date,
                    end=data_tmax or "present",
                )
            elif end_date:
                info_text = t_(
                    "general.showing_filtered_range",
                    count=filtered_count,
                    total=original_count,
                    start=data_tmin or "earliest",
                    end=end_date,
                )
            else:
                info_text = t_(
                    "general.showing_filtered_range",
                    count=original_count,
                    total=original_count,
                    start=data_tmin or "",
                    end=data_tmax or "",
                )
        else:
            # No date range filter applied
            if data_tmin and data_tmax:
                info_text = t_(
                    "general.showing_filtered_range",
                    count=original_count,
                    total=original_count,
                    start=data_tmin,
                    end=data_tmax,
                )
            else:
                info_text = t_("general.no_data_available")

        unsaved_count = _count_unsaved_corrections(
            table1_data,
            original_data.get("table1_displayed", []),
        ) + _count_unsaved_corrections(
            table2_data,
            original_data.get("table2_displayed", []),
        )

        if unsaved_count > 0:
            info_text = (
                f"{info_text} • "
                f"{t_('general.unsaved_corrections', count=unsaved_count)}"
            )

        return info_text

    # Callback 2b: Capture and persist user edits to history store
    @app.callback(
        Output(ids.CORRECTIONS_EDIT_HISTORY_STORE, "data"),
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
    def capture_edits(table1_data, table2_data, original_data, edit_history, **kwargs):
        """Capture and persist user edits by datetime key.

        Compares current table data with displayed version to extract actual edits,
        then stores them keyed by well IDs and datetime for re-application after
        filtering. This ensures corrections are tied to specific time series.

        Parameters
        ----------
        table1_data : list[dict]
            Current data from table 1.
        table2_data : list[dict]
            Current data from table 2.
        original_data : dict or None
            Original store with displayed versions and well IDs.
        edit_history : dict or None
            Previous edit history.

        Returns
        -------
        dict
            Updated edit history keyed by well IDs and datetime.
        """
        if not original_data:
            return {}

        # Get current well IDs to namespace the edits
        current_well1_id = original_data.get("well1_id")
        current_well2_id = original_data.get("well2_id")
        well_key = f"{current_well1_id}:{current_well2_id}"

        # Rebuild edit history from scratch on each invocation.
        # This prevents stale row keys from surviving reset/commit/re-filter cycles.
        new_edit_history = {"_well_key": well_key}

        def _normalize_value(val, col):
            """Normalize values for comparison (same as track_edits)."""
            if val is None:
                return None
            if isinstance(val, str) and val.strip() == "":
                return None
            if col == ColumnNames.SET_MISSING:
                return _as_bool_set_missing(val)
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
                except (TypeError, ValueError):
                    return None
            if col == "comment":
                return val.strip() if isinstance(val, str) else val
            return val

        def _equal_values(a, b, col):
            """Compare normalized values."""
            na = _normalize_value(a, col)
            nb = _normalize_value(b, col)
            if na is None and (nb is None or pd.isna(nb)):
                return True
            if nb is None and (na is None or pd.isna(na)):
                return True
            return na == nb

        # Columns to track as editable
        editable_cols = [
            ColumnNames.CALCULATED_VALUE,
            ColumnNames.FIELD_VALUE,
            "corrected_value",
            ColumnNames.SET_MISSING,
            "comment",
        ]

        # Extract edits from table 1
        table1_displayed = original_data.get("table1_displayed", [])
        if table1_data and table1_displayed:
            for current_row in table1_data:
                datetime_val = current_row.get("datetime")
                if not datetime_val:
                    continue

                # Find matching row in displayed version by datetime
                original_row = None
                for orig_row in table1_displayed:
                    if orig_row.get("datetime") == datetime_val:
                        original_row = orig_row
                        break

                if original_row is None:
                    continue

                # Check for edits in this row
                row_key = f"{well_key}:table1:{datetime_val}"
                row_edits = {}
                for col in editable_cols:
                    current_val = current_row.get(col)
                    original_val = original_row.get(col)
                    if not _equal_values(current_val, original_val, col):
                        row_edits[col] = current_val

                if row_edits:
                    new_edit_history[row_key] = row_edits

        # Extract edits from table 2
        table2_displayed = original_data.get("table2_displayed", [])
        if table2_data and table2_displayed:
            for current_row in table2_data:
                datetime_val = current_row.get("datetime")
                if not datetime_val:
                    continue

                # Find matching row in displayed version by datetime
                original_row = None
                for orig_row in table2_displayed:
                    if orig_row.get("datetime") == datetime_val:
                        original_row = orig_row
                        break

                if original_row is None:
                    continue

                # Check for edits in this row
                row_key = f"{well_key}:table2:{datetime_val}"
                row_edits = {}
                for col in editable_cols:
                    current_val = current_row.get(col)
                    original_val = original_row.get(col)
                    if not _equal_values(current_val, original_val, col):
                        row_edits[col] = current_val

                if row_edits:
                    new_edit_history[row_key] = row_edits

        return new_edit_history

    # Callback 2c: Enable/disable commit and reset buttons based on dropdown selections
    @app.callback(
        Output(ids.CORRECTIONS_COMMIT_BUTTON, "disabled"),
        Output(ids.CORRECTIONS_RESET_BUTTON, "disabled"),
        Output(ids.CORRECTIONS_COMMIT_BUTTON_LABEL, "children"),
        Output(ids.CORRECTIONS_COMMIT_BUTTON, "style"),
        Input(ids.CORRECTIONS_WELL1_DROPDOWN, "value"),
        Input(ids.CORRECTIONS_WELL2_DROPDOWN, "value"),
        Input(ids.CORRECTIONS_OBSERVATIONS_TABLE_1, "data"),
        Input(ids.CORRECTIONS_OBSERVATIONS_TABLE_2, "data"),
        State(ids.CORRECTIONS_ORIGINAL_DATA_STORE, "data"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def enable_correction_buttons(
        well1_id,
        well2_id,
        table1_data,
        table2_data,
        original_data,
    ):
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

        # Commit enabled when a well is selected and data is available.
        commit_disabled = not (has_well_selected and has_data)

        # Reset is not supported for pastastore backend.
        reset_disabled = commit_disabled or data.db.backend == "pastastore"

        unsaved_count = 0
        if original_data:
            unsaved_count = _count_unsaved_corrections(
                table1_data,
                original_data.get("table1_displayed", []),
            ) + _count_unsaved_corrections(
                table2_data,
                original_data.get("table2_displayed", []),
            )

        commit_label = t_("general.commit_corrections")
        if unsaved_count > 0:
            commit_label = f" {commit_label} ({unsaved_count})"
        else:
            commit_label = f" {commit_label}"

        commit_button_style = {
            "margin-right": "10px",
            "--corrections-commit-bg": UI.DEFAULT_BUTTON_COLOR,
            "--corrections-commit-border": UI.DEFAULT_BUTTON_COLOR,
            "--corrections-commit-text": "#ffffff",
        }
        if unsaved_count > 0:
            commit_button_style.update(
                {
                    "--corrections-commit-bg": UI.DIRTY_BUTTON_WARNING_COLOR,
                    "--corrections-commit-border": UI.DIRTY_BUTTON_WARNING_COLOR,
                    "--corrections-commit-text": UI.DIRTY_BUTTON_TEXT_COLOR,
                }
            )

        return (
            CallbackResponse()
            .add(commit_disabled)
            .add(reset_disabled)
            .add(commit_label)
            .add(commit_button_style)
            .build()
        )

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

            if col == ColumnNames.SET_MISSING:
                return _as_bool_set_missing(val)

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

        # Use the DISPLAYED version (not the full unfiltered version) for edit tracking
        original_table1 = original_data.get("table1_displayed", [])
        original_table2 = original_data.get("table2_displayed", [])

        def is_empty_row(row):
            """Check if a row is an alignment placeholder (all editable cols empty)."""
            calculated_val = row.get(ColumnNames.CALCULATED_VALUE)
            field_val = row.get(ColumnNames.FIELD_VALUE)
            corrected_val = row.get("corrected_value")
            comment_val = row.get("comment", "")
            set_missing = _as_bool_set_missing(row.get(ColumnNames.SET_MISSING))

            # Treat empty strings like None for emptiness check
            def empty(val, col):
                n = _normalize_value(val, col)
                return n is None or pd.isna(n)

            return (
                empty(calculated_val, ColumnNames.CALCULATED_VALUE)
                and empty(field_val, ColumnNames.FIELD_VALUE)
                and empty(corrected_val, "corrected_value")
                and not set_missing
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
                        ColumnNames.CORRECTED_VALUE,
                        ColumnNames.SET_MISSING,
                        ColumnNames.COMMENT,
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
                        ColumnNames.CORRECTED_VALUE,
                        ColumnNames.SET_MISSING,
                        ColumnNames.COMMENT,
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

        return CallbackResponse().add(style_table1).add(style_table2).build()

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
    def commit_or_reset_corrections(
        _commit_clicks,
        _reset_clicks,
        table1_data,
        table2_data,
        original_data,
        state_well1_id,
        state_well2_id,
        **kwargs,
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
        state_well1_id : str or None
            Currently selected well 1 id.
        state_well2_id : str or None
            Currently selected well 2 id.

        Returns
        -------
        tuple
            (alert_data, commit_trigger, reset_trigger)
        """
        ctx_obj = get_callback_context(**kwargs)

        if not ctx_obj.triggered:
            return (
                CallbackResponse().add(no_update).add(no_update).add(no_update).build()
            )

        # Determine which button was clicked
        trigger_id = ctx_obj.triggered_id

        if trigger_id == ids.CORRECTIONS_COMMIT_BUTTON:
            return _handle_commit_corrections(
                table1_data, table2_data, original_data, state_well1_id, state_well2_id
            )
        elif trigger_id == ids.CORRECTIONS_RESET_BUTTON:
            return _handle_reset_corrections(
                table1_data, table2_data, original_data, state_well1_id, state_well2_id
            )

        return CallbackResponse().add(no_update).add(no_update).add(no_update).build()

    def _handle_commit_corrections(table1_data, table2_data, original_data, wid1, wid2):
        """Handle committing corrections to the database.

        Parameters
        ----------
        table1_data : list
            Current table 1 data with edits.
        table2_data : list
            Current table 2 data with edits.
        original_data : dict
            Original data with table1/table2 keys.
        wid1 : str or None
            Currently selected well 1 id.
        wid2 : str or None
            Currently selected well 2 id.

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
            if col == ColumnNames.SET_MISSING:
                return _as_bool_set_missing(val)
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
            wids = []  # collect well ids to clear caches
            corrections_to_save = []
            # Use displayed (baseline) data for comparison
            original_table1 = original_data.get("table1_displayed", [])
            original_table2 = original_data.get("table2_displayed", [])

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
                        set_missing_changed = not _equal_values(
                            current_row.get(ColumnNames.SET_MISSING),
                            original_row.get(ColumnNames.SET_MISSING),
                            ColumnNames.SET_MISSING,
                        )

                        if corrected_changed or comment_changed or set_missing_changed:
                            set_missing = _as_bool_set_missing(
                                current_row.get(ColumnNames.SET_MISSING)
                            )
                            corrected_val = (
                                np.nan
                                if set_missing
                                else _normalize_value(
                                    current_row.get(ColumnNames.CORRECTED_VALUE),
                                    ColumnNames.CORRECTED_VALUE,
                                )
                            )
                            if corrected_val is not None or set_missing:
                                corrections_to_save.append(
                                    {
                                        "measurement_tvp_id": current_row[
                                            "measurement_tvp_id"
                                        ],
                                        ColumnNames.TIMESTAMP: current_row.get(
                                            ColumnNames.DATETIME
                                        ),
                                        "original_calculated_value": _normalize_value(
                                            original_row.get(
                                                ColumnNames.CALCULATED_VALUE
                                            ),
                                            ColumnNames.CALCULATED_VALUE,
                                        ),
                                        "corrected_value": corrected_val,
                                        "comment": current_row.get("comment", ""),
                                        "display_name": wid1,
                                    }
                                )
                                wids.append(wid1)

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
                        set_missing_changed = not _equal_values(
                            current_row.get(ColumnNames.SET_MISSING),
                            original_row.get(ColumnNames.SET_MISSING),
                            ColumnNames.SET_MISSING,
                        )

                        if corrected_changed or comment_changed or set_missing_changed:
                            set_missing = _as_bool_set_missing(
                                current_row.get(ColumnNames.SET_MISSING)
                            )
                            corrected_val = (
                                np.nan
                                if set_missing
                                else _normalize_value(
                                    current_row.get(ColumnNames.CORRECTED_VALUE),
                                    ColumnNames.CORRECTED_VALUE,
                                )
                            )
                            if corrected_val is not None or set_missing:
                                corrections_to_save.append(
                                    {
                                        "measurement_tvp_id": current_row[
                                            "measurement_tvp_id"
                                        ],
                                        ColumnNames.TIMESTAMP: current_row.get(
                                            ColumnNames.DATETIME
                                        ),
                                        "original_calculated_value": _normalize_value(
                                            original_row.get(
                                                ColumnNames.CALCULATED_VALUE
                                            ),
                                            ColumnNames.CALCULATED_VALUE,
                                        ),
                                        "corrected_value": corrected_val,
                                        "comment": current_row.get("comment", ""),
                                        "display_name": wid2,
                                    }
                                )
                                wids.append(wid2)

            if len(corrections_to_save) == 0:
                # Inform user that there are no corrections to commit
                alert = AlertBuilder.warning(t_("general.no_corrections_to_commit"))
                return (
                    CallbackResponse().add(alert).add(no_update).add(no_update).build()
                )

            # Save corrections to database
            corrections_df = pd.DataFrame(corrections_to_save)
            ts_service.save_correction(wids, corrections_df)

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

    def _handle_reset_corrections(table1_data, table2_data, original_data, wid1, wid2):
        """Handle resetting corrections in the database.

        Parameters
        ----------
        table1_data : list
            Current table 1 data.
        table2_data : list
            Current table 2 data.
        original_data : dict
            Original data from store.
        wid1 : str or None
            Currently selected well 1 id.
        wid2 : str or None
            Currently selected well 2 id.

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
            wids = []
            corrections_to_reset = []

            # Collect corrections to reset from table 1
            if table1_data:
                for row in table1_data:
                    # Only reset if initial_calculcated_value is not null
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
                        wids.append(wid1)

            # Collect corrections to reset from table 2
            if table2_data:
                for row in table2_data:
                    # Only reset if initial_calculcated_value is not null
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
                        wids.append(wid2)

            if len(corrections_to_reset) == 0:
                # Inform user that there are no corrections to reset
                alert = AlertBuilder.warning(t_("general.no_corrections_to_reset"))
                return (
                    CallbackResponse().add(alert).add(no_update).add(no_update).build()
                )

            # Reset corrections in database
            corrections_df = pd.DataFrame(corrections_to_reset)
            ts_service.reset_correction(wids, corrections_df)

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

    # Callback: Update date range store from chart range slider selection
    @app.callback(
        Output(ids.CORRECTIONS_DATE_RANGE_STORE, "data"),
        Input(ids.CORRECTION_SERIES_CHART, "relayoutData"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def update_date_range_store(relayout_data, **kwargs):
        """Update date range from chart rangeslider selection.

        Handles chart range selection from rangeslider or range selector buttons.
        """
        if not relayout_data:
            raise PreventUpdate

        # Handle chart range selection - check both formats
        if "xaxis.range" in relayout_data:
            try:
                start_str, end_str = relayout_data["xaxis.range"]
                # Handle both ISO format and millisecond timestamps
                if isinstance(start_str, (int, float)):
                    start = pd.to_datetime(start_str, unit="ms").date()
                    end = pd.to_datetime(end_str, unit="ms").date()
                else:
                    start = pd.to_datetime(start_str).date()
                    end = pd.to_datetime(end_str).date()
                range_data = {"start": start.isoformat(), "end": end.isoformat()}
                return range_data
            except Exception as e:
                logger.warning("Failed to parse chart range: %s", e)
                raise PreventUpdate from None
        elif "xaxis.range[0]" in relayout_data and "xaxis.range[1]" in relayout_data:
            try:
                start_str = relayout_data["xaxis.range[0]"]
                end_str = relayout_data["xaxis.range[1]"]
                # Handle both ISO format and millisecond timestamps
                if isinstance(start_str, (int, float)):
                    start = pd.to_datetime(start_str, unit="ms").date()
                    end = pd.to_datetime(end_str, unit="ms").date()
                else:
                    start = pd.to_datetime(start_str).date()
                    end = pd.to_datetime(end_str).date()
                range_data = {"start": start.isoformat(), "end": end.isoformat()}
                return range_data
            except Exception as e:
                logger.warning("Failed to parse chart range: %s", e)
                raise PreventUpdate from None

        raise PreventUpdate


def _normalize_correction_value(val, col):
    """Normalize correction values for robust comparison."""
    if val is None:
        return None
    if isinstance(val, str) and val.strip() == "":
        return None

    if col == ColumnNames.SET_MISSING:
        return _as_bool_set_missing(val)

    if col in {
        ColumnNames.CALCULATED_VALUE,
        ColumnNames.FIELD_VALUE,
        "corrected_value",
    }:
        try:
            if isinstance(val, (int, float)):
                return val if not pd.isna(val) else None
            return float(str(val))
        except (TypeError, ValueError):
            return None

    if col == "comment":
        return val.strip() if isinstance(val, str) else val

    return val


def _equal_correction_values(a, b, col):
    """Compare normalized values and treat None/NaN equivalently."""
    na = _normalize_correction_value(a, col)
    nb = _normalize_correction_value(b, col)

    if na is None and (nb is None or pd.isna(nb)):
        return True
    if nb is None and (na is None or pd.isna(na)):
        return True

    return na == nb


def _count_unsaved_corrections(current_table, original_table):
    """Count rows with unsaved correction changes."""
    if not current_table or not original_table:
        return 0

    unsaved_count = 0
    max_rows = min(len(current_table), len(original_table))

    for row_idx in range(max_rows):
        current_row = current_table[row_idx]
        original_row = original_table[row_idx]

        corrected_changed = not _equal_correction_values(
            current_row.get("corrected_value"),
            original_row.get("corrected_value"),
            "corrected_value",
        )
        comment_changed = not _equal_correction_values(
            current_row.get("comment"),
            original_row.get("comment"),
            "comment",
        )
        set_missing_changed = not _equal_correction_values(
            current_row.get(ColumnNames.SET_MISSING),
            original_row.get(ColumnNames.SET_MISSING),
            ColumnNames.SET_MISSING,
        )

        if corrected_changed or comment_changed or set_missing_changed:
            unsaved_count += 1

    return unsaved_count


def _prepare_observation_table_data(obs_df):
    """Prepare observation DataFrame for table display."""
    try:
        validate_not_empty(obs_df, context="observation data for table")
    except EmptyResultError:
        return []

    table_df = obs_df.reset_index()

    # Ensure observation type is always present for display
    if ColumnNames.OBSERVATION_TYPE not in table_df:
        table_df[ColumnNames.OBSERVATION_TYPE] = ""
    else:
        table_df[ColumnNames.OBSERVATION_TYPE] = (
            table_df[ColumnNames.OBSERVATION_TYPE].fillna("").astype(str)
        )

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

    # SET_MISSING is True when an active DB correction exists but the corrected
    # value is NaN (i.e. initial_calculated_value is set, calculated_value is NULL).
    has_db_correction = table_df[ColumnNames.INITIAL_CALCULATED_VALUE].notna()
    corrected_to_nan = has_db_correction & pd.isna(current_calculated)
    table_df[ColumnNames.SET_MISSING] = corrected_to_nan

    # Format datetime
    table_df[ColumnNames.DATETIME] = table_df[ColumnNames.DATETIME].dt.strftime(
        ConfigDefaults.DATETIME_FORMAT
    )

    # Select columns for display
    return table_df[
        [
            ColumnNames.DATETIME,
            ColumnNames.OBSERVATION_TYPE,
            ColumnNames.FIELD_VALUE,
            ColumnNames.CALCULATED_VALUE,
            ColumnNames.CORRECTED_VALUE,
            ColumnNames.SET_MISSING,
            ColumnNames.COMMENT,
            ColumnNames.MEASUREMENT_TVP_ID,
            ColumnNames.INITIAL_CALCULATED_VALUE,
        ]
    ].to_dict("records")


def _as_bool_set_missing(value) -> bool:
    """Normalize set-missing values from DataTable payload to bool."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False

    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized in {"true", "1", "yes", "set nan", "nan"}

    return bool(value)


def _filter_by_date_range(table_data, start_date, end_date):
    """Filter table data by date range.

    Parameters
    ----------
    table_data : list[dict]
        Table data to filter
    start_date : str or None
        Start date in ISO format
    end_date : str or None
        End date in ISO format

    Returns
    -------
    list[dict]
        Filtered table data
    """
    if not table_data or (start_date is None and end_date is None):
        return table_data

    df = pd.DataFrame(table_data)
    if df.empty:
        return table_data

    # Parse datetime column
    df[ColumnNames.DATETIME] = pd.to_datetime(
        df[ColumnNames.DATETIME], format=ConfigDefaults.DATETIME_FORMAT, errors="coerce"
    )

    # Apply filters
    if start_date is not None:
        start_dt = pd.to_datetime(start_date)
        df = df[df[ColumnNames.DATETIME] >= start_dt]
    if end_date is not None:
        end_dt = (
            pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        )
        df = df[df[ColumnNames.DATETIME] <= end_dt]

    # Format datetime back to string
    df[ColumnNames.DATETIME] = df[ColumnNames.DATETIME].dt.strftime(
        ConfigDefaults.DATETIME_FORMAT
    )

    return df.to_dict("records")


def _extract_qc_result_wid(traval_result_figure_store):
    """Extract QC-result well id from TRAVAL_RESULT_FIGURE_STORE payload."""
    if traval_result_figure_store is None:
        return None

    if isinstance(traval_result_figure_store, (list, tuple)):
        if not traval_result_figure_store:
            return None
        candidate = traval_result_figure_store[0]
    else:
        candidate = traval_result_figure_store

    try:
        return int(candidate)
    except (TypeError, ValueError):
        return None


def _merge_traval_comments_into_observations(
    obs_df: pd.DataFrame,
    wid: int | None,
    qc_result_wid: int | None,
    traval_result_df: pd.DataFrame | None,
) -> pd.DataFrame:
    """Merge QC detection comments into observation correction reason column.

    Merge is applied only when the currently loaded well equals the well for the
    active QC result. Existing correction reasons are preserved.
    """
    if (
        obs_df is None
        or obs_df.empty
        or traval_result_df is None
        or traval_result_df.empty
        or wid is None
        or qc_result_wid is None
        or int(wid) != int(qc_result_wid)
    ):
        return obs_df

    if ColumnNames.COMMENT not in traval_result_df.columns:
        return obs_df

    result = obs_df.copy()

    existing_reason = (
        result.get(ColumnNames.CORRECTION_REASON, pd.Series(index=result.index))
        .fillna("")
        .astype(str)
    )

    detector_comment_series = (
        traval_result_df[ColumnNames.COMMENT].fillna("").astype(str).str.strip()
    )

    detector_comment_series = detector_comment_series[detector_comment_series != ""]
    if detector_comment_series.empty:
        return result

    qc_comments = pd.Series(index=result.index, dtype="object")

    if (
        ColumnNames.MEASUREMENT_TVP_ID in result.columns
        and ColumnNames.MEASUREMENT_TVP_ID in traval_result_df.columns
    ):
        detector_by_tvp = (
            traval_result_df.loc[detector_comment_series.index]
            .dropna(subset=[ColumnNames.MEASUREMENT_TVP_ID])
            .drop_duplicates(subset=[ColumnNames.MEASUREMENT_TVP_ID], keep="last")
            .set_index(ColumnNames.MEASUREMENT_TVP_ID)[ColumnNames.COMMENT]
        )
        qc_comments = result[ColumnNames.MEASUREMENT_TVP_ID].map(detector_by_tvp)

    if qc_comments.isna().all():
        detector_by_datetime = detector_comment_series.copy()
        try:
            detector_by_datetime.index = pd.to_datetime(detector_by_datetime.index)
            qc_comments = pd.Series(
                detector_by_datetime.reindex(result.index).values,
                index=result.index,
            )
        except Exception:
            return result

    qc_comments = qc_comments.fillna("").astype(str).str.strip()
    existing_empty = existing_reason.str.strip() == ""
    result.loc[existing_empty, ColumnNames.CORRECTION_REASON] = qc_comments.loc[
        existing_empty
    ]

    return result


def _filter_to_effective_non_empty_comments(
    table_data: list[dict] | None,
    table_num: int,
    edit_history: dict | None,
    well_key: str,
) -> list[dict]:
    """Keep only rows where effective comment is non-empty.

    Effective comment means:
    - edited comment in the current session (when present in edit_history),
      otherwise
    - baseline comment in table data.
    """
    if not table_data:
        return []

    history = edit_history or {}
    filtered_rows: list[dict] = []

    for row in table_data:
        datetime_val = row.get(ColumnNames.DATETIME)
        baseline_comment = row.get(ColumnNames.COMMENT)
        effective_comment = baseline_comment

        if datetime_val:
            row_key = f"{well_key}:table{table_num}:{datetime_val}"
            row_edits = history.get(row_key, {})
            if ColumnNames.COMMENT in row_edits:
                effective_comment = row_edits.get(ColumnNames.COMMENT)

        if effective_comment is None:
            continue
        if str(effective_comment).strip() == "":
            continue

        filtered_rows.append(row)

    return filtered_rows
