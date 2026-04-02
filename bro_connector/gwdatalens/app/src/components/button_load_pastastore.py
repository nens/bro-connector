import dash_bootstrap_components as dbc
from dash import dcc, html

from gwdatalens.app.messages import t_
from gwdatalens.app.src.components import ids


def render() -> html.Div:
    """Render upload button for loading a PastaStore from file."""
    return html.Div(
        [
            dcc.Upload(
                id=ids.LOAD_PASTASTORE_UPLOAD,
                accept=".pastastore,.zip",
                children=dbc.Button(
                    html.Span(
                        [
                            html.I(className="fa-solid fa-file-import"),
                            f" {t_('general.load')} PastaStore",
                        ]
                    ),
                    color="primary",
                    style={"backgroundColor": "#006f92"},
                ),
                multiple=False,
            ),
            dbc.Tooltip(
                t_("general.load") + " PastaStore (.pastastore/.zip)",
                target=ids.LOAD_PASTASTORE_UPLOAD,
                placement="left",
            ),
        ],
        className="d-inline-block",
    )
