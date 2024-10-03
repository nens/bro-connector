import dash_bootstrap_components as dbc
import i18n
from dash import dcc, html

from gwdatalens.app.settings import settings

from ..cache import TIMEOUT, cache
from ..data.interface import DataInterface
from ..utils import conditional_cache
from . import ids, overview_chart, overview_map, overview_table


def render():
    """Renders a Dash Tab component for the overview tab.

    Returns
    -------
    dcc.Tab
        overview tab
    """
    return dcc.Tab(
        label=i18n.t("general.tab_overview"),
        value=ids.TAB_OVERVIEW,
        className="custom-tab",
        selected_className="custom-tab--selected",
    )


def render_cancel_button():
    """Renders a cancel button component.

    Currently not in use.

    Returns
    -------
    html.Div
        A Div containing a disabled cancel button.
    """
    return html.Div(
        children=[
            dbc.Button(
                html.Span(
                    [
                        html.I(className="fa-regular fa-circle-stop"),
                        " " + i18n.t("general.cancel"),
                    ],
                    id="span-cancel-button",
                    n_clicks=0,
                ),
                style={
                    "margin-top": 10,
                    "margin-bottom": 10,
                },
                disabled=True,
                id=ids.OVERVIEW_CANCEL_BUTTON,
            ),
        ]
    )


@conditional_cache(
    cache.memoize,
    (not settings["DJANGO_APP"] and settings["CACHING"]),
    timeout=TIMEOUT,
)
def render_content(data: DataInterface, selected_data: str):
    """Renders the content for the overview tab.

    Parameters
    ----------
    data : DataInterface
        The data interface object containing the data to be rendered.
    selected_data : str
        The identifier for the selected data to be displayed.

    Returns
    -------
    dbc.Container
        A Dash Bootstrap Component container with the rendered content,
        including a map, table, and chart.
    """
    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            overview_map.render(data, selected_data),
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            overview_table.render(data, selected_data),
                        ],
                        width=6,
                    ),
                ],
                style={"height": "45vh"},
            ),
            # dbc.Row([render_cancel_button()]),
            dbc.Row(
                [
                    overview_chart.render(data, selected_data),
                ],
            ),
        ],
        fluid=True,
    )
