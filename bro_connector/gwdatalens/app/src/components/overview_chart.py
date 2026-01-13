from typing import Any, Dict, List, Optional

import plotly.express as px
import plotly.graph_objs as go
from dash import __version__ as DASH_VERSION
from dash import dcc, html
from packaging.version import parse as parse_version

from gwdatalens.app.constants import UI, ColumnNames, PlotConstants
from gwdatalens.app.messages import t_
from gwdatalens.app.src.components import ids
from gwdatalens.app.src.data.data_manager import DataManager


def render(data: DataManager, selected_data: Optional[List[int]] = None) -> html.Div:
    kwargs = (
        {"delay_show": 500}
        if parse_version(DASH_VERSION) >= parse_version("2.17.0")
        else {}
    )
    return html.Div(
        id="series-chart-div",
        children=[
            dcc.Loading(
                id=ids.LOADING_SERIES_CHART,
                type="dot",
                style={"position": "absolute", "align-self": "center"},
                parent_className="loading-wrapper",
                children=[
                    dcc.Graph(
                        figure=plot_obs(selected_data, data),
                        id=ids.SERIES_CHART,
                        config={
                            "displayModeBar": True,
                            "scrollZoom": True,
                        },
                        style={
                            "height": "40cqh",
                        },
                    ),
                ],
                **kwargs,
            ),
        ],
        style={
            "position": "relative",
            "justify-content": "center",
            "margin-bottom": UI.MARGIN_BOTTOM,
        },
    )


def plot_obs(
    wids: Optional[List[int]],
    data: DataManager,
    plot_manual_obs: bool = False,
) -> Dict[str, Any]:
    """Plots observation data for given monitoring wells and tube numbers.

    Parameters
    ----------
    names : list of int
        List of ids corresponding to monitoring wells and tube numbers.
    data : object
        Data object containing database access and configuration.

    Returns
    -------
    dict
        A dictionary containing plot data and layout configuration for the observations.

    Notes
    -----
    - If `iids` is None, returns a layout with a title indicating no plot.
    - If an iid is not found in the database, it is skipped.
    - For a single iid, plots the timeseries data with different qualifiers and manual
      observations.
    - For multiple iids, plots the timeseries data with markers and lines.
    """
    if wids is None:
        return {"layout": {"title": {"text": t_("general.no_plot")}}}

    hasobs = list(data.db.list_observation_wells_with_data[ColumnNames.ID])
    no_data = []

    traces = []
    colors = px.colors.qualitative.Dark24
    for i, wid in enumerate(wids):
        # no obs
        if wid not in hasobs:
            no_data.append(True)
            continue

        df = data.db.get_timeseries(wid)

        if df is None:
            continue

        df[data.db.qualifier_column] = df.loc[:, data.db.qualifier_column].fillna("")
        display_name = df.index.name
        if len(wids) == 1:
            no_data.append(False)
            ts = df[data.db.value_column]
            trace_i = go.Scattergl(
                x=ts.index,
                y=ts.values,
                mode="lines",
                line={"width": 1, "color": "gray"},
                name=display_name,
                legendgroup=display_name,
                showlegend=True,
            )
            traces.append(trace_i)

            # plot different qualifiers
            for qualifier in df[data.db.qualifier_column].unique():
                mask = df[data.db.qualifier_column] == qualifier
                ts = df.loc[mask, data.db.value_column]
                legendrank = 1000
                if qualifier in ["goedgekeurd"]:
                    color = PlotConstants.STATUS_RELIABLE
                elif qualifier in ["onbeslist"]:
                    color = PlotConstants.STATUS_UNDECIDED
                elif qualifier in ["afgekeurd"]:
                    color = PlotConstants.STATUS_UNRELIABLE
                elif qualifier == "":
                    color = PlotConstants.STATUS_NO_QUALIFIER
                    # legendrank = 999
                else:
                    color = PlotConstants.STATUS_UNKNOWN
                trace_i = go.Scattergl(
                    x=ts.index,
                    y=ts.values,
                    mode="markers",
                    marker={"color": color, "size": 4},
                    name=qualifier,
                    legendgroup=qualifier,
                    showlegend=True,
                    legendrank=legendrank,
                )
                traces.append(trace_i)

            # add controle metingen
            manual_obs = data.db.get_timeseries(wid, observation_type="controlemeting")
            if not manual_obs.empty:
                trace_mo = go.Scattergl(
                    x=manual_obs.index,
                    y=manual_obs[data.db.value_column],
                    mode="markers",
                    marker={
                        "color": PlotConstants.CONTROL_OBS_COLOR,
                        "size": PlotConstants.CONTROL_OBS_SIZE,
                    },
                    name=t_("general.manual_observations"),
                    legendgroup="manual obs",
                    showlegend=True,
                    legendrank=1001,
                )
                traces.append(trace_mo)
        else:
            no_data.append(False)
            ts = df[data.db.value_column]
            trace_i = go.Scattergl(
                x=ts.index,
                y=ts.values,
                mode="markers+lines",
                line={"width": 1, "color": colors[i % len(colors)]},
                marker={"size": 3, "line_color": colors[i % len(colors)]},
                name=display_name,
                legendgroup=display_name,
                # name=name,
                # legendgroup=f"{name}-{tube_nr}",
                showlegend=True,
                legendrank=1001,
            )
            traces.append(trace_i)
            if plot_manual_obs:
                # add controle metingen
                manual_obs = data.db.get_timeseries(
                    wid, observation_type="controlemeting"
                )
                if not manual_obs.empty:
                    trace_mo_i = go.Scattergl(
                        x=manual_obs.index,
                        y=manual_obs[data.db.value_column],
                        mode="markers",
                        marker={
                            "size": 8,
                            "symbol": "x-thin",
                            "line_width": 2,
                            "line_color": colors[i % len(colors)],
                        },
                        name=t_("general.manual_observations"),
                        legendgroup=display_name,
                        legendrank=1000,
                        showlegend=True,
                    )
                    traces.append(trace_mo_i)
    layout = {
        # "xaxis": {"range": [sim.index[0], sim.index[-1]]},
        "yaxis": {"title": "(m NAP)"},
        "legend": {
            "traceorder": "reversed+grouped",
            "orientation": "h",
            "xanchor": "left",
            "yanchor": "bottom",
            "x": 0.0,
            "y": 1.02,
        },
        "dragmode": "pan",
        "margin": {"t": 60, "b": 20, "l": 20, "r": 10},
    }
    if all(no_data):
        return None
    else:
        return {"data": traces, "layout": layout}
