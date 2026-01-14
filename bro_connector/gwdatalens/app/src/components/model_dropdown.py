from typing import Any, List, Optional

from dash import dcc, html

from gwdatalens.app.constants import ColumnNames
from gwdatalens.app.messages import t_
from gwdatalens.app.src.components import ids


def render(data: Any, selected_data: Optional[List[int]]) -> html.Div:
    """Renders a dropdown component for selecting a time series.

    Parameters
    ----------
    data : object
        An object that contains a database connection with methods to list
        locations and access location data.
    selected_data : list or None
        A list containing the internal ids of currently selected location(s).
        If None or the list is empty, no location is pre-selected.

    Returns
    -------
    html.Div
        A Dash HTML Div component containing a Dropdown for selecting a location.
    """
    locs = data.db.list_observation_wells_with_data
    locs.sort_values(ColumnNames.DISPLAY_NAME, inplace=True)
    options = [
        {"label": row[ColumnNames.DISPLAY_NAME], "value": row[ColumnNames.ID]}
        for _, row in locs.iterrows()
    ]

    if selected_data is not None and len(selected_data) == 1:
        value = selected_data[0]
    else:
        value = None

    return html.Div(
        [
            dcc.Dropdown(
                id=ids.MODEL_DROPDOWN_SELECTION,
                clearable=True,
                placeholder=t_("general.select_location"),
                value=value,
                multi=False,
                searchable=True,
                disabled=False,
                options=options,
            )
        ]
    )
