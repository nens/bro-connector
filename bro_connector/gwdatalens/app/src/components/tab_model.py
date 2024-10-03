from typing import List

import dash_bootstrap_components as dbc
import i18n
from dash import dcc, html

from ..data.interface import DataInterface
from . import ids, model_buttons, model_dropdown, model_plots


def render():
    """Renders the Model Tab.

    Returns
    -------
    dcc.Tab
        The model tab
    """
    return dcc.Tab(
        label=i18n.t("general.tab_model"),
        value=ids.TAB_MODEL,
        className="custom-tab",
        selected_className="custom-tab--selected",
    )


def render_datepicker_tmin(data, selected_data):
    """Renders a DatePickerSingle component for selecting the minimum date (tmin).

    Parameters
    ----------
    data : object
        The data object containing the `pstore` attribute, which provides
        access to the `get_tmin_tmax` method.
    selected_data : list or None
        A list containing the selected data. If the list contains exactly one
        item, the function will attempt to retrieve the tmin date for that
        item. If None or the list length is not 1, the date picker will be
        disabled.

    Returns
    -------
    dcc.DatePickerSingle
        A Dash DatePickerSingle component for selecting a start time.
    """
    if selected_data is not None and len(selected_data) == 1:
        name = selected_data[0]
        try:
            tmintmax = data.pstore.get_tmin_tmax("oseries", name)
            start_date = tmintmax.loc[name, "tmin"].to_pydatetime()
            disabled = False
        except Exception:
            start_date = None
            disabled = True
    else:
        start_date = None
        disabled = True

    return dcc.DatePickerSingle(
        date=start_date,
        placeholder=i18n.t("general.tmin"),
        display_format="YYYY-MM-DD",
        show_outside_days=True,
        number_of_months_shown=1,
        day_size=30,
        disabled=disabled,
        id=ids.MODEL_DATEPICKER_TMIN,
        style={"fontSize": 8},
    )


def render_datepicker_tmax(data, selected_data):
    """Renders a DatePickerSingle component for selecting the maximum date (tmax).

    Parameters
    ----------
    data : object
        The data object containing the `pstore` attribute, which provides
        access to the `get_tmin_tmax` method.
    selected_data : list or None
        A list containing the selected data. If the list contains exactly one
        item, the function will attempt to retrieve the tmax date for that
        item. If None or the list length is not 1, the date picker will be
        disabled.

    Returns
    -------
    dcc.DatePickerSingle
        A Dash DatePickerSingle component for selecting a end time.
    """
    if selected_data is not None and len(selected_data) == 1:
        name = selected_data[0]
        try:
            tmintmax = data.pstore.get_tmin_tmax("oseries", name)
            end_date = tmintmax.loc[name, "tmax"].to_pydatetime()
            disabled = False
        except Exception:
            end_date = None
            disabled = True
    else:
        end_date = None
        disabled = True

    return dcc.DatePickerSingle(
        date=end_date,
        placeholder=i18n.t("general.tmax"),
        display_format="YYYY-MM-DD",
        show_outside_days=True,
        number_of_months_shown=1,
        day_size=20,
        disabled=disabled,
        id=ids.MODEL_DATEPICKER_TMAX,
        style={"fontSize": 8},
    )


def render_checkbox():
    """Renders a checkbox component for running error detection on subset of obs.

    Returns
    -------
    dbc.Checkbox
        A checkbox allowing the user to select whether to run error detection
        only on unvalidated observations, or on all observations.
    """
    return dbc.Checkbox(
        id=ids.MODEL_USE_ONLY_VALIDATED,
        label=i18n.t("general.model_use_only_validated"),
        value=False,
    )


def render_content(data: DataInterface, selected_data: List):
    """Renders the content for the model tab.

    Parameters
    ----------
    data : DataInterface
        The data interface containing the necessary data for rendering.
    selected_data : List
        A list of selected data items.

    Returns
    -------
    dbc.Container
        A Dash Bootstrap Container with the rendered content.
    """
    return dbc.Container(
        [
            dbc.Row(
                children=[
                    dbc.Col([model_dropdown.render(data, selected_data)], width=4),
                    dbc.Col(
                        [render_datepicker_tmin(data, selected_data)], width="auto"
                    ),
                    dbc.Col(
                        [render_datepicker_tmax(data, selected_data)], width="auto"
                    ),
                    dbc.Col([model_buttons.render_generate_button()], width="auto"),
                    dbc.Col([model_buttons.render_save_button()], width="auto"),
                    dbc.Col([render_checkbox()], width="auto"),
                    dbc.Col(
                        [
                            html.P(
                                [
                                    i18n.t("general.powered_by") + " ",
                                    html.A(
                                        "Pastas",
                                        href="https://pastas.dev",
                                        target="_blank",
                                    ),
                                ]
                            )
                        ],
                        width="auto",
                    ),
                ],
            ),
            dbc.Row(
                [
                    # Column 1: Model results plot
                    dbc.Col(
                        children=[
                            model_plots.render_results(),
                        ],
                        width=6,
                    ),
                    # Column 2: Model diagnostics plot
                    dbc.Col(
                        children=[
                            model_plots.render_diagnostics(),
                        ],
                        width=6,
                    ),
                ]
            ),
        ],
        fluid=True,
    )
