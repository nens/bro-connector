import i18n
import plotly.graph_objs as go
from dash import __version__ as DASH_VERSION
from dash import dcc, html
from packaging.version import parse as parse_version

from . import ids


def render(data, selected_data):
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
                            "height": "40vh",
                            # "margin-bottom": "10px",
                            # "margin-top": 5,
                        },
                    ),
                ],
                **kwargs,
            ),
        ],
        style={
            "position": "relative",
            "justify-content": "center",
            "margin-bottom": 10,
        },
    )


def plot_obs(names, data):
    """Plots observation data for given monitoring wells and tube numbers.

    Parameters
    ----------
    names : list of str
        List of strings representing monitoring well and tube number in the format
        "{gmw_id}-{tube_id}".
    data : object
        Data object containing database access and configuration.

    Returns
    -------
    dict
        A dictionary containing plot data and layout configuration for the observations.

    Notes
    -----
    - If `names` is None, returns a layout with a title indicating no plot.
    - If a name is not found in the database, it is skipped.
    - For a single name, plots the timeseries data with different qualifiers and manual
      observations.
    - For multiple names, plots the timeseries data with markers and lines.
    """
    if names is None:
        return {"layout": {"title": i18n.t("general.no_plot")}}

    hasobs = list(data.db.list_locations())
    no_data = []

    traces = []
    for name in names:
        # split into monitoringwell and tube_number
        if "-" in name:
            monitoring_well, tube_nr = name.split("-")
        elif "_" in name:
            monitoring_well, tube_nr = name.split("_")
        else:
            raise ValueError(
                f"Error splitting name into monitoring well ID and tube number: {name}"
            )
        tube_nr = int(tube_nr)

        # no obs
        if name not in hasobs:
            no_data.append(True)
            continue

        df = data.db.get_timeseries(gmw_id=monitoring_well, tube_id=tube_nr)

        if df is None:
            continue

        df[data.db.qualifier_column] = df.loc[:, data.db.qualifier_column].fillna("")

        if len(names) == 1:
            no_data.append(False)
            ts = df[data.db.value_column]
            trace_i = go.Scattergl(
                x=ts.index,
                y=ts.values,
                mode="lines",
                line={"width": 1, "color": "gray"},
                name=name + data.db.get_nitg_code(name),
                legendgroup=f"{name}-{tube_nr}",
                showlegend=True,
            )
            traces.append(trace_i)

            # plot different qualifiers
            for qualifier in df[data.db.qualifier_column].unique():
                mask = df[data.db.qualifier_column] == qualifier
                ts = df.loc[mask, data.db.value_column]
                legendrank = 1000
                if qualifier in ["goedgekeurd"]:
                    color = "green"
                elif qualifier in ["onbeslist"]:
                    color = "orange"
                elif qualifier in ["afgekeurd"]:
                    color = "red"
                elif qualifier == "":
                    color = "#636EFA"
                    # legendrank = 999
                else:
                    color = "gray"
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

            manual_obs = data.db.get_timeseries(
                monitoring_well, tube_nr, observation_type="controlemeting"
            )
            if not manual_obs.empty:
                trace_mo = go.Scattergl(
                    x=manual_obs.index,
                    y=manual_obs[data.db.value_column],
                    mode="markers",
                    marker={"color": "red", "size": 7},
                    name=i18n.t("general.manual_observations"),
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
                line={"width": 1},
                marker={"size": 3},
                name=name,
                legendgroup=f"{name}-{tube_nr}",
                showlegend=True,
            )
            traces.append(trace_i)
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
        # "margin": dict(t=20, b=20, l=50, r=20),
        "margin-top": 0,
    }
    if all(no_data):
        return None
    else:
        return {"data": traces, "layout": layout}
