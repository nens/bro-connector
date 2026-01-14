import logging
from typing import List, Optional

import dash_bootstrap_components as dbc
from dash import dcc, html

from gwdatalens.app.messages import t_
from gwdatalens.app.src.components import (
    ids,
    model_buttons,
    model_dropdown,
    model_plots,
)
from gwdatalens.app.src.data.data_manager import DataManager

logger = logging.getLogger(__name__)


def render() -> dcc.Tab:
    """Renders the Model Tab.

    Returns
    -------
    dcc.Tab
        The model tab
    """
    return dcc.Tab(
        label=t_("general.tab_model"),
        value=ids.TAB_MODEL,
        className="custom-tab",
        selected_className="custom-tab--selected",
    )


def render_datepicker_tmin(
    data: DataManager, selected_data: Optional[List[int]]
) -> dcc.DatePickerSingle:
    """Renders a DatePickerSingle component for selecting the minimum date (tmin).

    Parameters
    ----------
    data : object
        The data object containing the `pstore` attribute, which provides
        access to the `get_tmin_tmax` method.
    selected_data : list or None
        A list containing the internal ids of selected data.
        If the list contains exactly one item, the function will attempt
        to retrieve the tmin date for that item. If None or the list length
        is not 1, the date picker will be disabled.

    Returns
    -------
    dcc.DatePickerSingle
        A Dash DatePickerSingle component for selecting a start time.
    """
    if selected_data is not None and len(selected_data) == 1:
        wid = selected_data[0]
        name = data.db.gmw_gdf.loc[wid, "display_name"]
        try:
            tmintmax = data.pastastore.get_tmin_tmax(libname="oseries", names=[name])
            start_date = tmintmax.loc[name, "tmin"].to_pydatetime()
            disabled = False
        except KeyError:
            logger.exception("No time series for well id %s", wid)
            raise
        # if other error converting to datetime, do not set date
        except Exception:
            start_date = None
            disabled = True
    else:
        start_date = None
        disabled = False

    return dcc.DatePickerSingle(
        date=start_date,
        placeholder=t_("general.tmin"),
        display_format="YYYY-MM-DD",
        show_outside_days=True,
        number_of_months_shown=1,
        day_size=30,
        disabled=disabled,
        id=ids.MODEL_DATEPICKER_TMIN,
        style={"fontSize": 8},
    )


def render_datepicker_tmax(
    data: DataManager, selected_data: Optional[List[int]]
) -> dcc.DatePickerSingle:
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
        wid = selected_data[0]
        name = data.db.gmw_gdf.loc[wid, "display_name"]
        try:
            tmintmax = data.pastastore.get_tmin_tmax(libname="oseries", names=[name])
            end_date = tmintmax.loc[name, "tmax"].to_pydatetime()
            disabled = False
        except KeyError:
            logger.exception("No time series for well id %s", wid)
            raise
        # if other error converting to datetime, do not set date
        except Exception:
            end_date = None
            disabled = True
    else:
        end_date = None
        disabled = False

    return dcc.DatePickerSingle(
        date=end_date,
        placeholder=t_("general.tmax"),
        display_format="YYYY-MM-DD",
        show_outside_days=True,
        number_of_months_shown=1,
        day_size=20,
        disabled=disabled,
        id=ids.MODEL_DATEPICKER_TMAX,
        style={"fontSize": 8},
    )


def render_checkbox() -> dbc.Checkbox:
    """Renders a checkbox component for running error detection on subset of obs.

    Returns
    -------
    dbc.Checkbox
        A checkbox allowing the user to select whether to run error detection
        only on unvalidated observations, or on all observations.
    """
    return dbc.Checkbox(
        id=ids.MODEL_USE_ONLY_VALIDATED,
        label=t_("general.model_use_only_validated"),
        value=False,
    )


def render_content(data: DataManager, selected_data: List):
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
                                    t_("general.powered_by") + " ",
                                    html.A(
                                        "Pastas",
                                        href="https://pastas.dev",
                                        target="_blank",
                                    ),
                                ]
                            )
                        ],
                        width="auto",
                        className="ms-auto",
                    ),
                ],
                className="align-items-center",
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
            # duplicate callback outputs stores
            dcc.Store(id=ids.MODEL_RESULTS_CHART_1),
            dcc.Store(id=ids.MODEL_RESULTS_CHART_2),
            dcc.Store(id=ids.MODEL_DIAGNOSTICS_CHART_1),
            dcc.Store(id=ids.MODEL_DIAGNOSTICS_CHART_2),
            dcc.Store(id=ids.MODEL_SAVE_BUTTON_1),
            dcc.Store(id=ids.MODEL_SAVE_BUTTON_2),
        ],
        fluid=True,
    )
