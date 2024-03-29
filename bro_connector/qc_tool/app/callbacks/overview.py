import i18n
import numpy as np
import pandas as pd
from dash import Input, Output, Patch, State, no_update

try:
    from ..src.components import ids
    from ..src.components.overview_chart import plot_obs
except ImportError:
    from src.components import ids
    from src.components.overview_chart import plot_obs


def register_overview_callbacks(app, data):
    @app.callback(
        Output(ids.SELECTED_OSERIES_STORE, "data"),
        Input(ids.OVERVIEW_MAP, "selectedData"),
        State(ids.SELECTED_OSERIES_STORE, "data"),
    )
    def store_modeldetails_dropdown_value(selected_data, current_value):
        """Store model results tab dropdown value.

        Parameters
        ----------
        selected_data : list of dict
            selected data points from map

        Returns
        -------
        names : list of str
            list of selected names
        """
        if selected_data is not None:
            pts = pd.DataFrame(selected_data["points"])
            if not pts.empty:
                names = pts["text"].tolist()
                return names
            else:
                return None if current_value is None else current_value
        else:
            return None if current_value is None else current_value

    @app.callback(
        Output(ids.SERIES_CHART, "figure", allow_duplicate=True),
        Output(ids.OVERVIEW_TABLE, "data", allow_duplicate=True),
        Output(ids.ALERT, "is_open", allow_duplicate=True),
        Output(ids.ALERT, "color", allow_duplicate=True),
        Output(ids.ALERT_BODY, "children", allow_duplicate=True),
        Output(ids.OVERVIEW_TABLE_SELECTION, "data", allow_duplicate=True),
        # Output(ids.UPDATE_OVERVIEW_TABLE, "data"),
        Input(ids.OVERVIEW_MAP, "selectedData"),
        State(ids.SELECTED_OSERIES_STORE, "data"),
        State(ids.OVERVIEW_TABLE_SELECTION, "data"),
        background=False,
        # NOTE: only used if background is True
        running=[
            (Output(ids.OVERVIEW_CANCEL_BUTTON, "disabled"), False, True),
        ],
        cancel=[Input(ids.OVERVIEW_CANCEL_BUTTON, "n_clicks")],
        prevent_initial_call=True,
    )
    def plot_overview_time_series(selectedData, selected_oseries, table_selected):
        usecols = [
            "id",
            "bro_id",
            # "nitg_code",
            "tube_number",
            "screen_top",
            "screen_bot",
            "x",
            "y",
            "metingen",
        ]

        if selectedData is not None:
            pts = pd.DataFrame(selectedData["points"])

            # get selected points
            if not pts.empty:
                names = pts["text"].tolist()
            else:
                names = None

            if len(names) > 10:
                return (
                    no_update,
                    no_update,
                    True,
                    "warning",
                    i18n.t("general.max_selection_warning"),
                    False,
                )

            if table_selected:
                table = no_update
            else:
                table = (
                    data.db.gmw_gdf.loc[names, usecols].reset_index().to_dict("records")
                )

            try:
                chart = plot_obs(names, data)
                if chart is not None:
                    return (
                        chart,
                        table,
                        False,
                        None,
                        None,
                        False,
                    )
                else:
                    return (
                        {"layout": {"title": i18n.t("general.no_data_selection")}},
                        table,
                        True,
                        "warning",
                        f"No data to plot for: {names}.",
                        False,
                    )
            except Exception as e:
                raise e
                return (
                    {"layout": {"title": i18n.t("general.no_series")}},
                    data.db.gmw_gdf.loc[:, usecols].reset_index().to_dict("records"),
                    True,  # show alert
                    "danger",  # alert color
                    f"Error! Something went wrong: {e}",  # alert message
                    False,
                )
        elif selected_oseries is not None:
            chart = plot_obs(selected_oseries, data)
            table = data.db.gmw_gdf.loc[:, usecols].reset_index().to_dict("records")
            return (
                chart,
                table,
                False,
                None,
                None,
                False,
            )
        else:
            table = data.db.gmw_gdf.loc[:, usecols].reset_index().to_dict("records")
            return (
                {"layout": {"title": i18n.t("general.no_series")}},
                table,
                False,
                None,
                None,
                False,
            )

    @app.callback(
        Output(ids.OVERVIEW_MAP, "selectedData"),
        Output(ids.OVERVIEW_MAP, "figure"),
        Output(ids.OVERVIEW_TABLE_SELECTION, "data", allow_duplicate=True),
        Input(ids.OVERVIEW_TABLE, "selected_cells"),
        State(ids.OVERVIEW_TABLE, "derived_virtual_data"),
        prevent_initial_call=True,
    )
    def highlight_point_on_map_from_table(selected_cells, table):
        if selected_cells is None:
            return no_update, no_update, False

        rows = np.unique([cell["row"] for cell in selected_cells]).tolist()
        df = pd.DataFrame.from_dict(table, orient="columns")
        loc = df.loc[rows]
        pts = loc["id"].tolist()

        dfm = data.db.gmw_gdf.reset_index().loc[pts].copy()
        dfm["curveNumber"] = 0
        mask = dfm.loc[:, "metingen"] == 1
        dfm.loc[mask, "curveNumber"] = 1

        # update selected points
        mappatch = Patch()
        mappatch["data"][1]["selectedpoints"] = dfm.loc[mask, "id"].tolist()
        mappatch["data"][0]["selectedpoints"] = dfm.loc[~mask, "id"].tolist()

        return (
            {
                "points": [
                    {
                        "curveNumber": dfm["curveNumber"].iloc[i],
                        "pointNumber": dfm["id"].iloc[i],
                        "pointIndex": dfm["id"].iloc[i],
                        "lon": dfm["lon"].iloc[i],
                        "lat": dfm["lat"].iloc[i],
                        "text": dfm["name"].iloc[i],
                    }
                    for i in range(loc.index.size)
                ]
            },
            mappatch,
            True,
        )
