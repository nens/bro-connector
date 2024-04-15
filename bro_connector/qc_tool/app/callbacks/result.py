import i18n
import numpy as np
import pandas as pd
from dash import ALL, Input, Output, Patch, State, ctx, dcc, no_update
from dash.exceptions import PreventUpdate
from icecream import ic

try:
    from ..src.cache import cache
    from ..src.components import ids
    from ..src.components.overview_chart import plot_obs

except ImportError:
    from src.cache import cache
    from src.components import ids
    from src.components.overview_chart import plot_obs


def register_result_callbacks(app, data):
    @app.callback(
        Output(ids.QC_RESULT_CHART, "figure"),
        Output(ids.QC_RESULT_EXPORT_CSV, "disabled"),
        Output(ids.QC_RESULT_EXPORT_DB, "disabled"),
        Input(ids.TAB_CONTAINER, "value"),
        Input(ids.TRAVAL_RESULT_FIGURE_STORE, "data"),
    )
    def qc_result_traval_figure(tab, figure):
        if tab == ids.TAB_QC_RESULT:
            if figure is not None:
                figure["layout"]["dragmode"] = "select"
                return (figure, False, False)
            else:
                return ({"layout": {"title": "No traval result."}}, True, True)
        else:
            raise PreventUpdate

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
        Output(ids.ALERT, "is_open", allow_duplicate=True),
        Output(ids.ALERT, "color", allow_duplicate=True),
        Output(ids.ALERT_BODY, "children", allow_duplicate=True),
        Input(ids.QC_RESULT_EXPORT_DB, "n_clicks"),
        State(ids.SELECTED_OSERIES_STORE, "data"),
        prevent_initial_call=True,
    )
    def export_to_db(n_clicks, name):
        if n_clicks:
            if data.traval.traval_result is not None:
                df = data.traval.traval_result.copy()
                mask = df["reliable"] == 1.0
                df.loc[mask, "qualifier_by_category"] = "goedgekeurd"
                mask = df["reliable"] == 0.0
                df.loc[mask, "qualifier_by_category"] = "afgekeurd"
                data.db.save_qualifier(df)
                try:
                    data.db.save_qualifier(df)
                    # clear cache entry, maybe do not cache plot_obs at all?
                    cache.delete_memoized(plot_obs)
                    return (
                        True,
                        "success",
                        f"Succesfully exported to Database: {name}",
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
            return no_update

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

    # @app.callback(
    #     Output(ids.QC_RESULT_TABLE, "data", allow_duplicate=True),
    #     Output(ids.ACTIVE_TABLE_SELECTION_STORE, "data", allow_duplicate=True),
    #     Output(
    #         {"type": ids.QC_RESULT_MARK_OBS_BUTTONS, "index": ALL},
    #         "disabled",
    #         allow_duplicate=True,
    #     ),
    #     Input(ids.QC_RESULT_CHART, "selectedData"),
    #     State(ids.ACTIVE_TABLE_SELECTION_STORE, "data"),
    #     State(ids.QC_RESULT_TABLE, "selected_cells"),
    #     prevent_initial_call=True,
    # )
    # def filter_table_from_result_chart(
    #     selected_data, active_table_selection, table_selection
    # ):
    #     # ic(active_table_selection)
    #     if active_table_selection:
    #         # ic("Hit first trap")
    #         return no_update, False, [no_update, no_update, no_update]
    #     if table_selection is not None and len(table_selection) > 0:
    #         return no_update, False, [no_update, no_update, no_update]
    #     if selected_data is not None and len(selected_data) > 0:
    #         pts = pd.DataFrame(selected_data["points"])
    #         if pts.empty:
    #             # ic("Hit second trap")
    #             return (
    #                 data.traval.traval_result.reset_index(names="datetime").to_dict(
    #                     "records"
    #                 ),
    #                 False,
    #                 [True, True, True],
    #             )
    #         t = pd.to_datetime(pts["x"].unique())
    #         # mask = data.traval.traval_result["datetime"].isin(t)
    #         return (
    #             data.traval.traval_result.loc[t]
    #             .reset_index(names="datetime")
    #             .to_dict("records"),
    #             False,
    #             [False, False, False],
    #         )
    #     elif data.traval.traval_result is not None:
    #         return (
    #             data.traval.traval_result.reset_index(names="datetime").to_dict(
    #                 "records"
    #             ),
    #             False,
    #             [True, True, True],
    #         )
    #     else:
    #         return no_update, False, [no_update, no_update, no_update]

    # @app.callback(
    #     Output(ids.QC_RESULT_CHART, "selectedData", allow_duplicate=True),
    #     Output(ids.QC_RESULT_CHART, "figure", allow_duplicate=True),
    #     Output(ids.ACTIVE_TABLE_SELECTION_STORE, "data", allow_duplicate=True),
    #     Output(
    #         {"type": ids.QC_RESULT_MARK_OBS_BUTTONS, "index": ALL},
    #         "disabled",
    #         allow_duplicate=True,
    #     ),
    #     Output(ids.QC_RESULT_CLEAR_TABLE_SELECTION, "disabled", allow_duplicate=True),
    #     Input(ids.QC_RESULT_TABLE, "selected_cells"),
    #     prevent_initial_call=True,
    # )
    # def select_points_in_chart_from_table(selected_cells):
    #     ic(ctx.triggered_id)
    #     if selected_cells is not None:
    #         selected_row_ids = [c["row_id"] for c in selected_cells]
    #         series = data.traval.traval_result

    #         selectedData = {
    #             "points": [
    #                 {
    #                     "curveNumber": 2,  # TODO: if no pastas model, the original series is trace 0
    #                     "pointNumber": series["id"].iloc[i],
    #                     "pointIndex": series["id"].iloc[i],
    #                     "x": series.index[i],
    #                     "y": series["values"].iloc[i],
    #                 }
    #                 for i in selected_row_ids
    #             ]
    #         }
    #         ptspatch = Patch()
    #         # TODO: if no pastas model, the original series is trace 0
    #         ptspatch["data"][2]["selectedpoints"] = selected_row_ids
    #         active_selection = len(selected_row_ids) > 0
    #         disabled = len(selected_row_ids) == 0
    #         disable_clearable = len(selected_row_ids) == 0
    #     else:
    #         selectedData = {}
    #         active_selection = False
    #         # ptspatch = Patch()
    #         # # TODO: if no pastas model, the original series is trace 0
    #         # ptspatch["data"][2]["selectedpoints"] = []
    #         ptspatch = no_update
    #         disabled = no_update
    #         disable_clearable = True

    #     # ic(active_selection)

    #     return (
    #         selectedData,
    #         ptspatch,
    #         active_selection,
    #         [disabled, disabled, disabled],
    #         disable_clearable,
    #     )

    @app.callback(
        Output(ids.SELECTED_OBS_STORE, "data"),
        Output(ids.QC_RESULT_CLEAR_TABLE_SELECTION, "disabled"),
        Output(
            {"type": ids.QC_RESULT_MARK_OBS_BUTTONS, "index": ALL},
            "disabled",
            allow_duplicate=True,
        ),
        Input(ids.QC_RESULT_TABLE, "selected_cells"),
        Input(ids.QC_RESULT_CHART, "selectedData"),
        # State(ids.SELECTED_OBS_STORE, "data"),
        prevent_initial_call=True,
    )
    def update_selected_observations(
        table_selection,
        chart_selection,
        # current_selection_state,
        **kwargs,
    ):
        ctx = kwargs["callback_context"]
        ic(ctx)
        if table_selection is None and chart_selection is None:
            return {"trigger": None, "selection": None}, True, [True] * 3
        if ctx.triggered_id == ids.QC_RESULT_TABLE:
            # if current_selection_state["trigger"] == ids.QC_RESULT_CHART:
            #     raise PreventUpdate
            trigger = ids.QC_RESULT_TABLE
            if table_selection is None or len(table_selection) == 0:
                return {"trigger": trigger, "selection": None}, True, [True] * 3
            selection = [c["row_id"] for c in table_selection]
        elif ctx.triggered_id == ids.QC_RESULT_CHART:
            trigger = ids.QC_RESULT_CHART
            # if current_selection_state["trigger"] == ids.QC_RESULT_TABLE:
            #     raise PreventUpdate
            if chart_selection is None or len(chart_selection) == 0:
                return {"trigger": trigger, "selection": None}, True, [True] * 3
            pts = pd.DataFrame(chart_selection["points"])
            if pts.empty:
                raise PreventUpdate
            # TODO: if no pastas model, the original series is trace 0
            selection = pts.loc[pts.curveNumber == 2, "pointIndex"].tolist()
        else:
            return {"trigger": None, "selection": None}, True, [True] * 3
        return {"trigger": trigger, "selection": selection}, False, [False] * 3

    @app.callback(
        Output(ids.QC_RESULT_CHART, "figure", allow_duplicate=True),
        Output(ids.QC_RESULT_CHART, "selectedData", allow_duplicate=True),
        Output(ids.QC_RESULT_TABLE, "data", allow_duplicate=True),
        Input(ids.SELECTED_OBS_STORE, "data"),
        prevent_initial_call=True,
    )
    def synchronize_selections(selection):
        if selection is None or data.traval.traval_result is None:
            raise PreventUpdate

        trigger = selection["trigger"]
        selected_points = selection["selection"]

        if selected_points is None or (len(selected_points) == 0):
            update_figure = no_update
            update_figure_selection = no_update
            update_table = data.traval.traval_result.reset_index(
                names="datetime"
            ).to_dict("records")
            return update_figure, update_figure_selection, update_table

        if trigger == ids.QC_RESULT_CHART:
            update_figure = no_update
            update_figure_selection = no_update

            update_table = (
                data.traval.traval_result.iloc[np.sort(selected_points)]
                .reset_index(names="datetime")
                .to_dict("records")
            )

        elif trigger == ids.QC_RESULT_TABLE:
            update_table = no_update
            series = data.traval.traval_result

            update_figure_selection = {
                "points": [
                    {
                        "curveNumber": 2,  # TODO: if no pastas model, the original series is trace 0
                        "pointNumber": series["id"].iloc[i],
                        "pointIndex": series["id"].iloc[i],
                        "x": series.index[i],
                        "y": series["values"].iloc[i],
                    }
                    for i in selected_points
                ]
            }
            update_figure = Patch()
            # TODO: if no pastas model, the original series is trace 0
            update_figure["data"][2]["selectedpoints"] = selected_points
        else:
            raise PreventUpdate
        return update_figure, update_figure_selection, update_table

    @app.callback(
        Output(ids.QC_RESULT_TABLE, "selected_cells"),
        Output(ids.QC_RESULT_TABLE, "active_cell"),
        Output(
            {"type": ids.QC_RESULT_MARK_OBS_BUTTONS, "index": ALL},
            "disabled",
            allow_duplicate=True,
        ),
        Output(ids.QC_RESULT_CLEAR_TABLE_SELECTION, "disabled", allow_duplicate=True),
        Input(ids.QC_RESULT_CLEAR_TABLE_SELECTION, "n_clicks"),
        prevent_initial_call=True,
    )
    def clear_table_selection(n):
        if n:
            return (
                [],  # selected cells in table
                None,  # active cell in table
                [True, True, True],
                True,
            )
        else:
            raise PreventUpdate

    @app.callback(
        Output(ids.QC_RESULT_TABLE, "data", allow_duplicate=True),
        Output(ids.ALERT, "is_open", allow_duplicate=True),
        Output(ids.ALERT, "color", allow_duplicate=True),
        Output(ids.ALERT_BODY, "children", allow_duplicate=True),
        Input({"type": ids.QC_RESULT_MARK_OBS_BUTTONS, "index": ALL}, "n_clicks"),
        State(ids.QC_RESULT_TABLE, "derived_virtual_data"),
        State(ids.QC_RESULT_CHART, "selectedData"),
        prevent_initial_call=True,
    )
    def mark_obs(n, table_view, selected_points, **kwargs):
        if any(v is not None for v in n):
            ic(ctx)
            ctx = kwargs["callback_context"]
            if ctx.triggered_id["index"] == "reliable":
                value = 1
            elif ctx.triggered_id["index"] == "suspect":
                value = 0
            elif ctx.triggered_id["index"] == "unknown":
                value = -1
            else:
                raise PreventUpdate
            df = data.traval.traval_result
            table = pd.DataFrame(table_view)
            # if table is empty (because of filtering or whatever) do not allow updating
            # labels
            if table.empty:
                return (
                    no_update,
                    True,
                    "warning",
                    i18n.t("general.alert_failed_labeling"),
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
                    True,
                    "warning",
                    i18n.t("general.alert_failed_labeling"),
                )
            df.loc[selected_pts, "reliable"] = value
            t = table["datetime"].tolist()
            return (
                df.loc[t].reset_index(names="datetime").to_dict("records"),
                False,
                "success",
                "",
            )
        else:
            raise PreventUpdate
