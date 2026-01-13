import dash_bootstrap_components as dbc
from dash import __version__ as DASH_VERSION
from dash import dcc, html
from packaging.version import parse as parse_version

from gwdatalens.app.constants import UI
from gwdatalens.app.messages import ErrorMessages, t_
from gwdatalens.app.src.components import ids, qc_results_table
from gwdatalens.app.src.data.data_manager import DataManager
from gwdatalens.app.src.data.qc_definitions import qc_categories
from gwdatalens.app.src.utils.callback_helpers import EmptyFigure


def render() -> dcc.Tab:
    """Renders a Dash Tab component for QC results.

    Returns
    -------
    dccc.Tab
        QC results tab.
    """
    return dcc.Tab(
        label=t_("general.tab_qc_result"),
        value=ids.TAB_QC_RESULT,
        className="custom-tab",
        selected_className="custom-tab--selected",
    )


def render_export_to_csv_button(disabled: bool = True) -> html.Div:
    """Renders a button for exporting QC results to CSV.

    Parameters
    ----------
    disabled : bool, optional
        A flag indicating whether the button should be disabled, by default True.

    Returns
    -------
    html.Div
        A Dash HTML Div component containing the export to CSV button and a
        download component.
    """
    return html.Div(
        [
            dbc.Button(
                html.Span(
                    [
                        html.I(className="fa-solid fa-file-csv"),
                        " " + t_("general.export_csv"),
                    ],
                    id="span-export-csv",
                    n_clicks=0,
                ),
                style={
                    "margin-top": UI.MARGIN_TOP,
                    "margin-bottom": UI.MARGIN_BOTTOM,
                },
                disabled=disabled,
                id=ids.QC_RESULT_EXPORT_CSV,
            ),
            dcc.Download(id=ids.DOWNLOAD_EXPORT_CSV),
        ]
    )


def render_export_to_database_button(disabled: bool = True) -> html.Div:
    """Renders a button for exporting data to the Zeeland postgresql database.

    Parameters
    ----------
    disabled : bool, optional
        If True, the button will be disabled. Default is True.

    Returns
    -------
    html.Div
        A Dash HTML component containing the export button.
    """
    return html.Div(
        dbc.Button(
            html.Span(
                [
                    html.I(className="fa-solid fa-database"),
                    " " + t_("general.export_db"),
                ],
                id="span-export-db",
                n_clicks=0,
            ),
            style={
                "margin-top": UI.MARGIN_TOP,
                "margin-bottom": UI.MARGIN_BOTTOM,
            },
            disabled=disabled,
            id=ids.QC_RESULT_EXPORT_DB,
        ),
    )


def render_mark_selection_reliable_button():
    """Renders a button for marking table selections as reliable.

    Returns
    -------
    html.Div
        A Dash HTML Div containing the button.
    """
    return html.Div(
        dbc.Button(
            html.Span(
                [
                    html.I(className="fa-solid fa-check"),
                    " " + t_("general.mark_reliable"),
                ],
                id="span-export-db",
                n_clicks=0,
            ),
            style={
                "margin-top": UI.MARGIN_TOP,
                "margin-bottom": UI.MARGIN_BOTTOM,
            },
            disabled=True,
            id={"type": ids.QC_RESULT_MARK_OBS_BUTTONS, "index": "reliable"},
        ),
    )


def render_mark_selection_unreliable_button():
    """Renders a button for marking table selections as unreliable.

    Returns
    -------
    html.Div
        A Dash HTML Div containing the button.
    """
    return html.Div(
        dbc.Button(
            html.Span(
                [
                    html.I(className="fa-solid fa-xmark"),
                    " " + t_("general.mark_unreliable"),
                ],
                id="span-export-db",
                n_clicks=0,
            ),
            style={
                "margin-top": UI.MARGIN_TOP,
                "margin-bottom": UI.MARGIN_BOTTOM,
            },
            disabled=True,
            id={"type": ids.QC_RESULT_MARK_OBS_BUTTONS, "index": "unreliable"},
        ),
    )


def render_mark_selection_unknown_button():
    """Renders a button for marking table selections as unknown (reset).

    Returns
    -------
    html.Div
        A Dash HTML Div containing the button.
    """
    return html.Div(
        dbc.Button(
            html.Span(
                [
                    html.I(className="fa-solid fa-delete-left"),
                    " " + t_("general.mark_unknown"),
                ],
                id="span-export-db",
                n_clicks=0,
            ),
            style={
                "margin-top": UI.MARGIN_TOP,
                "margin-bottom": UI.MARGIN_BOTTOM,
            },
            disabled=True,
            id={"type": ids.QC_RESULT_MARK_OBS_BUTTONS, "index": "unknown"},
        ),
    )


def render_mark_selection_undecided_button():
    """Renders a button for marking table selections as undecided.

    Returns
    -------
    html.Div
        A Dash HTML Div containing the button.
    """
    return html.Div(
        dbc.Button(
            html.Span(
                [
                    html.I(className="fa-regular fa-circle-question"),
                    " " + t_("general.mark_undecided"),
                ],
                id="span-export-db",
                n_clicks=0,
            ),
            style={
                "margin-top": UI.MARGIN_TOP,
                "margin-bottom": UI.MARGIN_BOTTOM,
            },
            disabled=True,
            id={"type": ids.QC_RESULT_MARK_OBS_BUTTONS, "index": "undecided"},
        ),
    )


def render_clear_table_selection_button():
    """Renders a button for clearing table selection.

    Returns
    -------
    html.Div
        A Dash HTML Div containing the button.
    """
    return html.Div(
        dbc.Button(
            html.Span(
                [
                    html.I(className="fa-solid fa-ban"),
                    " " + t_("general.clear_selection_table"),
                ],
                id="span-deselect-all",
                n_clicks=0,
            ),
            style={
                "margin-top": UI.MARGIN_TOP,
                "margin-bottom": UI.MARGIN_BOTTOM,
            },
            disabled=True,
            id=ids.QC_RESULT_CLEAR_TABLE_SELECTION,
        ),
    )


def render_select_all_in_table_button():
    """Renders a button for selecting all rows in table.

    Returns
    -------
    html.Div
        A Dash HTML Div containing the button.
    """
    return html.Div(
        dbc.Button(
            html.Span(
                [
                    html.I(className="fa-solid fa-check-double"),
                    " " + t_("general.select_all"),
                ],
                id="span-select-all",
                n_clicks=0,
            ),
            style={
                "margin-top": UI.MARGIN_TOP,
                "margin-bottom": UI.MARGIN_BOTTOM,
            },
            disabled=False,
            id=ids.QC_RESULT_TABLE_SELECT_ALL,
        ),
    )


def render_qc_chart(figure: dict):
    """Render a QC chart.

    Parameters
    ----------
    figure : dict
        A dictionary containing the figure data and layout for the QC chart.
        If None, a default empty figure will be shown.

    Returns
    -------
    html.Div
        A Dash HTML Div component containing the QC result chart
    """
    if figure is None:
        figure = EmptyFigure.with_message(t_(ErrorMessages.NO_QC_RESULT))
    else:
        figure["layout"]["dragmode"] = "select"

    kwargs = (
        {"delay_show": 500}
        if parse_version(DASH_VERSION) >= parse_version("2.17.0")
        else {}
    )

    return html.Div(
        id="series-chart-div",
        children=[
            dcc.Loading(
                id=ids.LOADING_QC_CHART,
                type="dot",
                style={"position": "absolute", "align-self": "center"},
                parent_className="loading-wrapper-qc-result",
                children=[
                    dcc.Graph(
                        id=ids.QC_RESULT_CHART,
                        config={
                            "displayModeBar": True,
                            "scrollZoom": True,
                        },
                        figure=figure,
                        style={
                            "height": "40cqh",
                        },
                    ),
                ],
                **kwargs,
            ),
        ],
        style={
            "position": "relative",
            "justify-content": "center",
            "margin-bottom": UI.MARGIN_BOTTOM,
        },
    )


def render_qc_label_dropdown():
    """Renders a dropdown component for selecting QC labels.

    Returns
    -------
    dcc.Dropdown
        A Dash `Dropdown` component with QC label options.
    """
    options = [
        {
            "label": v + f" ({k})",
            "value": v + f"({k})",
            "search": v + f" {k}",
        }
        for k, v in qc_categories.items()
    ]
    options = [
        {
            "label": t_("general.clear_qc_label"),
            "value": "",
            "search": t_("general.clear_qc_label"),
        }
    ] + options
    return dcc.Dropdown(
        id=ids.QC_RESULT_LABEL_DROPDOWN,
        placeholder=t_("general.select_qc_label"),
        options=options,
        disabled=True,
        value=None,
        multi=False,
        searchable=True,
        clearable=False,
    )


def render_export_dropdown_and_tooltip(disabled=True):
    """Renders a dropdown component for exporting QC status flags.

    Returns
    -------
    list
        A list containing a Dash Dropdown, help icon with Tooltip components.

    Dropdown Options
    ----------------
    - "suspect": Mark suspect observations with their incoming status
    - "all_not_suspect": Mark all non-suspect observations as approved
    - "all": Mark all observations (overwrite existing status)
    """
    return [
        html.Div(
            [
                dcc.Dropdown(
                    id=ids.QC_RESULT_EXPORT_QC_STATUS_FLAG,
                    options=[
                        {
                            "label": t_("general.qc_export_status_flag_suspect"),
                            "value": "suspect",
                        },
                        {
                            "label": t_(
                                "general.qc_export_status_flag_all_not_suspect"
                            ),
                            "value": "all_not_suspect",
                        },
                        {
                            "label": t_("general.qc_export_status_flag_all"),
                            "value": "all",
                        },
                    ],
                    value=None,
                    multi=False,
                    searchable=False,
                    clearable=False,
                    placeholder=t_("general.qc_export_status_flag_placeholder"),
                    disabled=disabled,
                    style={"flex": "1"},
                    maxHeight=200,
                    className="dropUp",
                ),
                dbc.Button(
                    html.Span(
                        [html.I(className="fa-solid fa-question")],
                        id="span-info-button2",
                        n_clicks=0,
                    ),
                    style={
                        "fontSize": "small",
                        "background-color": UI.DEFAULT_BUTTON_COLOR,
                        # "padding": 1,
                        "height": "30px",
                        "width": "30px",
                        # "border": None,
                        "border-radius": "50%",
                        "padding": 0,
                        "textAlign": "center",
                        "display": "block",
                    },
                    id=ids.QC_RESULT_EXPORT_QC_STATUS_FLAG + "_help",
                ),
            ],
            style={
                "display": "flex",
                "alignItems": "center",
                "gap": "10px",
                "width": "100%",
            },
        ),
        dbc.Tooltip(
            html.Div(
                [
                    html.P(
                        html.Strong(t_("general.qc_export_status_flag_suspect")),
                        style={"marginBottom": "8px"},
                    ),
                    html.P(
                        t_("general.qc_export_status_flag_suspect_tooltip"),
                        style={"marginBottom": "12px"},
                    ),
                    html.P(
                        html.Strong(
                            t_("general.qc_export_status_flag_all_not_suspect")
                        ),
                        style={"marginBottom": "8px"},
                    ),
                    html.P(
                        t_("general.qc_export_status_flag_all_not_suspect_tooltip"),
                        style={"marginBottom": "12px"},
                    ),
                    html.P(
                        html.Strong(t_("general.qc_export_status_flag_all")),
                        style={"marginBottom": "8px"},
                    ),
                    html.P(
                        t_("general.qc_export_status_flag_all_tooltip"),
                        style={"marginBottom": "0px"},
                    ),
                ],
                style={"textAlign": "left"},
            ),
            id=ids.QC_RESULT_EXPORT_QC_STATUS_FLAG + "_tooltip",
            target=ids.QC_RESULT_EXPORT_QC_STATUS_FLAG + "_help",
            placement="right",
            className="wide-tooltip",
        ),
    ]


def render_content(data: DataManager, figure: dict):
    """Renders the content for the QC results tab.

    Parameters
    ----------
    data : DataInterface
        The data interface containing the necessary data for rendering.
    figure : dict
        The figure dictionary to be used for rendering the QC chart.

    Returns
    -------
    dbc.Container
        A Dash Bootstrap Container with the rendered content.
    """
    disabled_csv = figure is None
    disabled_db = figure is None or data.db.backend == "hydropandas"
    return dbc.Container(
        [
            dbc.Row([render_qc_chart(figure)]),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Switch(
                                label=t_("general.show_all"),
                                value=False,
                                disabled=data.qc.traval_result is None,
                                id=ids.QC_RESULTS_SHOW_ALL_OBS_SWITCH,
                                style={"margin-left": "10px"},
                            ),
                            dbc.Tooltip(
                                html.P(
                                    t_("general.show_all_tooltip"),
                                    style={
                                        "margin-top": UI.MARGIN_ZERO,
                                        "margin-bottom": UI.MARGIN_ZERO,
                                    },
                                ),
                                target=ids.QC_RESULTS_SHOW_ALL_OBS_SWITCH,
                                placement="top",
                            ),
                        ],
                        width="auto",
                    ),
                    dbc.Col([render_select_all_in_table_button()], width="auto"),
                    dbc.Col([render_clear_table_selection_button()], width="auto"),
                    dbc.Col(
                        [
                            html.Div(
                                className="col-right-border", style={"height": "60px"}
                            )
                        ],
                        width="auto",
                        style={"min-width": "15px"},
                    ),
                    dbc.Col([render_mark_selection_reliable_button()], width="auto"),
                    dbc.Col([render_mark_selection_unreliable_button()], width="auto"),
                    dbc.Col([render_mark_selection_undecided_button()], width="auto"),
                    dbc.Col([render_mark_selection_unknown_button()], width="auto"),
                    dbc.Col(
                        [
                            html.Div(
                                className="col-right-border", style={"height": "60px"}
                            )
                        ],
                        width="auto",
                        style={"min-width": "15px"},
                    ),
                    dbc.Col([render_qc_label_dropdown()], width=2),
                ],
                className="align-items-center",
            ),
            dbc.Row([qc_results_table.render(data)]),
            dbc.Row(
                [
                    dbc.Col([render_export_to_csv_button(disabled_csv)], width="auto"),
                    dbc.Col(
                        [render_export_to_database_button(disabled_db)], width="auto"
                    ),
                    dbc.Col(render_export_dropdown_and_tooltip(disabled_db), width=3),
                ],
                className="align-items-center",
            ),
            dcc.Store(id=ids.QC_RESULT_TABLE_STORE_1),
            dcc.Store(id=ids.QC_RESULT_TABLE_STORE_2),
            dcc.Store(id=ids.QC_RESULT_TABLE_STORE_3),
        ],
        fluid=True,
    )
