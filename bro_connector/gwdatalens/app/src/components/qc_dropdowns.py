from typing import List, Optional

import i18n
from dash import dcc, html
from traval import rulelib

from ..data.interface import DataInterface
from . import ids


def render_selection_series_dropdown(
    data: DataInterface, selected_data: Optional[List]
):
    """Renders a dropdown component for selecting a time series.

    Parameters
    ----------
    data : DataInterface
        An interface to the data source containing the series information.
    selected_data : Optional[List]
        A list of selected data items. If a single item is selected, it will be set
        as the default value in the dropdown.

    Returns
    -------
    html.Div
        A Dash HTML Div component containing the dropdown.
    """
    locs = data.db.list_locations()
    options = [
        {"label": f"{i} ({data.db.gmw_gdf.at[i, 'nitg_code']})", "value": i}
        for i in locs
    ]

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
    """Render a dropdown component for selecting additional series.

    Locations are sorted based on distance from selected location in main dropdown.

    Parameters
    ----------
    data : DataInterface
        An interface to the data source, providing methods to query data.
    selected_data : list or None
        The currently selected data. If None, the dropdown will be disabled.

    Returns
    -------
    html.Div
        A Dash HTML Div component containing the dropdown for additional series
        selection.
    """
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
    """Renders a dropdown component for adding rules for the error detection algorithm.

    This function generates a dropdown menu with options populated from
    the `traval.rulelib` module. Each option corresponds to a rule whose name
    starts with "rule_*".

    Returns
    -------
    html.Div
        A Dash HTML Div component containing the dropdown menu.

    Notes
    -----
    - The dropdown is clearable, allowing users to remove their selection.
    - The dropdown is searchable.
    """
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
