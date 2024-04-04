from dash import dcc

from . import ids, tab_model, tab_overview, tab_qc, tab_qc_result


def render():
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
