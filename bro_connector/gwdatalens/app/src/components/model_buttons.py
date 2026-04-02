from dash import html
from dash_bootstrap_components import Button

from gwdatalens.app.constants import UI
from gwdatalens.app.messages import t_
from gwdatalens.app.src.components import ids


def render_generate_button() -> html.Div:
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
                    " " + t_("general.generate"),
                ],
                id="span-recalculate",
                n_clicks=0,
            ),
            style={
                "margin-top": UI.MARGIN_TOP,
                "margin-bottom": UI.MARGIN_BOTTOM,
            },
            disabled=False,
            id=ids.MODEL_GENERATE_BUTTON,
        ),
    )


def render_save_button() -> html.Div:
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
                    " " + t_("general.save"),
                ],
                id="span-recalculate",
                n_clicks=0,
            ),
            style={
                "margin-top": UI.MARGIN_TOP,
                "margin-bottom": UI.MARGIN_BOTTOM,
            },
            disabled=True,
            id=ids.MODEL_SAVE_BUTTON,
        ),
    )
