import dash_bootstrap_components as dbc
import i18n
from dash import __version__ as DASH_VERSION
from dash import dcc, html
from packaging.version import parse as parse_version

from ..data.interface import DataInterface
from ..data.qc_definitions import qc_categories
from . import ids, qc_results_table


def render():
    """Renders a Dash Tab component for QC results.

    Returns
    -------
    dccc.Tab
        QC results tab.
    """
    return dcc.Tab(
        label=i18n.t("general.tab_qc_result"),
        value=ids.TAB_QC_RESULT,
        className="custom-tab",
        selected_className="custom-tab--selected",
    )


def render_export_to_csv_button(disabled=True):
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
                        " " + i18n.t("general.export_csv"),
                    ],
                    id="span-export-csv",
                    n_clicks=0,
                ),
                style={
                    "margin-top": 10,
                    "margin-bottom": 10,
                },
                disabled=disabled,
                id=ids.QC_RESULT_EXPORT_CSV,
            ),
            dcc.Download(id=ids.DOWNLOAD_EXPORT_CSV),
        ]
    )


def render_export_to_database_button(disabled=True):
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
                    " " + i18n.t("general.export_db"),
                ],
                id="span-export-db",
                n_clicks=0,
            ),
            style={
                "margin-top": 10,
                "margin-bottom": 10,
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
                    " " + i18n.t("general.mark_reliable"),
                ],
                id="span-export-db",
                n_clicks=0,
            ),
            style={
                "margin-top": 10,
                "margin-bottom": 10,
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
                    " " + i18n.t("general.mark_unreliable"),
                ],
                id="span-export-db",
                n_clicks=0,
            ),
            style={
                "margin-top": 10,
                "margin-bottom": 10,
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
                    " " + i18n.t("general.mark_unknown"),
                ],
                id="span-export-db",
                n_clicks=0,
            ),
            style={
                "margin-top": 10,
                "margin-bottom": 10,
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
                    " " + i18n.t("general.mark_undecided"),
                ],
                id="span-export-db",
                n_clicks=0,
            ),
            style={
                "margin-top": 10,
                "margin-bottom": 10,
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
                    " " + i18n.t("general.clear_selection"),
                ],
                id="span-deselect-all",
                n_clicks=0,
            ),
            style={
                "margin-top": 10,
                "margin-bottom": 10,
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
                    " " + i18n.t("general.select_all"),
                ],
                id="span-select-all",
                n_clicks=0,
            ),
            style={
                "margin-top": 10,
                "margin-bottom": 10,
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
        If None, a default layout with the title "No traval result." will be used.

    Returns
    -------
    html.Div
        A Dash HTML Div component containing the QC result chart
    """
    if figure is None:
        figure = {"layout": {"title": "No traval result."}}
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
                            "height": "40vh",
                            # "margin-bottom": "10px",
                            # "margin-top": 5,
                        },
                    ),
                ],
                **kwargs,
            ),
        ],
        style={
            "position": "relative",
            "justify-content": "center",
            "margin-bottom": 10,
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
        {"label": v + f" ({k})", "value": v + f"({k})"}
        for k, v in qc_categories.items()
    ]
    options = [{"label": i18n.t("general.clear_qc_label"), "value": ""}] + options
    return dcc.Dropdown(
        id=ids.QC_RESULT_LABEL_DROPDOWN,
        placeholder=i18n.t("general.select_qc_label"),
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
        A list containing a Dash Dropdown and Tooltip components.

    Dropdown Options
    ----------------
    - "suspect": Export QC status for suspect observations only.
    - "all_not_suspect": Export QC status for all observations that were not already
      marked as suspect.
    - "all": Export all QC status flags (overwriting the current status)
    """
    return [
        dcc.Dropdown(
            id=ids.QC_RESULT_EXPORT_QC_STATUS_FLAG,
            options=[
                {
                    "label": i18n.t("general.qc_export_status_flag_suspect"),
                    "value": "suspect",
                },
                {
                    "label": i18n.t("general.qc_export_status_flag_all_not_suspect"),
                    "value": "all_not_suspect",
                },
                {
                    "label": i18n.t("general.qc_export_status_flag_all"),
                    "value": "all",
                },
            ],
            value="suspect",
            multi=False,
            searchable=True,
            clearable=False,
            placeholder=i18n.t("general.qc_export_status_flag_placeholder"),
            disabled=disabled,
        ),
        dbc.Tooltip(
            i18n.t("general.qc_export_status_flag_tooltip"),
            id=ids.QC_RESULT_EXPORT_QC_STATUS_FLAG + "_tooltip",
            target=ids.QC_RESULT_EXPORT_QC_STATUS_FLAG,
        ),
    ]


def render_content(data: DataInterface, figure: dict):
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
                                label=i18n.t("general.show_all"),
                                value=False,
                                disabled=data.traval.traval_result is None,
                                id=ids.QC_RESULTS_SHOW_ALL_OBS_SWITCH,
                                style={"margin-left": "10px"},
                            ),
                            dbc.Tooltip(
                                html.P(
                                    i18n.t("general.show_all_tooltip"),
                                    style={"margin-top": 0, "margin-bottom": 0},
                                ),
                                target=ids.QC_RESULTS_SHOW_ALL_OBS_SWITCH,
                                placement="top",
                            ),
                        ],
                        width=True,
                    ),
                    dbc.Col([render_select_all_in_table_button()], width="auto"),
                    dbc.Col([render_clear_table_selection_button()], width="auto"),
                    dbc.Col([html.Div(className="col-right-border")], width="auto"),
                    dbc.Col([render_mark_selection_reliable_button()], width="auto"),
                    dbc.Col([render_mark_selection_unreliable_button()], width="auto"),
                    dbc.Col([render_mark_selection_undecided_button()], width="auto"),
                    dbc.Col([render_mark_selection_unknown_button()], width="auto"),
                    dbc.Col([html.Div(className="col-right-border")], width="auto"),
                    dbc.Col([render_qc_label_dropdown()], width=2),
                ],
            ),
            dbc.Row([qc_results_table.render(data)]),
            dbc.Row(
                [
                    dbc.Col([render_export_to_csv_button(disabled_csv)], width="auto"),
                    dbc.Col(
                        [render_export_to_database_button(disabled_db)], width="auto"
                    ),
                    dbc.Col(render_export_dropdown_and_tooltip(disabled_db), width=2),
                ]
            ),
        ],
        fluid=True,
    )
