from typing import List, Optional

from dash import dcc, html
from traval import rulelib

from gwdatalens.app.constants import ColumnNames
from gwdatalens.app.messages import t_
from gwdatalens.app.src.components import ids
from gwdatalens.app.src.data.data_manager import DataManager
from gwdatalens.app.src.data.qc_custom_rules import CUSTOM_RULE_NAMES


def render_selection_series_dropdown(
    data: DataManager, selected_data: Optional[List[int]]
) -> html.Div:
    """Renders a dropdown component for selecting a time series.

    Parameters
    ----------
    data : DataInterface
        An interface to the data source containing the series information.
    selected_data : Optional[List]
        A list of ids of selected data items. If a single item is selected,
        it will be set as the default value in the dropdown.

    Returns
    -------
    html.Div
        A Dash HTML Div component containing the dropdown.
    """
    locs = data.db.list_observation_wells_with_data
    locs.sort_values(ColumnNames.DISPLAY_NAME, inplace=True)
    options = [
        {"label": row[ColumnNames.DISPLAY_NAME], "value": row[ColumnNames.ID]}
        for _, row in locs.iterrows()
    ]

    if selected_data is not None and len(selected_data) == 1:
        wid = selected_data[0]
    else:
        wid = None

    return html.Div(
        children=[
            dcc.Dropdown(
                options=options,
                value=wid,
                clearable=True,
                searchable=True,
                placeholder=t_("general.select_series"),
                id=ids.QC_DROPDOWN_SELECTION,
                disabled=False,
            )
        ]
    )


def render_additional_series_dropdown(
    data: DataManager, selected_data: Optional[List[int]]
) -> html.Div:
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
        locs = data.db.list_observation_wells_with_data_sorted_by_distance(
            selected_data[0]
        )
        options = [
            {
                "label": row[ColumnNames.DISPLAY_NAME]
                + f" ({row.distance / 1e3:.1f} km)",
                "value": row[ColumnNames.ID],
            }
            for _, row in locs.iterrows()
        ]
    else:
        options = []
    return html.Div(
        children=[
            dcc.Dropdown(
                options=options,
                clearable=True,
                searchable=True,
                placeholder=t_("general.select_series2"),
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
        + CUSTOM_RULE_NAMES
    ]

    return html.Div(
        [
            dcc.Dropdown(
                id=ids.TRAVAL_ADD_RULE_DROPDOWN,
                clearable=True,
                placeholder=t_("general.select_rule"),
                value=None,
                multi=False,
                searchable=True,
                disabled=False,
                options=options,
            )
        ]
    )
