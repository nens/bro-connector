import logging
from typing import Any

import numpy as np
import pandas as pd
from dash import Input, Output, Patch, State, no_update
from gwdatalens.app.config import config
from gwdatalens.app.constants import ColumnNames, ConfigDefaults
from gwdatalens.app.exceptions import EmptyResultError, QueryError
from gwdatalens.app.messages import ErrorMessages, t_
from gwdatalens.app.src.components import ids
from gwdatalens.app.src.components.overview_chart import plot_obs
from gwdatalens.app.src.services import TimeSeriesService, WellService
from gwdatalens.app.src.utils import log_callback
from gwdatalens.app.src.utils.callback_helpers import (
    AlertBuilder,
    CallbackResponse,
    EmptyFigure,
    TimestampStore,
    get_callback_context,
    validate_selection_limit,
)

logger = logging.getLogger(__name__)


def register_overview_callbacks(app, data):
    ts_service = TimeSeriesService(data.db)
    well_service = WellService(data.db)

    def _should_restore_after_tab_render(
        render_signal: tuple | None,
        selected_oseries: list[int] | None,
        max_age_seconds: int = 2,
    ) -> bool:
        """Return True when a null map selection is caused by tab remount.

        The overview map is recreated when the tab content is rendered. Its
        initial ``selectedData=None`` should restore the persisted selection,
        not clear the chart as if the user explicitly deselected the map.
        """
        if render_signal is None or selected_oseries is None:
            return False

        signal_timestamp, restore_allowed = render_signal
        if not restore_allowed:
            return False

        return (pd.Timestamp.now() - pd.Timestamp(signal_timestamp)) <= pd.Timedelta(
            seconds=max_age_seconds
        )

    @app.callback(
        Output(ids.SELECTED_OSERIES_STORE, "data"),
        Input(ids.OVERVIEW_MAP, "selectedData"),  # allow_optional=True
        Input(ids.OVERVIEW_CLEAR_SELECTION_BUTTON, "n_clicks"),
        State(ids.SELECTED_OSERIES_STORE, "data"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def store_selected_oseries_value(
        selected_data: dict | None,
        clear_clicks: int | None,
        current_value: list[int] | None,
        **kwargs,
    ) -> list[int] | None:
        """Store selected well IDs from map selection or clear selection."""
        ctx_obj = get_callback_context(**kwargs)
        triggered_id = ctx_obj.triggered_id

        # Handle clear button click
        if triggered_id == ids.OVERVIEW_CLEAR_SELECTION_BUTTON:
            return None

        # Handle map selection
        if selected_data is None:
            # Preserve current store value when selection is cleared
            # This allows the selection to persist when switching tabs
            return current_value

        _, wids = well_service.get_selected_wells_from_map_data(selected_data)
        if wids:
            # Block storing selections that exceed the configured load limit
            limit_alert = validate_selection_limit(
                wids,
                config.get("SERIES_LOAD_LIMIT"),
                t_("general.max_selection_warning"),
            )
            if limit_alert:
                logger.warning(
                    "Selection exceeds limit; not updating store (limit=%s, "
                    "selected=%s)",
                    config.get("SERIES_LOAD_LIMIT"),
                    len(wids),
                )
                return current_value

            return wids

        return current_value

    @app.callback(
        Output(ids.SERIES_CHART, "figure"),
        Output(ids.OVERVIEW_TABLE, "data"),
        Output(ids.ALERT_TIME_SERIES_CHART, "data"),
        Output(ids.OVERVIEW_TABLE_SELECTION_1, "data"),
        Input(ids.OVERVIEW_MAP, "selectedData"),  # allow_optional=True
        Input(ids.OVERVIEW_TIME_RANGE_REFRESH_STORE, "data"),
        Input(ids.OVERVIEW_TAB_RENDER_STORE, "data"),
        Input(ids.OVERVIEW_CLEAR_SELECTION_BUTTON, "n_clicks"),
        State(ids.TIME_RANGE_STORE, "data"),
        State(ids.SELECTED_OSERIES_STORE, "data"),
        State(ids.OVERVIEW_TABLE_SELECTION_1, "data"),
        State(ids.OVERVIEW_TABLE_SELECTION_2, "data"),
        background=False,
        prevent_initial_call=True,
        optional=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def plot_overview_time_series(
        selectedData: dict | None,
        _overview_refresh_signal: tuple | None,
        _overview_tab_render_signal: tuple | None,
        _clear_clicks: int | None,
        time_range: dict | None,
        selected_oseries: list[int] | None,
        table_selected_1: dict | None,
        table_selected_2: dict | None,
        **kwargs,
    ) -> tuple[dict, list[dict] | Any, tuple, dict]:
        """Plot time series and sync table based on map or stored selection.

        Handles synchronization between map selection, table display, and chart.
        Determines if selection originated from table (to avoid table update loops).
        Re-renders automatically when the global time-range filter changes.
        Also handles clearing selection via the clear button.
        """
        ctx_obj = get_callback_context(**kwargs)
        triggered_id = ctx_obj.triggered_id

        # Handle clear button click - return empty state
        if triggered_id == ids.OVERVIEW_CLEAR_SELECTION_BUTTON:
            all_wells_table = well_service.get_well_metadata_for_display(
                well_service.get_all_well_ids()
            ).to_dict("records")
            return (
                EmptyFigure.with_message(t_("general.select_location")),
                all_wells_table,
                AlertBuilder.no_alert(),
                TimestampStore.create(success=False),
            )
        time_range_triggered = triggered_id == ids.OVERVIEW_TIME_RANGE_REFRESH_STORE
        restore_from_tab_render = True
        if _overview_tab_render_signal is not None:
            _, restore_from_tab_render = _overview_tab_render_signal

        # Extract tmin/tmax from the time range store
        tmin = time_range.get("tmin") if time_range else None
        tmax = time_range.get("tmax") if time_range else None
        preset = time_range.get("preset") if time_range else None

        # Determine if selection originated from table
        table_triggered = _was_selection_from_table(table_selected_1, table_selected_2)
        restore_after_tab_render = _should_restore_after_tab_render(
            _overview_tab_render_signal, selected_oseries
        )

        # Handle explicit deselection on map
        if (
            selectedData is None
            and triggered_id == ids.OVERVIEW_MAP
            and not table_triggered
            and not restore_after_tab_render
        ):
            all_wells_table = well_service.get_well_metadata_for_display(
                well_service.get_all_well_ids()
            ).to_dict("records")
            return (
                EmptyFigure.with_message(t_("general.select_location")),
                all_wells_table,
                no_update,
                TimestampStore.create(success=False),
            )

        # Extract well IDs from map selection
        if selectedData is not None:
            names, wids = well_service.get_selected_wells_from_map_data(selectedData)
            # If no valid wells extracted (e.g., during table filtering),
            # preserve current state
            if not wids:
                return no_update, no_update, no_update, no_update

            # Validate selection limit
            limit_alert = validate_selection_limit(
                wids,
                config.get("SERIES_LOAD_LIMIT"),
                t_("general.max_selection_warning"),
            )
            if limit_alert:
                return (
                    CallbackResponse()
                    .add(no_update)
                    .add(no_update)
                    .add(limit_alert)
                    .add(TimestampStore.create(success=False))
                    .build()
                )

            # Skip table refresh when the event originated from the table or
            # when only the time-range filter changed.
            if time_range_triggered or table_triggered:
                table_data = no_update
            else:
                # When box selecting on the map, show only the selected wells.
                table_data = well_service.get_well_metadata_for_display(wids).to_dict(
                    "records"
                )

            # Plot chart and handle errors
            try:
                if not ts_service.check_if_wells_have_data(wids):
                    return (
                        CallbackResponse()
                        .add_figure(
                            EmptyFigure.with_message(
                                t_(ErrorMessages.NO_DATA_SELECTION)
                            )
                        )
                        .add(table_data)
                        .add(
                            AlertBuilder.warning(
                                t_(ErrorMessages.NO_PLOT_DATA, names=names)
                            )
                        )
                        .add(TimestampStore.create(success=False))
                        .build()
                    )

                chart = plot_obs(
                    wids,
                    data,
                    tmin=tmin,
                    tmax=tmax,
                    time_range_preset=preset,
                    plot_manual_obs=True,
                )
                return (
                    CallbackResponse()
                    .add_figure(chart)
                    .add(table_data)
                    .add(AlertBuilder.no_alert())
                    .add(TimestampStore.create(success=False))
                    .build()
                )
            except EmptyResultError as e:
                logger.warning("No time series data available: %s", e)
                all_wells_table = well_service.get_well_metadata_for_display(
                    well_service.get_all_well_ids()
                ).to_dict("records")
                return (
                    CallbackResponse()
                    .add_figure(
                        EmptyFigure.with_message(t_(ErrorMessages.NO_SERIES_DATA))
                    )
                    .add(all_wells_table)
                    .add(AlertBuilder.warning(t_(ErrorMessages.NO_SERIES_DATA)))
                    .add(TimestampStore.create(success=False))
                    .build()
                )
            except QueryError as e:
                logger.exception("Database query failed: %s", e)
                all_wells_table = well_service.get_well_metadata_for_display(
                    well_service.get_all_well_ids()
                ).to_dict("records")
                return (
                    CallbackResponse()
                    .add_figure(
                        EmptyFigure.with_message(t_(ErrorMessages.DATA_LOAD_FAILED))
                    )
                    .add(all_wells_table)
                    .add(AlertBuilder.danger(t_(ErrorMessages.DATABASE_ERROR)))
                    .add(TimestampStore.create(success=False))
                    .build()
                )
            except Exception as e:
                logger.exception(
                    "Unexpected error plotting overview time series: %s", e
                )
                all_wells_table = well_service.get_well_metadata_for_display(
                    well_service.get_all_well_ids()
                ).to_dict("records")
                return (
                    CallbackResponse()
                    .add_figure(
                        EmptyFigure.with_message(t_(ErrorMessages.DATA_LOAD_FAILED))
                    )
                    .add(all_wells_table)
                    .add(AlertBuilder.danger(t_(ErrorMessages.DATA_LOAD_FAILED)))
                    .add(TimestampStore.create(success=False))
                    .build()
                )

        # Handle fallback to stored selection
        elif selected_oseries is not None:
            if (
                triggered_id == ids.OVERVIEW_TAB_RENDER_STORE
                and not restore_from_tab_render
            ):
                return no_update, no_update, no_update, no_update

            wids = selected_oseries
            chart = plot_obs(
                wids,
                data,
                tmin=tmin,
                tmax=tmax,
                time_range_preset=preset,
            )
            if time_range_triggered:
                table_data = no_update
            else:
                # When restoring from persisted selection, show only the
                # selected wells in the Overview table.
                table_data = well_service.get_well_metadata_for_display(wids).to_dict(
                    "records"
                )
            return (
                CallbackResponse()
                .add_figure(chart)
                .add(table_data)
                .add(AlertBuilder.no_alert())
                .add(TimestampStore.create(success=False))
                .build()
            )

        return no_update, no_update, no_update, no_update

    def _was_selection_from_table(table_selected_1, table_selected_2):
        """Determine if most recent selection came from table.

        Compares timestamps of table selection stores to see if table
        was the origin of the selection event.
        """
        date = pd.Timestamp("1900-01-01 00:00:00")
        table_triggered = False

        for value in [table_selected_1, table_selected_2]:
            if value is None:
                continue
            d, t = value
            if pd.Timestamp(d) > date:
                table_triggered = t
                date = pd.Timestamp(d)

        return table_triggered

    @app.callback(
        Output(ids.OVERVIEW_MAP, "selectedData"),
        Output(ids.OVERVIEW_MAP, "figure"),
        Output(ids.OVERVIEW_TABLE_SELECTION_2, "data"),
        Input(ids.OVERVIEW_TABLE, "selected_cells"),
        Input(ids.OVERVIEW_CLEAR_SELECTION_BUTTON, "n_clicks"),
        State(ids.OVERVIEW_TABLE, "derived_virtual_data"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def highlight_point_on_map_from_table(
        selected_cells, clear_clicks, table, **kwargs
    ):
        """Sync map selection from table row selection or clear selection.

        When user selects rows in overview table, this updates the map
        to highlight the corresponding wells and returns selectedData
        to trigger chart update. Also handles clearing selection via button.
        """
        ctx_obj = get_callback_context(**kwargs)
        triggered_id = ctx_obj.triggered_id

        # Handle clear button click
        if triggered_id == ids.OVERVIEW_CLEAR_SELECTION_BUTTON:
            # Clear selectedData and also clear selectedpoints from all traces
            # in the figure
            mappatch = Patch()
            if config.get("USE_MAPBOX"):
                # Mapbox uses two traces (no data and data)
                mappatch["data"][0]["selectedpoints"] = None
                mappatch["data"][1]["selectedpoints"] = None
            else:
                # Non-Mapbox uses one trace
                mappatch["data"][0]["selectedpoints"] = None
            return None, mappatch, TimestampStore.create(success=False)

        # Handle table selection
        if selected_cells is None:
            return no_update, no_update, TimestampStore.create(success=False)

        # Extract unique row indices and get well IDs
        rows = np.unique([cell["row"] for cell in selected_cells]).tolist()
        df = pd.DataFrame.from_dict(table, orient="columns")
        # trap for an empty df
        if df.empty:
            return no_update, no_update, TimestampStore.create(success=False)
        wids = df.loc[rows, ColumnNames.ID].tolist()

        # Prepare map selection data
        selectedData = well_service.prepare_map_selection_data(wids)

        # Update map highlighting with Patch
        dfm = well_service.get_wells_subset(wids)

        mappatch = Patch()

        # Mapbox uses separate traces for wells with and without data, so both
        # traces need their selected points updated.
        if config.get("USE_MAPBOX"):
            # Update both traces with the selected points
            mappatch["data"][0]["selectedpoints"] = dfm.loc[
                dfm["metingen"] == 0, ColumnNames.ID
            ].tolist()
            mappatch["data"][1]["selectedpoints"] = dfm.loc[
                dfm["metingen"] > 0, ColumnNames.ID
            ].tolist()
        else:
            # For non-Mapbox maps, there's only one trace (index 1)
            dfm["curveNumber"] = 0
            mappatch["data"][0]["selectedpoints"] = dfm.loc[:, ColumnNames.ID].tolist()

        return (
            selectedData,
            mappatch,
            TimestampStore.create(success=True),
        )

    @app.callback(
        Output(ids.OVERVIEW_CLEAR_SELECTION_BUTTON, "disabled"),
        Input(ids.SELECTED_OSERIES_STORE, "data"),
    )
    def update_clear_selection_button_disabled(selected_oseries: list[int] | None):
        """Update the disabled state of the clear selection button.

        Enable the button when there is an active selection, disable it otherwise.
        """
        # Button is disabled when there's no selection
        return selected_oseries is None or len(selected_oseries) == 0
