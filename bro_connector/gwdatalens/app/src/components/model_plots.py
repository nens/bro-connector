from dash import dcc, html

from . import ids


def render_results():
    return html.Div(
        children=[
            dcc.Loading(
                id="loading_chart",
                type="circle",
                children=[
                    dcc.Graph(
                        id=ids.MODEL_RESULTS_CHART,
                        config={"displayModeBar": True, "scrollZoom": True},
                        style={"height": "78vh", "margin-bottom": "1vh"},
                    )
                ],
            )
        ]
    )


def render_diagnostics():
    return html.Div(
        children=[
            dcc.Loading(
                id="loading_chart",
                type="circle",
                children=[
                    dcc.Graph(
                        id=ids.MODEL_DIAGNOSTICS_CHART,
                        config={"displayModeBar": True, "scrollZoom": True},
                        style={"height": "78vh", "margin-bottom": "1vh"},
                    )
                ],
            )
        ]
    )
