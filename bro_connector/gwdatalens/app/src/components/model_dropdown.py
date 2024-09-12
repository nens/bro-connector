import i18n
from dash import dcc, html

from . import ids


def render(data, selected_data):
    locs = data.db.list_locations()
    options = [{"label": i, "value": i} for i in locs]

    if selected_data is not None and len(selected_data) == 1:
        value = selected_data[0]
    else:
        value = None

    return html.Div(
        [
            dcc.Dropdown(
                id=ids.MODEL_DROPDOWN_SELECTION,
                clearable=True,
                placeholder=i18n.t("general.select_location"),
                value=value,
                multi=False,
                searchable=True,
                disabled=False,
                options=options,
            )
        ]
    )
