import dash_bootstrap_components as dbc
from dash import dcc, html

from gwdatalens.app.settings import ASSETS_PATH

from . import ids

# load Modal helper text from MarkDown
with open(ASSETS_PATH / "qc_dashboard_help.md", "r") as f:
    help_md = dcc.Markdown("".join(f.readlines()), mathjax=True)


def render():
    return html.Div(
        [
            dbc.Button(
                html.Span(
                    [html.I(className="fa-solid fa-circle-info"), " Help"],
                    id="span-open-help",
                    n_clicks=0,
                ),
                id=ids.HELP_BUTTON_OPEN,
                class_name="ms-auto",
            ),
            dbc.Modal(
                [
                    dbc.ModalHeader(
                        dbc.ModalTitle(
                            html.H3(
                                "About GW DataLens",
                                id=ids.HELP_TITLE,
                            ),
                        ),
                    ),
                    dbc.ModalBody(help_md),
                    dbc.ModalFooter(
                        [
                            html.I(
                                "Developed by D.A. Brakenhoff "
                                "and R.C. Caljé, Artesia, 2024"
                            ),
                            dbc.Button(
                                "Close",
                                id=ids.HELP_BUTTON_CLOSE,
                                className="ms-auto",
                                n_clicks=0,
                            ),
                        ]
                    ),
                ],
                id=ids.HELP_MODAL,
                is_open=False,
                scrollable=True,
                size="xl",
            ),
        ]
    )
