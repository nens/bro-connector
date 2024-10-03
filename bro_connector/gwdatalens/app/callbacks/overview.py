import i18n
import numpy as np
import pandas as pd
from dash import Input, Output, Patch, State, no_update

from gwdatalens.app.settings import settings
from gwdatalens.app.src.components import ids
from gwdatalens.app.src.components.overview_chart import plot_obs


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
        current_value : str
            current selected value

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
        Output(ids.SERIES_CHART, "figure"),
        Output(ids.OVERVIEW_TABLE, "data"),
        Output(ids.ALERT_TIME_SERIES_CHART, "data"),
        Output(ids.OVERVIEW_TABLE_SELECTION_1, "data"),
        # Output(ids.UPDATE_OVERVIEW_TABLE, "data"),
        Input(ids.OVERVIEW_MAP, "selectedData"),
        State(ids.SELECTED_OSERIES_STORE, "data"),
        State(ids.OVERVIEW_TABLE_SELECTION_1, "data"),
        State(ids.OVERVIEW_TABLE_SELECTION_2, "data"),
        background=False,
        # NOTE: only used if background is True
        # running=[
        #     (Output(ids.OVERVIEW_CANCEL_BUTTON, "disabled"), False, True),
        # ],
        # cancel=[Input(ids.OVERVIEW_CANCEL_BUTTON, "n_clicks")],
        prevent_initial_call=True,
    )
    def plot_overview_time_series(
        selectedData, selected_oseries, table_selected_1, table_selected_2
    ):
        """Plots an overview time series based on selected data.

        Parameters
        ----------
        selectedData : dict
            Dictionary containing data points selected by the user on the map.
        selected_oseries : list
            List of selected observation series from store.
        table_selected_1 : tuple or None
            Tuple containing the date and table data for the first table selection.
        table_selected_2 : tuple or None
            Tuple containing the date and table data for the second table selection.

        Returns
        -------
        chart : dict
            Dictionary representing the chart layout and data.
        table : list
            List of records representing the table data.
        alert : tuple
            Tuple containing a boolean indicating whether to show an alert, the alert
            type, and the alert message.
        timestamp : tuple
            Tuple containing the current timestamp and a boolean indicating the status.
        """
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

        # check for newest entry whether selection was made from table
        date = pd.Timestamp("1900-01-01 00:00:00")  # some early date
        for value in [table_selected_1, table_selected_2]:
            if value is None:
                continue
            else:
                d, t = value
            if pd.Timestamp(d) > date:
                table_selected = t
                date = pd.Timestamp(d)

        if selectedData is not None:
            pts = pd.DataFrame(selectedData["points"])

            # get selected points
            if not pts.empty:
                names = pts["text"].tolist()
            else:
                names = None

            if names is not None and len(names) > settings["SERIES_LOAD_LIMIT"]:
                return (
                    no_update,
                    no_update,
                    (
                        True,
                        "warning",
                        i18n.t("general.max_selection_warning").format(
                            settings["SERIES_LOAD_LIMIT"]
                        ),
                    ),
                    (pd.Timestamp.now().isoformat(), False),
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
                        (False, None, None),
                        (pd.Timestamp.now().isoformat(), False),
                    )
                else:
                    return (
                        {"layout": {"title": i18n.t("general.no_data_selection")}},
                        table,
                        (True, "warning", f"No data to plot for: {names}."),
                        (pd.Timestamp.now().isoformat(), False),
                    )
            except Exception as e:
                # raise e
                return (
                    {"layout": {"title": i18n.t("general.no_series")}},
                    data.db.gmw_gdf.loc[:, usecols].reset_index().to_dict("records"),
                    (
                        True,  # show alert
                        "danger",  # alert color
                        f"Error! Something went wrong: {e}",  # alert message
                    ),
                    (pd.Timestamp.now().isoformat(), False),
                )
        elif selected_oseries is not None:
            chart = plot_obs(selected_oseries, data)
            table = data.db.gmw_gdf.loc[:, usecols].reset_index().to_dict("records")
            return (
                chart,
                table,
                (False, None, None),
                (pd.Timestamp.now().isoformat(), False),
            )
        else:
            table = data.db.gmw_gdf.loc[:, usecols].reset_index().to_dict("records")
            return (
                {"layout": {"title": i18n.t("general.no_series")}},
                table,
                (False, None, None),
                (pd.Timestamp.now().isoformat(), False),
            )

    @app.callback(
        Output(ids.OVERVIEW_MAP, "selectedData"),
        Output(ids.OVERVIEW_MAP, "figure"),
        Output(ids.OVERVIEW_TABLE_SELECTION_2, "data"),
        Input(ids.OVERVIEW_TABLE, "selected_cells"),
        State(ids.OVERVIEW_TABLE, "derived_virtual_data"),
        prevent_initial_call=True,
    )
    def highlight_point_on_map_from_table(selected_cells, table):
        """Highlights points on a map based on selected cells from overview table.

        Parameters
        ----------
        selected_cells : list of dict or None
            List of dictionaries containing information about selected cells.
            Each dictionary should have a "row" key. If None, the function returns
            no updates.
        table : dict
            records representing the table data.

        Returns
        -------
        tuple
            A tuple containing:
            - dict: A dictionary with information about the highlighted points.
            - Patch: An object representing the updated map patch with selected points.
            - tuple: A tuple containing the current timestamp and a boolean indicating
              if the update was successful.
        """
        if selected_cells is None:
            return no_update, no_update, (pd.Timestamp.now().isoformat(), False)

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
            (pd.Timestamp.now().isoformat(), True),
        )
