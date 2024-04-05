import dash_bootstrap_components as dbc
import i18n
from dash import dcc, html

from ..data.source import DataInterface
from . import ids, qc_results_table


def render():
    return dcc.Tab(
        label=i18n.t("general.tab_qc_result"),
        value=ids.TAB_QC_RESULT,
        className="custom-tab",
        selected_className="custom-tab--selected",
    )


def render_export_to_csv_button():
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
                disabled=True,
                id=ids.QC_RESULT_EXPORT_CSV,
            ),
            dcc.Download(id=ids.DOWNLOAD_EXPORT_CSV),
        ]
    )


def render_export_to_database_button():
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
            disabled=True,
            id=ids.QC_RESULT_EXPORT_DB,
        ),
    )


def render_mark_selection_reliable_button():
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


def render_mark_selection_suspect_button():
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
            id={"type": ids.QC_RESULT_MARK_OBS_BUTTONS, "index": "suspect"},
        ),
    )


def render_reset_qualifier_button():
    return html.Div(
        dbc.Button(
            html.Span(
                [
                    html.I(className="fa-solid fa-delete-left"),
                    " " + i18n.t("general.reset_status"),
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


def render_clear_table_selection_button():
    return html.Div(
        dbc.Button(
            html.Span(
                [
                    html.I(className="fa-solid fa-ban"),
                    " " + i18n.t("general.clear_selection"),
                ],
                id="span-export-db",
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


def render_qc_chart():
    return html.Div(
        id="series-chart-div",
        children=[
            dcc.Loading(
                # TODO: on new release dash, use delay_show option to hide loading
                # on short updates. See https://github.com/plotly/dash/pull/2760
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
                        style={
                            "height": "40vh",
                            # "margin-bottom": "10px",
                            # "margin-top": 5,
                        },
                    ),
                ],
            ),
        ],
        style={
            "position": "relative",
            "justify-content": "center",
            "margin-bottom": 10,
        },
    )


def render_content(data: DataInterface):
    return dbc.Container(
        [
            dbc.Row([render_qc_chart()]),
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
                    dbc.Col([render_clear_table_selection_button()], width="auto"),
                    dbc.Col([render_mark_selection_suspect_button()], width="auto"),
                    dbc.Col([render_mark_selection_reliable_button()], width="auto"),
                    dbc.Col([render_reset_qualifier_button()], width="auto"),
                ],
            ),
            dbc.Row([qc_results_table.render(data)]),
            dbc.Row(
                [
                    dbc.Col([render_export_to_csv_button()], width="auto"),
                    dbc.Col([render_export_to_database_button()], width="auto"),
                ]
            ),
        ],
        fluid=True,
    )
