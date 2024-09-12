from typing import List, Optional

import i18n
from dash import dcc, html
from traval import rulelib

from ..data.interface import DataInterface
from . import ids


def render_selection_series_dropdown(
    data: DataInterface, selected_data: Optional[List]
):
    locs = data.db.list_locations()
    options = [{"label": i, "value": i} for i in locs]

    if selected_data is not None and len(selected_data) == 1:
        value = selected_data[0]
    else:
        value = None

    return html.Div(
        children=[
            dcc.Dropdown(
                options=options,
                value=value,
                clearable=True,
                searchable=True,
                placeholder=i18n.t("general.select_series"),
                id=ids.QC_DROPDOWN_SELECTION,
                disabled=False,
            )
        ]
    )


def render_additional_series_dropdown(data: DataInterface, selected_data):
    if selected_data is not None:
        locs = data.db.list_locations_sorted_by_distance(selected_data[0])
        options = [
            {"label": i + f" ({row.distance / 1e3:.1f} km)", "value": i}
            for i, row in locs.iterrows()
        ]
    else:
        options = []
    return html.Div(
        children=[
            dcc.Dropdown(
                options=options,
                clearable=True,
                searchable=True,
                placeholder=i18n.t("general.select_series2"),
                id=ids.QC_DROPDOWN_ADDITIONAL,
                disabled=selected_data is None,
                multi=True,
            )
        ]
    )


def render_add_rule_dropdown():
    options = [
        {"value": i, "label": i}
        for i in [rule for rule in dir(rulelib) if rule.startswith("rule_")]
    ]

    return html.Div(
        [
            dcc.Dropdown(
                id=ids.TRAVAL_ADD_RULE_DROPDOWN,
                clearable=True,
                placeholder=i18n.t("general.select_rule"),
                value=None,
                multi=False,
                searchable=True,
                disabled=False,
                options=options,
            )
        ]
    )
