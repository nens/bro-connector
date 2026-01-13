import logging
from ast import literal_eval
from typing import Any

import numpy as np
import pandas as pd
from dash import ALL, Input, Output, Patch, State, dcc, no_update
from dash.exceptions import PreventUpdate

from gwdatalens.app.config import config
from gwdatalens.app.constants import ColumnNames, ConfigDefaults, PlotConstants, QCFlags
from gwdatalens.app.messages import ErrorMessages, SuccessMessages, t_
from gwdatalens.app.src.components import ids
from gwdatalens.app.src.services import TimeSeriesService, WellService
from gwdatalens.app.src.utils import log_callback
from gwdatalens.app.src.utils.callback_helpers import (
    AlertBuilder,
    CallbackResponse,
    extract_selected_points_x,
    get_callback_context,
)

logger = logging.getLogger(__name__)


def register_result_callbacks(app, data):
    ts_service = TimeSeriesService(data.db)
    well_service = WellService(data.db)
    # @app.callback(
    #     Output(ids.QC_RESULT_TABLE, "derived_virtual_data", allow_duplicate=True),
    #     Input(ids.QC_RESULT_TABLE, "derived_virtual_data"),
    #     State(ids.QC_RESULT_TABLE, "selected_cells"),
    #     # State(ids.QC_RESULT_TABLE, "data"),
    #     prevent_initial_call=True,
    # )
    # def multi_edit_qc_results_table(filtered_data, selected_cells):
    #     # if no selection do nothing
    #     if selected_cells is None or selected_cells == []:
    #         raise PreventUpdate

    #     # check columns
    #     selected_columns = [c["column_id"] for c in selected_cells]
    #     if not np.any(np.isin(selected_columns, ["reliable", "category"])):
    #         raise PreventUpdate

    #     selected_row_id = [c["row_id"] for c in selected_cells]
    #     changed_cell = selected_cells[0]
    #     new_value = filtered_data[changed_cell["row"]][changed_cell["column_id"]]

    #     # return filtered_data
    #     for r in filtered_data:
    #         if r["id"] in selected_row_id:
    #             mask = data.qc.traval_result["id"] == r["id"]
    #             data.qc.traval_result.loc[
    #                 mask, changed_cell["column_id"]
    #             ] = new_value
    #             r[changed_cell["column_id"]] = new_value
    #     return data.qc.traval_result.reset_index(names="datetime").to_dict(
    #         "records"
    #     )

    @app.callback(
        Output(ids.QC_RESULT_TABLE_STORE_3, "data"),
        Output(ids.ALERT_LABEL_OBS, "data"),
        Output(ids.QC_RESULT_LABEL_DROPDOWN, "value"),
        Input(ids.QC_RESULT_LABEL_DROPDOWN, "value"),
        State(ids.QC_RESULT_TABLE, "derived_virtual_data"),
        State(ids.QC_RESULT_CHART, "selectedData"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def apply_qc_label(
        value: str | None, table_view: list[dict], selected_points: dict | None
    ) -> tuple[list[dict] | Any, tuple, None]:
        """Apply QC label category to selected observations.

        Updates the category field for selected chart points that are in the table view.
        """
        if value is None:
            logger.debug("QC apply label: value is None, preventing update")
            raise PreventUpdate

        df = data.qc.traval_result
        table = pd.DataFrame(table_view)

        # Check if table is empty due to filtering
        if table.empty:
            return (
                no_update,
                AlertBuilder.warning(t_("general.alert_failed_labeling")),
                None,
            )

        selected_pts = extract_selected_points_x(selected_points)
        if selected_pts is None:
            return (
                no_update,
                AlertBuilder.warning(t_("general.alert_failed_labeling")),
                None,
            )

        # Check if all selected points are in filtered table
        if np.any(
            ~np.isin(pd.to_datetime(selected_pts), pd.to_datetime(table["datetime"]))
        ):
            return (
                no_update,
                AlertBuilder.warning(t_("general.alert_failed_labeling")),
                None,
            )

        df.loc[selected_pts, "category"] = value
        t = table["datetime"].tolist()
        return (
            df.loc[t].reset_index(names="datetime").to_dict("records"),
            AlertBuilder.no_alert(),
            None,
        )

    @app.callback(
        Output(ids.DOWNLOAD_EXPORT_CSV, "data"),
        Input(ids.QC_RESULT_EXPORT_CSV, "n_clicks"),
        State(ids.SELECTED_OSERIES_STORE, "data"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def download_export_csv(n_clicks, wid):
        if wid is None:
            logger.debug("QC export CSV: wid is None, preventing update")
            raise PreventUpdate

        timestr = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        name = well_service.get_well_name(wid).squeeze()
        filename = f"{timestr}_qc_result_{name}.csv"
        if data.qc.traval_result is not None:
            return dcc.send_string(data.qc.traval_result.to_csv, filename=filename)

    @app.callback(
        Output(ids.ALERT_EXPORT_TO_DB, "data"),
        Input(ids.QC_RESULT_EXPORT_DB, "n_clicks"),
        State(ids.SELECTED_OSERIES_STORE, "data"),
        State(ids.QC_RESULT_EXPORT_QC_STATUS_FLAG, "value"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def export_to_db(n_clicks, wid, non_flagged_reliable):
        """Export QC results to database.

        Applies quality control status flags and saves to database.
        """
        if not n_clicks:
            logger.debug("QC export DB: no click, preventing update")
            raise PreventUpdate

        if wid is None:
            return AlertBuilder.warning(t_(ErrorMessages.NO_WELLS_SELECTED))

        if data.qc.traval_result is None:
            return AlertBuilder.warning(t_(ErrorMessages.NO_QC_RESULT))

        df = data.qc.traval_result.copy()
        name = well_service.get_well_name(wid)

        # Translate status flags if in English locale
        if config.get("LOCALE") == "en":
            bro_en_to_nl = QCFlags.BRO_STATUS_TRANSLATION_EN_TO_NL
            df[ColumnNames.STATUS_QUALITY_CONTROL] = df[
                ColumnNames.STATUS_QUALITY_CONTROL
            ].apply(lambda v: bro_en_to_nl[v])
            df[ColumnNames.INCOMING_STATUS_QUALITY_CONTROL] = df[
                ColumnNames.INCOMING_STATUS_QUALITY_CONTROL
            ].apply(lambda v: bro_en_to_nl[v])

        # Apply QC status rules
        mask = df[ColumnNames.STATUS_QUALITY_CONTROL] == ""
        mask_incoming_not_suspect = ~df[
            ColumnNames.INCOMING_STATUS_QUALITY_CONTROL
        ].isin([QCFlags.AFGEKEURD, QCFlags.ONBESLIST])

        if non_flagged_reliable == "all_not_suspect":
            # mark all non-flagged observations as reliable except incoming suspects
            df.loc[
                mask & mask_incoming_not_suspect, ColumnNames.STATUS_QUALITY_CONTROL
            ] = QCFlags.GOEDGEKEURD
            # Maintain incoming status for suspects
            df.loc[~mask_incoming_not_suspect, ColumnNames.STATUS_QUALITY_CONTROL] = (
                df.loc[
                    ~mask_incoming_not_suspect,
                    ColumnNames.INCOMING_STATUS_QUALITY_CONTROL,
                ]
            )
        elif non_flagged_reliable == "suspect":
            # Only update suspect observations, the rest remains as is
            df.loc[mask, ColumnNames.STATUS_QUALITY_CONTROL] = df.loc[
                mask, ColumnNames.INCOMING_STATUS_QUALITY_CONTROL
            ]
        elif non_flagged_reliable == "all":
            # mark all non-flagged observations as reliable
            df.loc[mask, ColumnNames.STATUS_QUALITY_CONTROL] = QCFlags.GOEDGEKEURD
        else:
            raise ValueError(
                f"Invalid value {non_flagged_reliable} for non_flagged_reliable"
            )

        if name is None:
            well_display = str(wid)
        else:
            well_display = name.squeeze()
        # Save to database
        try:
            ts_service.save_qualifier(df)
            return AlertBuilder.success(
                t_(SuccessMessages.EXPORT_SUCCESS, well=well_display)
            )
        except Exception as e:
            logger.exception("Failed to export data to database: %s", e)

            return AlertBuilder.danger(
                t_(ErrorMessages.EXPORT_FAILED, well=well_display)
            )

    @app.callback(
        Output(ids.QC_RESULT_TABLE, "filter_query"),
        Input(ids.QC_RESULTS_SHOW_ALL_OBS_SWITCH, "value"),
        State(ids.QC_RESULT_TABLE, "filter_query"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def show_all_observations(value, query):
        if value and (query != ""):
            return ""
        elif not value and (query == ""):
            return '{comment} != ""'
        else:
            # some query is active, try keeping it active but also filtering on comments
            if "{comment}" not in query:
                if value:
                    return query
                else:
                    return query + ' && {comment} != ""'  # add comment query
            else:
                if value:
                    return ""  # can't remove only comment query so remove all filters
                else:
                    return query  # return current active query

    @app.callback(
        Output(ids.QC_RESULT_CHART, "figure"),
        Output(ids.QC_RESULT_CHART, "selectedData"),
        Output(ids.QC_RESULT_TABLE_STORE_1, "data"),
        Output(ids.QC_RESULT_TABLE, "selected_cells"),
        Output(ids.QC_RESULT_TABLE, "active_cell"),
        Output(ids.QC_RESULT_CLEAR_TABLE_SELECTION, "disabled"),
        Output(ids.QC_RESULT_TABLE_SELECT_ALL, "disabled"),
        Output(
            {"type": ids.QC_RESULT_MARK_OBS_BUTTONS, "index": ALL},
            "disabled",
        ),
        Output(ids.QC_RESULT_LABEL_DROPDOWN, "disabled"),
        Input(ids.QC_RESULT_TABLE, "selected_cells"),
        Input(ids.QC_RESULT_CHART, "selectedData"),
        Input(ids.QC_RESULT_CLEAR_TABLE_SELECTION, "n_clicks"),
        Input(ids.QC_RESULT_TABLE_SELECT_ALL, "n_clicks"),
        State(ids.QC_RESULT_TABLE, "derived_virtual_data"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def synchronize_selected_observations(
        table_selection,
        chart_selection,
        click_clear,
        click_select,
        current_table,
        **kwargs,
    ):
        """Synchronize selection between QC result chart and table.

        Keeps chart selection and table selection in sync, updating one when the other
        changes.
        """
        ctx_obj = get_callback_context(**kwargs)
        triggered_id = ctx_obj.triggered_id

        # Get trace configuration from orchestrator
        curveNumber = data.qc.last_plot_context["observations_trace_index"]

        # Handle clear selection button
        if click_clear and triggered_id == ids.QC_RESULT_CLEAR_TABLE_SELECTION:
            update_figure = Patch()
            # TODO: if no pastas model, the original series is trace 0
            update_figure["data"][curveNumber]["selectedpoints"] = []

            cleared_table = (
                data.qc.traval_result.reset_index(names="datetime").to_dict("records")
                if data.qc.traval_result is not None
                else no_update
            )

            logger.debug(
                "QC sync: clear selection triggered_id=%s click_clear=%s table_size=%s",
                triggered_id,
                click_clear,
                len(cleared_table) if cleared_table is not no_update else "no_update",
            )

            return (
                CallbackResponse()
                .add(update_figure)
                .add(None)
                .add_data(cleared_table)
                .add([])
                .add(None)
                .add(True)  # disable deselect
                .add(False)  # enable select all
                .add([True] * 4)  # disable mark buttons
                .add(True)  # disable label dropdown
                .build()
            )

        # Handle select all button
        if click_select and triggered_id == ids.QC_RESULT_TABLE_SELECT_ALL:
            selection = [row[ColumnNames.ID] for row in current_table]
            series = data.qc.traval_result

            update_figure_selection = {
                "points": [
                    {
                        "curveNumber": curveNumber,
                        "pointNumber": series[ColumnNames.ID].iloc[i],
                        "pointIndex": series[ColumnNames.ID].iloc[i],
                        "x": series.index[i],
                        "y": series[data.db.value_column].iloc[i],
                    }
                    for i in selection
                ]
            }

            update_figure = Patch()
            update_figure["data"][curveNumber]["selectedpoints"] = []

            new_table_selection = [
                {"column": 0, "column_id": "datetime", "row": i, "row_id": rowid}
                for i, rowid in enumerate(selection)
            ]

            logger.debug(
                "QC sync: select all triggered_id=%s click_select=%s "
                "selection_count=%s",
                triggered_id,
                click_select,
                len(selection),
            )

            return (
                CallbackResponse()
                .add(update_figure)
                .add(update_figure_selection)
                .add(no_update)
                .add(new_table_selection)
                .add(None)
                .add(False)  # enable deselect
                .add(True)  # disable select all
                .add([False] * 4)  # enable mark buttons
                .add(False)  # enable label dropdown
                .build()
            )

        # Determine trigger and selection
        if table_selection is None and chart_selection is None:
            selection = None

        # Get selection from table if table was trigger
        if triggered_id == ids.QC_RESULT_TABLE:
            if table_selection is None or len(table_selection) == 0:
                selection = None
            else:
                selection = [c["row_id"] for c in table_selection]

        # Get selection from chart if chart was trigger
        elif triggered_id == ids.QC_RESULT_CHART:
            if chart_selection is None or len(chart_selection) == 0:
                logger.debug("QC sync: chart selection is None or empty")
                selection = None
            else:
                pts = pd.DataFrame(chart_selection["points"])

                if pts.empty:
                    logger.debug(
                        "QC sync: chart selection empty points triggered_id=%s",
                        triggered_id,
                    )
                    raise PreventUpdate
                selection = pts.loc[
                    pts.curveNumber == curveNumber, "pointIndex"
                ].tolist()
        else:
            logger.debug(
                "QC sync: unknown triggered_id=%s, preventing update",
                triggered_id,
            )
            raise PreventUpdate

        # Selection is empty
        if selection is None or len(selection) == 0:
            if data.qc.traval_result is not None:
                update_table = data.qc.traval_result.reset_index(
                    names="datetime"
                ).to_dict("records")
            else:
                update_table = no_update

            logger.debug(
                "QC sync: empty selection triggered_id=%s table_return=%s",
                triggered_id,
                "no_update" if update_table is no_update else len(update_table),
            )
            return (
                CallbackResponse()
                .add(no_update)
                .add(no_update)
                .add(update_table)
                .add([])
                .add(None)
                .add(True)  # disable deselect
                .add(False)  # enable select all
                .add([True] * 4)  # disable mark buttons
                .add(True)  # disable label dropdown
                .build()
            )

        # Update table based on chart selection
        if triggered_id == ids.QC_RESULT_CHART:
            update_table = (
                data.qc.traval_result.iloc[np.sort(selection)]
                .reset_index(names="datetime")
                .to_dict("records")
            )
            update_figure = no_update
            update_figure_selection = no_update
            update_table_selection = []
            logger.debug(
                "QC sync: chart triggered selection_count=%s",
                len(selection) if selection is not None else 0,
            )

        # Update chart based on table selection
        elif triggered_id == ids.QC_RESULT_TABLE:
            series = data.qc.traval_result
            update_figure_selection = {
                "points": [
                    {
                        # TODO: if no pastas model, the original series is trace 0
                        "curveNumber": curveNumber,
                        "pointNumber": int(series[ColumnNames.ID].iloc[i]),
                        "pointIndex": int(series[ColumnNames.ID].iloc[i]),
                        "x": series.index[i],
                        "y": float(series[data.db.value_column].iloc[i]),
                    }
                    for i in selection
                ]
            }
            update_figure = Patch()
            # TODO: if no pastas model, the original series is trace 0
            update_figure["data"][curveNumber]["selectedpoints"] = selection
            update_table = no_update
            update_table_selection = no_update
            logger.debug(
                "QC sync: table triggered selection_count=%s",
                len(selection) if selection is not None else 0,
            )
        else:
            logger.debug(
                "QC sync: unexpected triggered_id=%s after selection, prevent update",
                triggered_id,
            )
            raise PreventUpdate

        logger.debug(
            "QC sync: final return triggered_id=%s selection_count=%s",
            triggered_id,
            len(selection) if selection is not None else 0,
        )

        return (
            CallbackResponse()
            .add(update_figure)
            .add(update_figure_selection)
            .add(update_table)
            .add(update_table_selection)
            .add(no_update)
            .add(False)  # enable deselect
            .add(False)  # enable select all
            .add([False] * 4)  # enable mark buttons
            .add(False)  # enable label dropdown
            .build()
        )

    @app.callback(
        Output(ids.QC_RESULT_TABLE_STORE_2, "data"),
        Output(ids.ALERT_MARK_OBS, "data"),
        Input({"type": ids.QC_RESULT_MARK_OBS_BUTTONS, "index": ALL}, "n_clicks"),
        State(ids.QC_RESULT_TABLE, "derived_virtual_data"),
        State(ids.QC_RESULT_CHART, "selectedData"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def mark_obs(n, table_view, selected_points, **kwargs):
        """Mark observations with QC status.

        Updates the status_quality_control field based on the selected button.
        """
        if not any(v is not None for v in n):
            logger.debug("QC mark obs: no button clicks, preventing update")
            raise PreventUpdate

        ctx_obj = get_callback_context(**kwargs)
        triggered_id = ctx_obj.triggered_id

        # Extract index from pattern-matched callback ID
        if isinstance(triggered_id, dict):
            triggered_id_index = triggered_id["index"]
        else:
            triggered_id_index = literal_eval(triggered_id)["index"]

        # Map button index to status value
        status_map = {
            QCFlags.RELIABLE: t_("general.reliable"),
            QCFlags.UNRELIABLE: t_("general.unreliable"),
            QCFlags.UNKNOWN: t_("general.unknown"),
            QCFlags.UNDECIDED: t_("general.undecided"),
        }

        if triggered_id_index not in status_map:
            logger.debug(
                "QC mark obs: unknown trigger index=%s, preventing update",
                triggered_id_index,
            )
            raise PreventUpdate

        value = status_map[triggered_id_index]
        df = data.qc.traval_result
        table = pd.DataFrame(table_view)

        # Check if table is empty due to filtering
        if table.empty:
            return (
                no_update,
                AlertBuilder.warning(t_("general.alert_failed_labeling")),
            )

        selected_pts = extract_selected_points_x(selected_points)
        if selected_pts is None:
            return (
                no_update,
                AlertBuilder.warning(t_("general.alert_failed_labeling")),
            )

        # Check if all selected points are in filtered table
        if np.any(
            ~np.isin(pd.to_datetime(selected_pts), pd.to_datetime(table["datetime"]))
        ):
            return (
                no_update,
                AlertBuilder.warning(t_("general.alert_failed_labeling")),
            )

        df.loc[selected_pts, ColumnNames.STATUS_QUALITY_CONTROL] = value
        t = table["datetime"].tolist()
        return (
            df.loc[t].reset_index(names="datetime").to_dict("records"),
            AlertBuilder.no_alert(),
        )

    @app.callback(
        Output(ids.QC_RESULT_TABLE, "style_data_conditional"),
        Input(ids.QC_RESULT_TABLE, "data"),
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def style_qc_status_cells(table_data):
        """Apply conditional styling to QC status cells based on their values.

        Colors:
        - Reliable: translucent green (#d4edda)
        - Unreliable: translucent red (#f8d7da)
        - Undecided: translucent orange/yellow (#fff3cd)
        - Unknown: translucent light grey (#e2e3e5)
        """
        if not table_data:
            return []

        styles = []

        # Define status-to-color mapping
        status_colors = {
            t_("general.reliable"): PlotConstants.STATUS_RELIABLE_BG,
            t_("general.unreliable"): PlotConstants.STATUS_UNRELIABLE_BG,
            t_("general.undecided"): PlotConstants.STATUS_UNDECIDED_BG,
            t_("general.unknown"): PlotConstants.STATUS_UNKNOWN_BG,
        }

        # Create conditional styles for each status
        for status_value, color in status_colors.items():
            styles.append(
                {
                    "if": {
                        "filter_query": (
                            f"{{{ColumnNames.STATUS_QUALITY_CONTROL}}}"
                            f' = "{status_value}"'
                        ),
                        "column_id": ColumnNames.STATUS_QUALITY_CONTROL,
                    },
                    "backgroundColor": color,
                }
            )

        return styles

    @app.callback(
        Output(ids.QC_RESULT_TABLE, "data"),
        Input(ids.QC_RESULT_TABLE_STORE_1, "data"),
        Input(ids.QC_RESULT_TABLE_STORE_2, "data"),
        Input(ids.QC_RESULT_TABLE_STORE_3, "data"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def update_results_table_data(*tables, **kwargs):
        """Update results table data from triggered store.

        Switches between multiple table update sources (from different callbacks).
        """
        if not any(tables):
            logger.debug("QC update table data: no tables present, preventing update")
            raise PreventUpdate

        ctx_obj = get_callback_context(**kwargs)
        triggered_id = ctx_obj.triggered_id
        inputs_list = ctx_obj.inputs_list

        # Find which input was triggered
        for i, input_item in enumerate(inputs_list):
            if input_item["id"] == triggered_id:
                return tables[i]

        logger.debug(
            "QC update table data: no matching triggered_id=%s, preventing update",
            triggered_id,
        )
        raise PreventUpdate

    # NOTE: this callback does not work in DEBUG mode
    if not config.get("DEBUG"):
        app.clientside_callback(
            """
            function() {
                //console.log(dash_clientside.callback_context);
                const triggered_id = dash_clientside.callback_context.triggered_id;
                //use this to set the focus on last active component
                document.lastActiveElement.focus(); 
                return;
            }
            """,
            # Hidden div output no longer necessary in since dash 2.17
            # Output("hidden-div", "children"),
            # This triggers the javascript callback:
            Input({"type": ids.QC_RESULT_MARK_OBS_BUTTONS, "index": ALL}, "n_clicks"),
            prevent_initial_call=True,
        )
