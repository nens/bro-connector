from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
from dash import __version__ as DASH_VERSION
from dash import dcc, html
from packaging.version import parse as parse_version
from pandas import Timedelta, Timestamp

from gwdatalens.app.constants import (
    UI,
    ColumnNames,
    ConfigDefaults,
    PlotConstants,
    TimeRangeDefaults,
)
from gwdatalens.app.messages import t_
from gwdatalens.app.src.components import ids
from gwdatalens.app.src.data.data_manager import DataManager


def render(data: DataManager, selected_data: list[int] | None = None) -> html.Div:
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
    wids: list[int] | None,
    data: DataManager,
    plot_manual_obs: bool = False,
    tmin: str | None = None,
    tmax: str | None = None,
    time_range_preset: str | None = None,
) -> dict[str, Any]:  # noqa: C901
    """Plots observation data for given monitoring wells and tube numbers.

    Parameters
    ----------
    wids : list of int
        List of ids corresponding to monitoring wells and tube numbers.
    data : DataManager
        Data object containing database access and configuration.
    plot_manual_obs : bool, optional
        Whether to include control observations (controle metingen).
    tmin : str or None, optional
        ISO-8601 date string; only load data at or after this timestamp.
        When ``None`` no lower bound is applied.
    tmax : str or None, optional
        ISO-8601 date string; only load data at or before this timestamp.
        When ``None`` no upper bound is applied.
    time_range_preset : str or None, optional
        Active global time-range preset key. When there is no data in the
        selected period and this is a bounded preset (e.g. ``last_year``),
        axis limits are recalculated relative to "today".

    Returns
    -------
    dict
        A dictionary containing plot data and layout configuration for the observations.

    Notes
    -----
    - If `wids` is None, returns a layout with a title indicating no plot.
    - If a wid is not found in the database, it is skipped.
    - For a single wid, plots the timeseries data with different qualifiers and manual
      observations.
    - For multiple wids, plots the timeseries data with markers and lines.
    """
    if wids is None:
        return {"layout": {"title": {"text": t_("general.no_plot")}}}

    requested_tmin = None
    requested_tmax = None
    now = Timestamp.now().normalize()
    if tmin is not None:
        requested_tmin = Timestamp(tmin)
    if tmax is not None:
        requested_tmax = Timestamp(tmax)

    # Keep preset windows relative to current date for empty-period charts,
    # even when persisted store values were created on an earlier day.
    if (
        time_range_preset is not None
        and time_range_preset in TimeRangeDefaults.PRESETS
        and time_range_preset not in {"custom", "all"}
        and requested_tmax is None
    ):
        _, offset = TimeRangeDefaults.PRESETS[time_range_preset]
        if offset is not None:
            requested_tmin = now - pd.tseries.frequencies.to_offset(offset)

    hasobs = list(data.db.list_observation_wells_with_data[ColumnNames.ID])
    has_any_data = False

    traces = []
    series_colors = px.colors.qualitative.Set2
    manual_obs_colors = px.colors.qualitative.Dark2

    # Track min/max dates across all traces
    all_dates = []

    for i, wid in enumerate(wids):
        # no obs
        if wid not in hasobs:
            continue

        df = data.db.get_timeseries(wid, tmin=tmin, tmax=tmax)

        if df is None or df.empty:
            continue

        has_any_data = True

        # disable hoverinfo for performance on large datasets
        if df.shape[0] > ConfigDefaults.MAX_SCATTER_POINTS_HOVERINFO:
            hoverinfo = "skip"
        else:
            hoverinfo = None

        df[data.db.qualifier_column] = df.loc[:, data.db.qualifier_column].fillna("")
        display_name = str(df.index.name)

        # Track dates from this dataframe
        all_dates.extend(df.index.tolist())

        if len(wids) == 1:
            ts = df[data.db.value_column].dropna()
            trace_i = go.Scattergl(
                x=ts.index,
                y=ts.values,
                mode="lines",
                line={"width": 1, "color": "gray"},
                name=display_name,
                legendgroup=display_name,
                showlegend=True,
                hoverinfo=hoverinfo,
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
                    legendgroup=str(qualifier),
                    showlegend=True,
                    legendrank=legendrank,
                    hoverinfo=hoverinfo,
                )
                traces.append(trace_i)

            # add controle metingen
            manual_obs = data.db.get_timeseries(
                wid,
                observation_type="controlemeting",
                tmin=tmin,
                tmax=tmax,
            )
            if not manual_obs.empty:
                # Track manual obs dates
                all_dates.extend(manual_obs.index.tolist())
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
                    # hoverinfo=hoverinfo,
                )
                traces.append(trace_mo)
        else:
            ts = df[data.db.value_column]
            trace_i = go.Scattergl(
                x=ts.index,
                y=ts.values,
                mode="markers+lines",
                line={"width": 1, "color": series_colors[i % len(series_colors)]},
                marker={
                    "size": 3,
                    "color": series_colors[i % len(series_colors)],
                    "line_color": series_colors[i % len(series_colors)],
                },
                name=display_name,
                legendgroup=display_name,
                # name=name,
                # legendgroup=f"{name}-{tube_nr}",
                showlegend=True,
                legendrank=1001,
                hoverinfo=hoverinfo,
            )
            traces.append(trace_i)
            if plot_manual_obs:
                # add controle metingen
                manual_obs = data.db.get_timeseries(
                    wid,
                    observation_type="controlemeting",
                    tmin=tmin,
                    tmax=tmax,
                )
                if not manual_obs.empty:
                    # Track manual obs dates
                    all_dates.extend(manual_obs.index.tolist())
                    trace_mo_i = go.Scattergl(
                        x=manual_obs.index,
                        y=manual_obs[data.db.value_column],
                        mode="markers",
                        marker={
                            "size": 8,
                            "symbol": "x-thin",
                            "line_width": 2,
                            "line_color": manual_obs_colors[i % len(manual_obs_colors)],
                        },
                        name=t_("general.manual_observations"),
                        legendgroup=display_name,
                        legendrank=1000,
                        showlegend=True,
                        # hoverinfo=hoverinfo,
                    )
                    traces.append(trace_mo_i)

    # Set xaxis range
    xaxis_range = None
    days = None
    if all_dates:
        data_tmin = min(all_dates)
        data_tmax = max(all_dates)

        range_start = requested_tmin if requested_tmin is not None else data_tmin
        if requested_tmax is not None:
            range_end = requested_tmax
        elif requested_tmin is not None:
            range_end = now
        else:
            range_end = data_tmax

        if range_end < range_start:
            range_end = range_start

        xaxis_range = [range_start.timestamp() * 1000, range_end.timestamp() * 1000]
        days = (range_end - range_start) / Timedelta(days=1) + 1
    else:
        # No data in selected range: still show requested window if available
        default_end = requested_tmax if requested_tmax is not None else now
        if requested_tmin is not None:
            default_start = requested_tmin
        else:
            default_start = default_end - Timedelta(days=3650)

        if default_end < default_start:
            default_end = default_start

        xaxis_range = [default_start.timestamp() * 1000, default_end.timestamp() * 1000]
        days = (default_end - default_start) / Timedelta(days=1) + 1

    layout = {
        "title": {
            "text": "" if has_any_data else t_("general.no_data_available"),
            "x": 0.5,
        },
        "yaxis": {"title": "(m NAP)"},
        "xaxis": {
            "range": xaxis_range,
            "autorangeoptions": {
                "minallowed": xaxis_range[0],
                "maxallowed": xaxis_range[1],
            },
            "rangeslider": {
                "visible": True,
                "thickness": 0.1,
                "bgcolor": "lightgray",
                "range": xaxis_range,
            },
            "type": "date",
            "rangeselector": {
                "buttons": [
                    {
                        "count": 1,
                        "label": "1m",
                        "step": "month",
                        "stepmode": "backward",
                    },
                    {
                        "count": 3,
                        "label": "3m",
                        "step": "month",
                        "stepmode": "backward",
                    },
                    {
                        "count": 6,
                        "label": "6m",
                        "step": "month",
                        "stepmode": "backward",
                    },
                    {
                        "count": 1,
                        "label": "1y",
                        "step": "year",
                        "stepmode": "backward",
                    },
                ]
                + (
                    [
                        {
                            "count": int(days),
                            "label": "All",
                            "step": "day",
                            "stepmode": "backward",
                        }
                    ]
                    if days
                    else []
                ),
            },
        },
        "legend": {
            "traceorder": "reversed+grouped",
            "orientation": "h",
            "xanchor": "right",
            "yanchor": "bottom",
            "x": 1.0,
            "y": 1.02,
        },
        "dragmode": "pan",
        "margin": {"t": 85, "b": 20, "l": 20, "r": 10},
    }
    return {"data": traces, "layout": layout}
