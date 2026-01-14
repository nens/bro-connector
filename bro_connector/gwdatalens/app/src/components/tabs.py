from dash import dcc

from gwdatalens.app.constants import ConfigDefaults
from gwdatalens.app.src.components import (
    ids,
    tab_corrections,
    tab_model,
    tab_overview,
    tab_qc,
    tab_qc_result,
)


def render() -> dcc.Tabs:
    """Renders the tab container.

    Returns
    -------
    dcc.Tabs
        A Dash Tabs component containing the overview, model, QC, and QC result tabs.
    """
    return dcc.Tabs(
        id=ids.TAB_CONTAINER,
        value=ConfigDefaults.DEFAULT_TAB,
        children=[
            tab_overview.render(),
            tab_model.render(),
            tab_qc.render(),
            tab_qc_result.render(),
            tab_corrections.render(),
        ],
    )
