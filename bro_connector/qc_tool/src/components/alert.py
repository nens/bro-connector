import dash_bootstrap_components as dbc
from dash import html

from . import ids


def render():
    return html.Div(
        [
            dbc.Alert(
                children=[
                    html.P("Placeholder", id=ids.ALERT_BODY),
                ],
                id=ids.ALERT,
                color="success",
                dismissable=True,
                duration=4000,
                fade=True,
                is_open=False,
            ),
        ]
    )
