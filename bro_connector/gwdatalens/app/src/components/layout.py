from dash import Dash, dcc, html

from ..data import DataInterface
from . import button_help_modal, ids, tabs


def create_layout(app: Dash, data: DataInterface) -> html.Div:
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
            dcc.Store(id=ids.ACTIVE_TABLE_SELECTION_STORE),
            dcc.Store(id=ids.TRAVAL_RULESET_STORE),
            dcc.Store(id=ids.TRAVAL_RESULT_FIGURE_STORE),
            dcc.Store(id=ids.TRAVAL_RESULT_TABLE_STORE),
            # alert containers
            dcc.Store(id=ids.ALERT_TIME_SERIES_CHART),
            dcc.Store(id=ids.ALERT_DISPLAY_RULES_FOR_SERIES),
            dcc.Store(id=ids.ALERT_GENERATE_MODEL),
            dcc.Store(id=ids.ALERT_SAVE_MODEL),
            dcc.Store(id=ids.ALERT_PLOT_MODEL_RESULTS),
            dcc.Store(id=ids.ALERT_EXPORT_TO_DB),
            dcc.Store(id=ids.ALERT_MARK_OBS),
            dcc.Store(id=ids.ALERT_LABEL_OBS),
            dcc.Store(id=ids.ALERT_LOAD_RULESET),
            dcc.Store(id=ids.ALERT_RUN_TRAVAL),
            dcc.Store(id=ids.ALERT_TAB_RENDER),
            # duplicate containers
            dcc.Store(id=ids.OVERVIEW_TABLE_SELECTION_1),
            dcc.Store(id=ids.OVERVIEW_TABLE_SELECTION_2),
            dcc.Store(id=ids.MODEL_RESULTS_CHART_1),
            dcc.Store(id=ids.MODEL_RESULTS_CHART_2),
            dcc.Store(id=ids.MODEL_DIAGNOSTICS_CHART_1),
            dcc.Store(id=ids.MODEL_DIAGNOSTICS_CHART_2),
            dcc.Store(id=ids.MODEL_SAVE_BUTTON_1),
            dcc.Store(id=ids.MODEL_SAVE_BUTTON_2),
            dcc.Store(id=ids.QC_DROPDOWN_ADDITIONAL_DISABLED_1),
            dcc.Store(id=ids.QC_DROPDOWN_ADDITIONAL_DISABLED_2),
            dcc.Store(id=ids.TRAVAL_RULES_FORM_STORE_1, data=[]),
            dcc.Store(id=ids.TRAVAL_RULES_FORM_STORE_2, data=[]),
            dcc.Store(id=ids.TRAVAL_RULES_FORM_STORE_3, data=[]),
            dcc.Store(id=ids.TRAVAL_RULES_FORM_STORE_4, data=[]),
            dcc.Store(id=ids.TRAVAL_RESET_RULESET_BUTTON_STORE_1),
            dcc.Store(id=ids.TRAVAL_RESET_RULESET_BUTTON_STORE_2),
            dcc.Store(id=ids.TRAVAL_RESET_RULESET_BUTTON_STORE_3),
            dcc.Store(id=ids.QC_RESULT_TABLE_STORE_1),
            dcc.Store(id=ids.QC_RESULT_TABLE_STORE_2),
            dcc.Store(id=ids.QC_RESULT_TABLE_STORE_3),
            dcc.Store(id=ids.LOADING_QC_CHART_STORE_1),
            dcc.Store(id=ids.LOADING_QC_CHART_STORE_2),
            dcc.Store(id=ids.QC_CHART_STORE_1),
            dcc.Store(id=ids.QC_CHART_STORE_2),
            # header + tabs
            html.Div(
                id="header",
                children=[
                    html.H1(app.title, id="app_title"),
                    html.Div(id=ids.ALERT_DIV),
                    # alert.render(),
                    button_help_modal.render(),
                ],
            ),
            tabs.render(),
            html.Div(id=ids.TAB_CONTENT),
        ],
    )
