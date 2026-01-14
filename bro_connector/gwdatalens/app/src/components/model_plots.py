from dash import __version__ as DASH_VERSION
from dash import dcc, html
from packaging.version import parse as parse_version

from gwdatalens.app.constants import UI
from gwdatalens.app.src.components import ids


def render_results() -> html.Div:
    """Plot time series models results.

    Returns
    -------
    html.Div
        A Div element containing the time series results plot.
    """
    kwargs = (
        {"delay_show": 50}
        if parse_version(DASH_VERSION) >= parse_version("2.17.0")
        else {}
    )
    return html.Div(
        children=[
            dcc.Loading(
                id=ids.LOADING_MODEL_RESULTS_CHART,
                type="circle",
                children=[
                    dcc.Graph(
                        id=ids.MODEL_RESULTS_CHART,
                        config={"displayModeBar": True, "scrollZoom": True},
                        style={
                            "height": "78cqh",
                            "margin-bottom": UI.MARGIN_BOTTOM,
                        },
                    )
                ],
                **kwargs,
            )
        ]
    )


def render_diagnostics() -> html.Div:
    """Plot the time series models diagnostics.

    Returns
    -------
    html.Div
        A Div component containing the diagnostics plot.
    """
    kwargs = (
        {"delay_show": 50}
        if parse_version(DASH_VERSION) >= parse_version("2.17.0")
        else {}
    )
    return html.Div(
        children=[
            dcc.Loading(
                id=ids.LOADING_MODEL_DIAGNOSTICS_CHART,
                type="circle",
                children=[
                    dcc.Graph(
                        id=ids.MODEL_DIAGNOSTICS_CHART,
                        config={"displayModeBar": True, "scrollZoom": True},
                        style={
                            "height": "78cqh",
                            "margin-bottom": UI.MARGIN_BOTTOM,
                        },
                    )
                ],
                **kwargs,
            )
        ]
    )
