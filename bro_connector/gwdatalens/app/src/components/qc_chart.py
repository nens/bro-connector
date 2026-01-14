from dash import __version__ as DASH_VERSION
from dash import dcc, html
from packaging.version import parse as parse_version

from gwdatalens.app.config import config
from gwdatalens.app.constants import UI, ConfigDefaults
from gwdatalens.app.src.cache import cache
from gwdatalens.app.src.components import ids
from gwdatalens.app.src.utils import conditional_cache


@conditional_cache(
    cache.memoize,
    (not config.get("DJANGO_APP") and config.get("CACHING")),
    timeout=ConfigDefaults.CACHE_TIMEOUT,
)
def render() -> html.Div:
    """Render QC chart.

    Returns
    -------
    dash_html_components.Div
        A Div component containing the QC chart.
    """
    kwargs = (
        {"delay_show": 500}
        if parse_version(DASH_VERSION) >= parse_version("2.17.0")
        else {}
    )
    return html.Div(
        id="series-chart-div",
        children=[
            dcc.Loading(
                id=ids.LOADING_QC_CHART,
                type="dot",
                style={"position": "absolute", "align-self": "center"},
                parent_className="loading-wrapper",
                children=[
                    dcc.Graph(
                        id=ids.QC_CHART,
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
