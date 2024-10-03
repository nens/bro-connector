from dash import dcc

from . import ids, tab_model, tab_overview, tab_qc, tab_qc_result


def render():
    """Renders the tab container.

    Returns
    -------
    dcc.Tabs
        A Dash Tabs component containing the overview, model, QC, and QC result tabs.
    """
    return dcc.Tabs(
        id=ids.TAB_CONTAINER,
        value=ids.TAB_OVERVIEW,
        children=[
            tab_overview.render(),
            tab_model.render(),
            tab_qc.render(),
            tab_qc_result.render(),
        ],
    )
