import dash_bootstrap_components as dbc
from dash import dcc, html

from gwdatalens.app.config import config
from gwdatalens.app.constants import UI, ConfigDefaults
from gwdatalens.app.messages import t_
from gwdatalens.app.src.cache import cache
from gwdatalens.app.src.components import (
    ids,
    overview_chart,
    overview_map,
    overview_table,
)
from gwdatalens.app.src.data.data_manager import DataManager
from gwdatalens.app.src.utils import conditional_cache


def render() -> dcc.Tab:
    """Renders a Dash Tab component for the overview tab.

    Returns
    -------
    dcc.Tab
        overview tab
    """
    return dcc.Tab(
        label=t_("general.tab_overview"),
        value=ids.TAB_OVERVIEW,
        className="custom-tab",
        selected_className="custom-tab--selected",
    )


def render_cancel_button() -> html.Div:
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
                        " " + t_("general.cancel"),
                    ],
                    id="span-cancel-button",
                    n_clicks=0,
                ),
                style={
                    "margin-top": UI.MARGIN_TOP,
                    "margin-bottom": UI.MARGIN_BOTTOM,
                },
                disabled=True,
                id=ids.OVERVIEW_CANCEL_BUTTON,
            ),
        ]
    )


@conditional_cache(
    cache.memoize,
    (not config.get("DJANGO_APP") and config.get("CACHING")),
    timeout=ConfigDefaults.CACHE_TIMEOUT,
)
def render_content(data: DataManager, selected_data: str):
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
                style={"height": "45cqh"},
            ),
            # dbc.Row([render_cancel_button()]),
            dbc.Row(
                [
                    overview_chart.render(data, selected_data),
                ],
            ),
            # duplicate callback outputs stores
            dcc.Store(id=ids.OVERVIEW_TABLE_SELECTION_1),
            dcc.Store(id=ids.OVERVIEW_TABLE_SELECTION_2),
        ],
        fluid=True,
    )
