import dash_bootstrap_components as dbc
import i18n
from dash import dcc, html

from ..cache import TIMEOUT, cache
from ..data.source import DataInterface
from . import ids, overview_chart, overview_map, overview_table


def render():
    return dcc.Tab(
        label=i18n.t("general.tab_overview"),
        value=ids.TAB_OVERVIEW,
        className="custom-tab",
        selected_className="custom-tab--selected",
    )


def render_cancel_button():
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


@cache.memoize(timeout=TIMEOUT)
def render_content(data: DataInterface, selected_data: str):
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
            dbc.Row([render_cancel_button()]),
            dbc.Row(
                [
                    overview_chart.render(data, selected_data),
                ],
            ),
        ],
        fluid=True,
    )
