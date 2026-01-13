import logging
from typing import Any

import dash_bootstrap_components as dbc
from dash import Input, Output, State, html
from dash.exceptions import PreventUpdate

from gwdatalens.app.constants import ConfigDefaults
from gwdatalens.app.messages import t_
from gwdatalens.app.src.components import (
    ids,
    tab_corrections,
    tab_model,
    tab_overview,
    tab_qc,
    tab_qc_result,
)
from gwdatalens.app.src.utils import log_callback
from gwdatalens.app.src.utils.callback_helpers import (
    AlertBuilder,
    get_callback_context,
)
from gwdatalens.app.validators import validate_selection_limit

logger = logging.getLogger(__name__)


def register_general_callbacks(app, data):
    @app.callback(
        Output(ids.HELP_MODAL, "is_open"),
        Input(ids.HELP_BUTTON_OPEN, "n_clicks"),
        Input(ids.HELP_BUTTON_CLOSE, "n_clicks"),
        State(ids.HELP_MODAL, "is_open"),
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def toggle_modal(n1: int | None, n2: int | None, is_open: bool) -> bool:
        """Toggle help modal window.

        Parameters
        ----------
        n1 : int
            button open help n_clicks
        n2 : int
            button close help n_clicks
        is_open : bool
            remember state of modal

        Returns
        -------
        bool
            whether window is open or closed
        """
        if n1 or n2:
            return not is_open
        return is_open

    @app.callback(
        Output(ids.TAB_CONTENT, "children"),
        Output(ids.ALERT_TAB_RENDER, "data"),
        Input(ids.TAB_CONTAINER, "value"),
        State(ids.SELECTED_OSERIES_STORE, "data"),
        State(ids.TRAVAL_RESULT_FIGURE_STORE, "data"),
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def render_tab_content(
        tab: str, selected_data: list[int] | None, figure: tuple | None
    ) -> tuple[Any, tuple]:
        """Render tab content with appropriate alerts for selection limits.

        Parameters
        ----------
        tab : str
            Tab identifier (e.g., "overview", "model", "qc")
        selected_data : list or None
            List of selected observation series IDs
        figure : tuple or None
            Stored Traval result figure data

        Returns
        -------
        tuple
            (tab_content, alert_data)
        """
        # Check selection limit and handle oversized selections
        if selected_data is not None and validate_selection_limit(
            selected_data, ConfigDefaults.MAX_WELLS_SELECTION
        ):
            # For model tab, show warning but keep selection
            if tab == ids.TAB_MODEL:
                alert = AlertBuilder.warning(
                    t_("general.multiple_series_model_warning")
                )
                return tab_model.render_content(data, selected_data), alert
            # For overview tab, clear selection to avoid performance issues
            elif tab == ids.TAB_OVERVIEW:
                alert = AlertBuilder.warning(
                    f"Selection limited to {ConfigDefaults.MAX_WELLS_SELECTION} "
                    "wells for performance"
                )
                return tab_overview.render_content(data, None), alert

        # No alert for most tabs
        no_alert = AlertBuilder.no_alert()

        if tab == ids.TAB_OVERVIEW:
            return tab_overview.render_content(data, selected_data), no_alert
        elif tab == ids.TAB_MODEL:
            return tab_model.render_content(data, selected_data), no_alert
        elif tab == ids.TAB_QC:
            return tab_qc.render_content(data, selected_data), no_alert
        elif tab == ids.TAB_QC_RESULT:
            figure_data = figure[1] if figure is not None else None
            return tab_qc_result.render_content(data, figure_data), no_alert
        elif tab == ids.TAB_CORRECTIONS:
            return tab_corrections.render_content(data, selected_data), no_alert
        else:
            raise PreventUpdate

    @app.callback(
        Output(ids.ALERT_DIV, "children"),
        Input(ids.ALERT_TIME_SERIES_CHART, "data"),
        Input(ids.ALERT_DISPLAY_RULES_FOR_SERIES, "data"),
        Input(ids.ALERT_GENERATE_MODEL, "data"),
        Input(ids.ALERT_SAVE_MODEL, "data"),
        Input(ids.ALERT_PLOT_MODEL_RESULTS, "data"),
        Input(ids.ALERT_LOAD_RULESET, "data"),
        Input(ids.ALERT_EXPORT_TO_DB, "data"),
        Input(ids.ALERT_MARK_OBS, "data"),
        Input(ids.ALERT_LABEL_OBS, "data"),
        Input(ids.ALERT_RUN_TRAVAL, "data"),
        Input(ids.ALERT_TAB_RENDER, "data"),
        Input(ids.ALERT_STATUS_CORRECTIONS, "data"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def show_alert(*args: tuple, **kwargs: Any) -> list[dbc.Alert]:
        """Display alert message from any alert input.

        Uses context helper to work in both standalone and Django modes.
        """
        # Get callback context (works for both Dash and Django)
        ctx_obj = get_callback_context(**kwargs)
        triggered_id = ctx_obj.triggered_id
        inputs_list = ctx_obj.inputs_list

        if not any(args):
            raise PreventUpdate

        # Find which input triggered this callback
        for i, input_item in enumerate(inputs_list):
            if input_item["id"] == triggered_id:
                alert_data = args[i]
                break
        else:
            raise PreventUpdate

        # Unpack alert data
        is_open, color, message = alert_data

        # Log warnings and errors
        if is_open and color in ["danger", "warning"]:
            logger.warning("Alert triggered by %s: %s", triggered_id, message)

        return [
            dbc.Alert(
                children=[html.P(message, id=ids.ALERT_BODY)],
                id=ids.ALERT,
                color=color,
                dismissable=True,
                duration=4000,
                fade=True,
                is_open=is_open,
            ),
        ]
