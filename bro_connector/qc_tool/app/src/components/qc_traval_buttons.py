import i18n
from dash import dcc, html
from dash_bootstrap_components import Button

from . import ids


def render_run_traval_button():
    return html.Div(
        Button(
            html.Span(
                [
                    html.I(className="fa-solid fa-gear"),
                    " Run TRAVAL",
                ],
                id="span-recalculate",
                n_clicks=0,
            ),
            style={
                "margin-top": 10,
                "margin-bottom": 10,
            },
            disabled=False,
            id=ids.QC_RUN_TRAVAL_BUTTON,
        ),
    )


def render_qc_cancel_button():
    return html.Div(
        children=[
            Button(
                html.Span(
                    [
                        html.I(className="fa-regular fa-circle-stop"),
                        " " + i18n.t("general.cancel"),
                    ],
                    id="span-cancel-button",
                    n_clicks=0,
                ),
                style={
                    "margin-top": 10,
                    "margin-bottom": 10,
                },
                disabled=True,
                id=ids.QC_CANCEL_BUTTON,
            ),
        ]
    )


def render_add_rule_button():
    return html.Div(
        Button(
            html.Span(
                [
                    html.I(className="fa-solid fa-plus"),
                    i18n.t("general.add_rule_button"),
                ],
                id="span-add-rule",
                n_clicks=0,
            ),
            style={
                "margin-top": 10,
                "margin-bottom": 10,
            },
            disabled=True,
            id=ids.TRAVAL_ADD_RULE_BUTTON,
        ),
    )


def render_reset_rules_button():
    return html.Div(
        Button(
            html.Span(
                [
                    html.I(className="fa-solid fa-arrows-rotate"),
                    " Reset",
                ],
                id="span-reset-rules",
                n_clicks=0,
            ),
            style={
                "margin-top": 10,
                "margin-bottom": 10,
            },
            disabled=True,
            id=ids.TRAVAL_RESET_RULESET_BUTTON,
        ),
    )


def render_export_ruleset_button():
    return html.Div(
        [
            Button(
                html.Span(
                    [
                        html.I(className="fa-solid fa-file-export"),
                        " " + i18n.t("general.export"),
                    ],
                    id="span-ruleset-export",
                    n_clicks=0,
                ),
                style={
                    "margin-top": 10,
                    "margin-bottom": 10,
                },
                disabled=False,
                id=ids.TRAVAL_EXPORT_RULESET_BUTTON,
            ),
            dcc.Download(id=ids.DOWNLOAD_TRAVAL_RULESET),
        ]
    )


def render_export_parameter_csv_button():
    return html.Div(
        [
            Button(
                html.Span(
                    [
                        html.I(className="fa-solid fa-file-csv"),
                        " " + i18n.t("general.export_params"),
                    ],
                    id="span-parameters-export",
                    n_clicks=0,
                ),
                style={
                    "margin-top": 10,
                    "margin-bottom": 10,
                },
                disabled=False,
                id=ids.TRAVAL_EXPORT_PARAMETERS_CSV_BUTTON,
            ),
            dcc.Download(id=ids.DOWNLOAD_TRAVAL_PARAMETERS_CSV),
        ]
    )


def render_load_ruleset_button():
    return html.Div(
        children=[
            # NOTE: Upload component does not trigger callback if same file is selected.
            # Solution (i.e. workaround) is to create a new Upload component once it's
            # been used.
            dcc.Upload(
                id=ids.TRAVAL_LOAD_RULESET_BUTTON,
                # accept=[
                #     ".pickle",
                #     ".pkl",
                # ],  # Only works in production mode, not in debug mode
                children=[
                    html.P(
                        html.Span(
                            [
                                html.I(className="fa-solid fa-file-import"),
                                f" {i18n.t('general.load')} RuleSet",
                            ],
                            style={
                                "color": "white",
                            },
                        )
                    )
                ],
                style={
                    "width": "110px",
                    "height": "33px",
                    "lineHeight": "31.5px",
                    "borderWidth": "1px",
                    "borderStyle": "solid",
                    "borderRadius": "3px",
                    "backgroundClip": "border-box",
                    "backgroundColor": "#2c3e50",  # "#006f92",
                    "textAlign": "center",
                },
            )
        ],
        style={
            "display": "inline-block",
            "margin-top": 5,
            "margin-bottom": 5,
            "margin-right": 5,
            "verticalAlign": "middle",
        },
    )