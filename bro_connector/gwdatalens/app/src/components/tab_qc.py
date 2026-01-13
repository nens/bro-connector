from typing import List, Optional

import dash_bootstrap_components as dbc
from dash import dcc, html

from gwdatalens.app.constants import UI
from gwdatalens.app.messages import t_
from gwdatalens.app.src.components import (
    ids,
    qc_chart,
    qc_dropdowns,
    qc_rules_form,
    qc_traval_buttons,
)
from gwdatalens.app.src.data.data_manager import DataManager
from gwdatalens.app.src.services import WellService


def render() -> dcc.Tab:
    """Renders a Dash Tab component for the QC tab.

    Returns
    -------
    dcc.Tab
        Qc tab for running error detection on time series.
    """
    return dcc.Tab(
        label=t_("general.tab_qc"),
        value=ids.TAB_QC,
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
        The data object containing the database connection and methods.
    selected_data : list or None
        A list containing internal ids of the selected data. Expected to
        contain a single int. If None or the list length is not 1, the
        date picker will be disabled.

    Returns
    -------
    dcc.DatePickerSingle
        A Dash DatePickerSingle with the start date.
    """
    if selected_data is not None and len(selected_data) == 1:
        wid = selected_data[0]
        ts = data.db.get_timeseries(wid)
        start_date = ts.index[0].to_pydatetime()
        disabled = False
    else:
        start_date = None
        disabled = True

    return dcc.DatePickerSingle(
        date=start_date,
        placeholder=t_("general.tmin"),
        display_format="YYYY-MM-DD",
        show_outside_days=True,
        number_of_months_shown=1,
        day_size=30,
        disabled=disabled,
        id=ids.QC_DATEPICKER_TMIN,
        style={"fontSize": 8},
    )


def render_datepicker_tmax(
    data: DataManager, selected_data: Optional[List[int]]
) -> dcc.DatePickerSingle:
    """Renders a DatePickerSingle component for selecting the maximum date (tmax).

    Parameters
    ----------
    data : object
        The data object containing the database connection and methods.
    selected_data : list or None
        A list containing the selected data. Expected to contain a single string
        in the format "gmw_id-tube_id". If None or the list length is not 1, the
        date picker will be disabled.

    Returns
    -------
    dcc.DatePickerSingle
        A Dash DatePickerSingle with the end date.
    """
    if selected_data is not None and len(selected_data) == 1:
        wid = selected_data[0]
        ts = data.db.get_timeseries(wid)
        end_date = ts.index[-1].to_pydatetime()
        disabled = False
    else:
        end_date = None
        disabled = True

    return dcc.DatePickerSingle(
        date=end_date,
        placeholder=t_("general.tmax"),
        display_format="YYYY-MM-DD",
        show_outside_days=True,
        number_of_months_shown=1,
        day_size=20,
        disabled=disabled,
        id=ids.QC_DATEPICKER_TMAX,
        style={"fontSize": 8},
    )


def render_checkbox() -> dbc.Checkbox:
    """Renders a checkbox component for running error detection on a subset of obs.

    Returns
    -------
    dbc.Checkbox
        A Dash Bootstrap Component (dbc) Checkbox for running error detection
        on all observations or only on unvalidated observations.
    """
    return dbc.Checkbox(
        id=ids.QC_RUN_ONLY_UNVALIDATED_CHECKBOX,
        label=t_("general.run_only_on_unvalidated"),
        value=True,
    )


def render_content(data: DataManager, selected_data: List[int]) -> dbc.Container:
    """Renders the content for the QC tab.

    Parameters
    ----------
    data : DataInterface
        The data interface object.
    selected_data : List
        A list of ids of selected data items.

    Returns
    -------
    dbc.Container
        A Dash Bootstrap Components container with the rendered content.
    """
    well_service = WellService(data.db)
    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            qc_dropdowns.render_selection_series_dropdown(
                                data, selected_data
                            )
                        ],
                        width=4,
                    ),
                    dbc.Col(
                        [
                            qc_dropdowns.render_additional_series_dropdown(
                                data, selected_data
                            )
                        ],
                        width=4,
                    ),
                ],
                style={"flex": "0 0 auto"},
            ),
            dbc.Row(
                [
                    dbc.Col([qc_chart.render()], width=12),
                ],
                style={"flex": "0 0 auto"},
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Button(
                            [
                                html.I(className="fa-solid fa-chevron-right"),
                                " " + t_("general.show_parameters"),
                            ],
                            style={
                                "backgroundcolor": UI.DEFAULT_BUTTON_COLOR,
                                "margin-top": UI.MARGIN_TOP,
                                "margin-bottom": UI.MARGIN_BOTTOM,
                            },
                            id=ids.QC_COLLAPSE_BUTTON,
                            n_clicks=0,
                        ),
                        width="auto",
                    ),
                    dbc.Col(
                        [qc_traval_buttons.render_run_traval_button()], width="auto"
                    ),
                    # dbc.Col(
                    #     [qc_traval_buttons.render_qc_cancel_button()], width="auto"
                    # ),
                    dbc.Col(
                        [render_datepicker_tmin(data, selected_data)], width="auto"
                    ),
                    dbc.Col(
                        [render_datepicker_tmax(data, selected_data)], width="auto"
                    ),
                    dbc.Col([render_checkbox()], width="auto"),
                ],
                style={"flex": "0 0 auto"},
                className="align-items-center",
            ),
            dbc.Collapse(
                dbc.Row(
                    id=ids.TRAVAL_FORM_ROW,
                    children=[
                        qc_rules_form.render_traval_form(
                            data, well_service=well_service
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [qc_dropdowns.render_add_rule_dropdown()], width="4"
                                ),
                                dbc.Col(
                                    [qc_traval_buttons.render_add_rule_button()],
                                    width="auto",
                                ),
                            ],
                            className="align-items-center",
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [qc_traval_buttons.render_reset_rules_button()],
                                    width="auto",
                                ),
                                dbc.Col(
                                    [qc_traval_buttons.render_load_ruleset_button()],
                                    width="auto",
                                ),
                                dbc.Col(
                                    [qc_traval_buttons.render_export_ruleset_button()],
                                    width="auto",
                                ),
                                dbc.Col(
                                    [
                                        qc_traval_buttons.render_export_parameter_csv_button()
                                    ],
                                    width="auto",
                                ),
                            ]
                        ),
                    ],
                ),
                is_open=False,
                id=ids.QC_COLLAPSE_CONTENT,
            ),
            dcc.Store(id=ids.QC_DROPDOWN_ADDITIONAL_DISABLED_1),
            dcc.Store(id=ids.QC_DROPDOWN_ADDITIONAL_DISABLED_2),
            dcc.Store(id=ids.TRAVAL_RULES_FORM_STORE_1, data=[]),
            dcc.Store(id=ids.TRAVAL_RULES_FORM_STORE_2, data=[]),
            dcc.Store(id=ids.TRAVAL_RULES_FORM_STORE_3, data=[]),
            dcc.Store(id=ids.TRAVAL_RULES_FORM_STORE_4, data=[]),
            dcc.Store(id=ids.TRAVAL_RESET_RULESET_BUTTON_STORE_1),
            dcc.Store(id=ids.TRAVAL_RESET_RULESET_BUTTON_STORE_2),
            dcc.Store(id=ids.TRAVAL_RESET_RULESET_BUTTON_STORE_3),
            dcc.Store(id=ids.LOADING_QC_CHART_STORE_1),
            dcc.Store(id=ids.LOADING_QC_CHART_STORE_2),
            dcc.Store(id=ids.QC_CHART_STORE_1),
            dcc.Store(id=ids.QC_CHART_STORE_2),
        ],
        fluid=True,
    )
