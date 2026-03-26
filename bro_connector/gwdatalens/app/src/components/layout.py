from dash import Dash, dcc, html

from gwdatalens.app.src.components import (
    button_help_modal,
    button_load_pastastore,
    ids,
    tabs,
)
from gwdatalens.app.src.components.time_range_filter import (
    default_store_value,
    render_time_range_filter,
)
from gwdatalens.app.src.data import DataManager


def create_layout(app: Dash, data: DataManager) -> html.Div:
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
        id="gwdatalans-main",
        className="gwdatalens-main",
        children=[
            dcc.Store(id=ids.SELECTED_OSERIES_STORE),
            dcc.Store(id=ids.PASTAS_MODEL_STORE),
            dcc.Store(id=ids.ACTIVE_TABLE_SELECTION_STORE),
            dcc.Store(id=ids.TRAVAL_RULESET_STORE),
            dcc.Store(id=ids.TRAVAL_RESULT_FIGURE_STORE),
            dcc.Store(id=ids.TRAVAL_RESULT_TABLE_STORE),
            dcc.Store(id=ids.OVERVIEW_TIME_RANGE_REFRESH_STORE),
            dcc.Store(id=ids.PASTASTORE_REFRESH_STORE),
            # Global time-range store — persists across all tab changes
            dcc.Store(
                id=ids.TIME_RANGE_STORE,
                data=default_store_value(),
                storage_type="session",
            ),
            # alert containers (global scope only)
            dcc.Store(id=ids.ALERT_TAB_RENDER),
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
            dcc.Store(id=ids.ALERT_STATUS_CORRECTIONS),
            dcc.Store(id=ids.ALERT_LOAD_PASTASTORE),
            # header + tabs
            html.Div(
                id="header",
                children=[
                    html.H1(app.title, id="app_title"),
                    html.Div(id=ids.ALERT_DIV),
                    # Right-side controls: time-range filter + help button
                    html.Div(
                        className="d-flex align-items-center gap-3",
                        children=[
                            render_time_range_filter(),
                            button_load_pastastore.render(),
                            button_help_modal.render(),
                        ],
                    ),
                ],
            ),
            tabs.render(),
            html.Div(id=ids.TAB_CONTENT),
        ],
    )
