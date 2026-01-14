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
    validate_selection_limit,
)

logger = logging.getLogger(__name__)


def register_overview_callbacks(app, data):
    ts_service = TimeSeriesService(data.db)
    well_service = WellService(data.db)

    @app.callback(
        Output(ids.SELECTED_OSERIES_STORE, "data"),
        Input(ids.OVERVIEW_MAP, "selectedData"),
        State(ids.SELECTED_OSERIES_STORE, "data"),
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def store_selected_oseries_value(
        selected_data: dict | None, current_value: list[int] | None
    ) -> list[int] | None:
        """Store selected well IDs from map selection."""
        if selected_data is None:
            return None if current_value is None else current_value

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
                return None if current_value is None else current_value

            return wids

        return None if current_value is None else current_value

    @app.callback(
        Output(ids.SERIES_CHART, "figure"),
        Output(ids.OVERVIEW_TABLE, "data"),
        Output(ids.ALERT_TIME_SERIES_CHART, "data"),
        Output(ids.OVERVIEW_TABLE_SELECTION_1, "data"),
        Input(ids.OVERVIEW_MAP, "selectedData"),
        State(ids.SELECTED_OSERIES_STORE, "data"),
        State(ids.OVERVIEW_TABLE_SELECTION_1, "data"),
        State(ids.OVERVIEW_TABLE_SELECTION_2, "data"),
        background=False,
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def plot_overview_time_series(
        selectedData: dict | None,
        selected_oseries: list[int] | None,
        table_selected_1: dict | None,
        table_selected_2: dict | None,
    ) -> tuple[dict, list[dict] | Any, tuple, dict]:
        """Plot time series and sync table based on map or stored selection.

        Handles synchronization between map selection, table display, and chart.
        Determines if selection originated from table (to avoid table update loops).
        """
        # Determine if selection originated from table
        table_triggered = _was_selection_from_table(table_selected_1, table_selected_2)

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

            # Generate table data (skip if selection came from table)
            if table_triggered:
                table_data = no_update
            else:
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

                chart = plot_obs(wids, data)
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
                    .add_figure(EmptyFigure.with_message(t_(ErrorMessages.NO_SERIES)))
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
            wids = selected_oseries
            chart = plot_obs(wids, data)
            table_data = well_service.get_well_metadata_for_display(
                well_service.get_all_well_ids()
            ).to_dict("records")
            return (
                CallbackResponse()
                .add_figure(chart)
                .add(table_data)
                .add(AlertBuilder.no_alert())
                .add(TimestampStore.create(success=False))
                .build()
            )

        # No selection - preserve current state (likely table filter operation)
        # Don't show alerts or update when selectedData becomes None after having
        # a selection
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
        State(ids.OVERVIEW_TABLE, "derived_virtual_data"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def highlight_point_on_map_from_table(selected_cells, table):
        """Sync map selection from table row selection.

        When user selects rows in overview table, this updates the map
        to highlight the corresponding wells and returns selectedData
        to trigger chart update.
        """
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
        dfm["curveNumber"] = 1

        mappatch = Patch()
        mappatch["data"][1]["selectedpoints"] = dfm.loc[:, ColumnNames.ID].tolist()
        # mask = dfm.loc[:, "metingen"] > 0
        # mappatch["data"][1]["selectedpoints"] = (
        #     dfm.loc[~mask, ColumnNames.ID].tolist()
        # )

        return (
            selectedData,
            mappatch,
            TimestampStore.create(success=True),
        )
