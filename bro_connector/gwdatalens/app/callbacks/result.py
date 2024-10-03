from ast import literal_eval

import i18n
import numpy as np
import pandas as pd
from dash import ALL, Input, Output, Patch, State, ctx, dcc, no_update
from dash.exceptions import PreventUpdate

from gwdatalens.app.settings import settings
from gwdatalens.app.src.components import ids


def register_result_callbacks(app, data):
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
    #             mask = data.traval.traval_result["id"] == r["id"]
    #             data.traval.traval_result.loc[
    #                 mask, changed_cell["column_id"]
    #             ] = new_value
    #             r[changed_cell["column_id"]] = new_value
    #     return data.traval.traval_result.reset_index(names="datetime").to_dict(
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
    def apply_qc_label(value, table_view, selected_points):
        if value is not None:
            df = data.traval.traval_result
            table = pd.DataFrame(table_view)
            # if table is empty (because of filtering or whatever) do not allow updating
            # labels
            if table.empty:
                return (
                    no_update,
                    (True, "warning", i18n.t("general.alert_failed_labeling")),
                    None,
                )

            selected_pts = pd.to_datetime(
                pd.DataFrame(selected_points["points"])["x"]
            ).tolist()

            # if any observations are not listed in table do not allow update
            if np.any(
                ~np.isin(
                    pd.to_datetime(selected_pts), pd.to_datetime(table["datetime"])
                )
            ):
                return (
                    no_update,
                    (True, "warning", i18n.t("general.alert_failed_labeling")),
                    None,
                )
            df.loc[selected_pts, "category"] = value
            t = table["datetime"].tolist()
            return (
                df.loc[t].reset_index(names="datetime").to_dict("records"),
                (False, "success", ""),
                None,
            )
        else:
            raise PreventUpdate

    @app.callback(
        Output(ids.DOWNLOAD_EXPORT_CSV, "data"),
        Input(ids.QC_RESULT_EXPORT_CSV, "n_clicks"),
        State(ids.SELECTED_OSERIES_STORE, "data"),
        prevent_initial_call=True,
    )
    def download_export_csv(n_clicks, name):
        timestr = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestr}_qc_result_{name[0]}.csv"
        if data.traval.traval_result is not None:
            return dcc.send_string(data.traval.traval_result.to_csv, filename=filename)

    @app.callback(
        Output(ids.ALERT_EXPORT_TO_DB, "data"),
        Input(ids.QC_RESULT_EXPORT_DB, "n_clicks"),
        State(ids.SELECTED_OSERIES_STORE, "data"),
        State(ids.QC_RESULT_EXPORT_QC_STATUS_FLAG, "value"),
        prevent_initial_call=True,
    )
    def export_to_db(n_clicks, name, non_flagged_reliable):
        if n_clicks:
            if data.traval.traval_result is not None:
                df = data.traval.traval_result.copy()

                mask_incoming_not_suspect = ~df["incoming_status_quality_control"].isin(
                    ["afgekeurd", "onbeslist"]
                )
                if settings["LOCALE"] == "en":
                    bro_en_to_nl = {
                        "": "",
                        "unknown": "onbekend",
                        "undecided": "onbeslist",
                        "unreliable": "afgekeurd",
                        "reliable": "goedgekeurd",
                        "onbekend": "onbekend",
                        "onbeslist": "onbeslist",
                        "afgekeurd": "afgekeurd",
                        "goedgekeurd": "goedgekeurd",
                    }
                    df["status_quality_control"] = df["status_quality_control"].apply(
                        lambda v: bro_en_to_nl[v]
                    )
                    df["incoming_status_quality_control"] = df[
                        "incoming_status_quality_control"
                    ].apply(lambda v: bro_en_to_nl[v])

                mask = df["status_quality_control"] == ""
                if non_flagged_reliable == "all_not_suspect":
                    # overwrite status to reliable for all except obs
                    # already flagged as suspect
                    df.loc[
                        mask & mask_incoming_not_suspect, "status_quality_control"
                    ] = "goedgekeurd"
                    # set status for incoming suspects
                    df.loc[~mask_incoming_not_suspect, "status_quality_control"] = (
                        df.loc[
                            ~mask_incoming_not_suspect,
                            "incoming_status_quality_control",
                        ]
                    )
                elif non_flagged_reliable == "suspect":
                    # only overwrite status to suspect for erroneous obs
                    df.loc[mask, "status_quality_control"] = df.loc[
                        mask, "incoming_status_quality_control"
                    ]
                elif non_flagged_reliable == "all":
                    df.loc[mask, "status_quality_control"] = "goedgekeurd"
                else:
                    raise ValueError(
                        f"Invalid value {non_flagged_reliable} for non_flagged_reliable"
                    )

                try:
                    data.db.save_qualifier(df)
                    return (
                        True,
                        "success",
                        f"Successfully exported to Database: {name}",
                    )
                except Exception as e:
                    return (
                        True,
                        "danger",
                        f"Database export failed: {name}. Error: {e}",
                    )
            else:
                return (
                    True,
                    "warning",
                    "No QC result to export.",
                )
        else:
            raise PreventUpdate

    @app.callback(
        Output(ids.QC_RESULT_TABLE, "filter_query"),
        Input(ids.QC_RESULTS_SHOW_ALL_OBS_SWITCH, "value"),
        State(ids.QC_RESULT_TABLE, "filter_query"),
        prevent_initial_call=True,
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
    def synchronize_selected_observations(
        table_selection,
        chart_selection,
        click_clear,
        click_select,
        current_table,
        **kwargs,
    ):
        if len(kwargs) > 0:
            ctx_ = kwargs["callback_context"]
            triggered_id = ctx_.triggered[0]["prop_id"].split(".")[0]
        else:
            triggered_id = ctx.triggered_id

        if click_clear and triggered_id == ids.QC_RESULT_CLEAR_TABLE_SELECTION:
            update_figure = Patch()
            # TODO: if no pastas model, the original series is trace 0
            update_figure["data"][2]["selectedpoints"] = []

            update_figure_selection = None
            update_table = data.traval.traval_result.reset_index(
                names="datetime"
            ).to_dict("records")
            update_table_selection = []
            disable_deselect = True
            disable_select = False
            disable_mark_buttons = True
            disable_qc_label_dropdown = True
            return (
                update_figure,
                update_figure_selection,
                update_table,
                update_table_selection,
                None,
                disable_deselect,
                disable_select,
                [disable_mark_buttons] * 4,
                disable_qc_label_dropdown,
            )
        if click_select and triggered_id == ids.QC_RESULT_TABLE_SELECT_ALL:
            selection = [row["id"] for row in current_table]
            series = data.traval.traval_result
            update_figure_selection = {
                "points": [
                    {
                        # TODO: if no pastas model, the original series is trace 0
                        "curveNumber": 2,
                        "pointNumber": series["id"].iloc[i],
                        "pointIndex": series["id"].iloc[i],
                        "x": series.index[i],
                        "y": series["values"].iloc[i],
                    }
                    for i in selection
                ]
            }
            update_figure = Patch()
            # TODO: if no pastas model, the original series is trace 0
            update_figure["data"][2]["selectedpoints"] = []
            update_table = no_update
            new_table_selection = [
                {"column": 0, "column_id": "datetime", "row": i, "row_id": rowid}
                for i, rowid in enumerate(selection)
            ]
            update_table_selection = new_table_selection
            disable_deselect = False
            disable_select = True
            disable_mark_buttons = False
            disable_qc_label_dropdown = False
            return (
                update_figure,
                update_figure_selection,
                update_table,
                update_table_selection,
                None,
                disable_deselect,
                disable_select,
                [disable_mark_buttons] * 4,
                disable_qc_label_dropdown,
            )

        # determine trigger and selection
        if table_selection is None and chart_selection is None:
            trigger = None
            selection = None
            disable_qc_label_dropdown = True

        # if table get selection from table
        if triggered_id == ids.QC_RESULT_TABLE:
            # if current_selection_state["trigger"] == ids.QC_RESULT_CHART:
            #     raise PreventUpdate
            trigger = ids.QC_RESULT_TABLE
            if table_selection is None or len(table_selection) == 0:
                selection = None
            else:
                selection = [c["row_id"] for c in table_selection]

        # if chart get selected pts from chart
        elif triggered_id == ids.QC_RESULT_CHART:
            trigger = ids.QC_RESULT_CHART
            # if current_selection_state["trigger"] == ids.QC_RESULT_TABLE:
            #     raise PreventUpdate
            if chart_selection is None or len(chart_selection) == 0:
                selection = None
            else:
                pts = pd.DataFrame(chart_selection["points"])
                if pts.empty:
                    raise PreventUpdate
                # TODO: if no pastas model, the original series is trace 0
                selection = pts.loc[pts.curveNumber == 2, "pointIndex"].tolist()

        # determine what to update and how

        # selection is empty
        if selection is None or (len(selection) == 0):
            update_figure = no_update
            update_figure_selection = no_update
            if data.traval.traval_result is not None:
                update_table = data.traval.traval_result.reset_index(
                    names="datetime"
                ).to_dict("records")
                update_table_selection = []
            else:
                update_table = no_update
                update_table_selection = no_update
            disable_deselect = True
            disable_select = False
            disable_mark_buttons = True
            disable_qc_label_dropdown = True
            return (
                update_figure,
                update_figure_selection,
                update_table,
                update_table_selection,
                None,
                disable_deselect,
                disable_select,
                [disable_mark_buttons] * 4,
                disable_qc_label_dropdown,
            )

        # if trigger was chart, update table
        if trigger == ids.QC_RESULT_CHART:
            update_figure = no_update
            update_figure_selection = no_update

            update_table = (
                data.traval.traval_result.iloc[np.sort(selection)]
                .reset_index(names="datetime")
                .to_dict("records")
            )
            update_table_selection = []  # np.sort(selection).tolist()

        # if trigger was table update chart
        elif trigger == ids.QC_RESULT_TABLE:
            update_table = no_update
            update_table_selection = no_update
            series = data.traval.traval_result

            update_figure_selection = {
                "points": [
                    {
                        # TODO: if no pastas model, the original series is trace 0
                        "curveNumber": 2,
                        "pointNumber": series["id"].iloc[i],
                        "pointIndex": series["id"].iloc[i],
                        "x": series.index[i],
                        "y": series["values"].iloc[i],
                    }
                    for i in selection
                ]
            }
            update_figure = Patch()
            # TODO: if no pastas model, the original series is trace 0
            update_figure["data"][2]["selectedpoints"] = selection

        # otherwise do nothing
        else:
            raise PreventUpdate

        disable_select = False
        disable_deselect = table_selection is None
        disable_mark_buttons = table_selection is None
        disable_qc_label_dropdown = table_selection is None

        return (
            update_figure,
            update_figure_selection,
            update_table,
            update_table_selection,
            no_update,
            disable_deselect,
            disable_select,
            [disable_mark_buttons] * 4,
            disable_qc_label_dropdown,
        )

    @app.callback(
        Output(ids.QC_RESULT_TABLE_STORE_2, "data"),
        Output(ids.ALERT_MARK_OBS, "data"),
        Input({"type": ids.QC_RESULT_MARK_OBS_BUTTONS, "index": ALL}, "n_clicks"),
        State(ids.QC_RESULT_TABLE, "derived_virtual_data"),
        State(ids.QC_RESULT_CHART, "selectedData"),
        prevent_initial_call=True,
    )
    def mark_obs(n, table_view, selected_points, **kwargs):
        if len(kwargs) > 0:
            ctx_ = kwargs["callback_context"]
            triggered_id = ctx_.triggered[0]["prop_id"].split(".")[0]
            triggered_id_index = literal_eval(triggered_id)["index"]
        else:
            triggered_id_index = ctx.triggered_id["index"]

        if any(v is not None for v in n):
            if triggered_id_index == "reliable":
                value = i18n.t("general.reliable")
            elif triggered_id_index == "unreliable":
                value = i18n.t("general.unreliable")
            elif triggered_id_index == "unknown":
                value = i18n.t("general.unknown")
            elif triggered_id_index == "undecided":
                value = i18n.t("general.undecided")
            else:
                raise PreventUpdate
            df = data.traval.traval_result
            table = pd.DataFrame(table_view)
            # if table is empty (because of filtering or whatever) do not allow updating
            # labels
            if table.empty:
                return (
                    no_update,
                    (True, "warning", i18n.t("general.alert_failed_labeling")),
                )

            selected_pts = pd.to_datetime(
                pd.DataFrame(selected_points["points"])["x"]
            ).tolist()

            # if any observations are not listed in table do not allow update
            if np.any(
                ~np.isin(
                    pd.to_datetime(selected_pts), pd.to_datetime(table["datetime"])
                )
            ):
                return (
                    no_update,
                    (True, "warning", i18n.t("general.alert_failed_labeling")),
                )
            df.loc[selected_pts, "status_quality_control"] = value
            t = table["datetime"].tolist()
            return (
                df.loc[t].reset_index(names="datetime").to_dict("records"),
                (False, "success", ""),
            )
        else:
            raise PreventUpdate

    @app.callback(
        Output(ids.QC_RESULT_TABLE, "data"),
        Input(ids.QC_RESULT_TABLE_STORE_1, "data"),
        Input(ids.QC_RESULT_TABLE_STORE_2, "data"),
        Input(ids.QC_RESULT_TABLE_STORE_3, "data"),
        prevent_initial_call=True,
    )
    def update_results_table_data(*tables, **kwargs):
        if len(kwargs) > 0:
            ctx_ = kwargs["callback_context"]
            triggered_id = ctx_.triggered[0]["prop_id"].split(".")[0]
            inputs_list = ctx_.inputs_list
        else:
            triggered_id = ctx.triggered_id
            inputs_list = ctx.inputs_list

        if any(tables):
            for i in range(len(inputs_list)):
                if inputs_list[i]["id"] == triggered_id:
                    break
            return tables[i]
        else:
            raise PreventUpdate
