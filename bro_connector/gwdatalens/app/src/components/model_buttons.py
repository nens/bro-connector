import i18n
from dash import html
from dash_bootstrap_components import Button

from . import ids


def render_generate_button():
    """Renders a button for generating time series models.

    Returns
    -------
    html.Div
        A Div containing the generate model button.
    """
    return html.Div(
        Button(
            html.Span(
                [
                    html.I(className="fa-solid fa-gear"),
                    " " + i18n.t("general.generate"),
                ],
                id="span-recalculate",
                n_clicks=0,
            ),
            style={
                "margin-top": 10,
                "margin-bottom": 10,
            },
            disabled=False,
            id=ids.MODEL_GENERATE_BUTTON,
        ),
    )


def render_save_button():
    """Renders a save model button component.

    Returns
    -------
    div
        A Div containing the model save button.
    """
    return html.Div(
        Button(
            html.Span(
                [
                    html.I(className="fa-solid fa-floppy-disk"),
                    " " + i18n.t("general.save"),
                ],
                id="span-recalculate",
                n_clicks=0,
            ),
            style={
                "margin-top": 10,
                "margin-bottom": 10,
            },
            disabled=True,
            id=ids.MODEL_SAVE_BUTTON,
        ),
    )
