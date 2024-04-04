from dash import Dash, dcc, html
from django_plotly_dash import DjangoDash
from ..data.source import DataInterface
from . import alert, button_help_modal, ids, tabs


def create_layout(app: DjangoDash, data: DataInterface) -> html.Div:
    """Create app layout.

    Parameters
    ----------
    app : Dash
        dash app object
    data : DataInterface
        data class

    Returns
    -------
    html.Div
        html containing app layout.
    """
    return html.Div(
        id="main",
        children=[
            dcc.Store(id=ids.SELECTED_OSERIES_STORE),
            dcc.Store(id=ids.PASTAS_MODEL_STORE),
            dcc.Store(id=ids.OVERVIEW_TABLE_SELECTION),
            dcc.Store(id=ids.ACTIVE_TABLE_SELECTION_STORE),
            dcc.Store(id=ids.TRAVAL_RULESET_STORE),
            dcc.Store(id=ids.TRAVAL_RESULT_FIGURE_STORE),
            dcc.Store(id=ids.TRAVAL_RESULT_TABLE_STORE),
            dcc.Store(id=ids.SELECTED_OBS_STORE),
            html.Div(
                id="header",
                children=[
                    html.H1(app.title, id="app_title"),
                    alert.render(),
                    button_help_modal.render(),
                ],
            ),
            tabs.render(),
            html.Div(id=ids.TAB_CONTENT),
        ],
    )
