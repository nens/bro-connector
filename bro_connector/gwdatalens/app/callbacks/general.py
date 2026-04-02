import base64
import binascii
import logging
import os
import tempfile
from typing import Any

import dash_bootstrap_components as dbc
import pastastore as pst
from dash import Input, Output, State, html, no_update
from dash.exceptions import PreventUpdate

from gwdatalens.app.constants import ConfigDefaults
from gwdatalens.app.messages import ErrorMessages, SuccessMessages, t_
from gwdatalens.app.src.components import (
    ids,
    tab_corrections,
    tab_model,
    tab_overview,
    tab_qc,
    tab_qc_result,
)
from gwdatalens.app.src.components.time_range_filter import build_time_range_store_value
from gwdatalens.app.src.utils import log_callback
from gwdatalens.app.src.utils.callback_helpers import (
    AlertBuilder,
    TimestampStore,
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
        Input(ids.PASTASTORE_REFRESH_STORE, "data"),
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
        tab: str,
        _pastastore_refresh: tuple | None,
        selected_data: list[int] | None,
        figure: tuple | None,
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
        Input(ids.ALERT_LOAD_PASTASTORE, "data"),
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

    @app.callback(
        Output(ids.ALERT_LOAD_PASTASTORE, "data"),
        Output(ids.PASTASTORE_REFRESH_STORE, "data"),
        Input(ids.LOAD_PASTASTORE_UPLOAD, "contents"),
        State(ids.LOAD_PASTASTORE_UPLOAD, "filename"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def load_pastastore_from_upload(
        contents: str | None,
        filename: str | None,
    ) -> tuple[tuple, tuple | Any]:
        """Load and activate a PastaStore from uploaded .pastastore or .zip."""
        if contents is None:
            raise PreventUpdate

        try:
            content_type, content_string = contents.split(",", maxsplit=1)
            decoded = base64.b64decode(content_string)

            is_zip = (filename or "").lower().endswith(
                ".zip"
            ) or "zip" in content_type.lower()
            suffix = ".zip" if is_zip else ".pastastore"

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                tmp_file.write(decoded)
                tmp_path = tmp_file.name

            try:
                if is_zip:
                    pstore = pst.PastaStore.from_zip(tmp_path)
                else:
                    pstore = pst.PastaStore.from_pastastore_config_file(
                        tmp_path,
                        update_path=False,
                    )
            finally:
                os.unlink(tmp_path)

            if getattr(data.db, "backend", None) == "pastastore":
                set_pastastore = getattr(data.db, "set_pastastore", None)
                if callable(set_pastastore):
                    set_pastastore(pstore)

            data.set_pastastore(pstore)
            source_name = filename or suffix
            logger.info("Loaded PastaStore from upload: %s", source_name)
            return (
                AlertBuilder.success(
                    t_(SuccessMessages.PASTASTORE_LOADED, source=source_name)
                ),
                TimestampStore.create(success=True),
            )
        except (binascii.Error, OSError, TypeError, ValueError, RuntimeError) as e:
            logger.warning(
                "Failed to load PastaStore from upload: %s", e, exc_info=True
            )
            return (
                AlertBuilder.danger(
                    t_(ErrorMessages.PASTASTORE_LOAD_FAILED, error=str(e))
                ),
                no_update,
            )

    # ------------------------------------------------------------------
    # Time-range filter callbacks
    # ------------------------------------------------------------------

    @app.callback(
        Output("time-range-tmin-col", "style"),
        Output("time-range-tmax-col", "style"),
        Output(ids.TIME_RANGE_APPLY_BUTTON, "style"),
        Input(ids.TIME_RANGE_PRESET_DROPDOWN, "value"),
        prevent_initial_call=True,
    )
    def toggle_custom_datepickers(preset: str | None):
        """Show custom date pickers and Apply button only for custom preset."""
        if preset == "custom":
            visible = {"display": "block"}
            return visible, visible, visible
        hidden = {"display": "none"}
        return hidden, hidden, hidden

    @app.callback(
        Output(ids.TIME_RANGE_STORE, "data"),
        Input(ids.TIME_RANGE_APPLY_BUTTON, "n_clicks"),
        Input(ids.TIME_RANGE_PRESET_DROPDOWN, "value"),
        State(ids.TIME_RANGE_TMIN_DATEPICKER, "date"),
        State(ids.TIME_RANGE_TMAX_DATEPICKER, "date"),
        State(ids.TIME_RANGE_STORE, "data"),
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def update_time_range_store(
        _n_clicks: int | None,
        preset: str | None,
        custom_tmin: str | None,
        custom_tmax: str | None,
        _current_store: dict | None,
        **kwargs,
    ) -> dict:
        """Update the global time-range store.

        Triggers on either:
        - Initial page load (sync store from dropdown/session-restored value).
        - A change in the preset dropdown (immediately applies non-custom presets).
        - Click of the Apply button (applies custom date range when preset=='custom').

        Parameters
        ----------
        n_clicks : int or None
            Apply button click counter.
        preset : str or None
            Selected preset key.
        custom_tmin : str or None
            Custom start date from the tmin date picker.
        custom_tmax : str or None
            Custom end date from the tmax date picker.
        current_store : dict or None
            Current store value (used as fallback).

        Returns
        -------
        dict
            Updated ``TIME_RANGE_STORE`` value.
        """
        ctx_obj = get_callback_context(**kwargs)
        triggered_id = ctx_obj.triggered_id

        if preset is None:
            return no_update

        # Initial load: align store with the dropdown value that may have been
        # restored by browser/session state.
        if not ctx_obj.triggered:
            return build_time_range_store_value(preset, custom_tmin, custom_tmax)

        # For non-custom presets, update immediately when dropdown changes.
        # For 'custom', only update when the Apply button is clicked.
        if preset != "custom" or triggered_id == ids.TIME_RANGE_APPLY_BUTTON:
            store_value = build_time_range_store_value(preset, custom_tmin, custom_tmax)
            logger.info(
                "Time range updated: preset=%s tmin=%s tmax=%s",
                store_value["preset"],
                store_value["tmin"],
                store_value["tmax"],
            )
            return store_value

        return no_update

    @app.callback(
        Output(ids.OVERVIEW_TIME_RANGE_REFRESH_STORE, "data"),
        Input(ids.TIME_RANGE_STORE, "data"),
        Input(ids.ALERT_TAB_RENDER, "data"),
        State(ids.TAB_CONTAINER, "value"),
        prevent_initial_call=True,
    )
    def refresh_overview_chart_on_time_range(
        time_range_store: dict | None,
        _tab_render_alert: tuple | None,
        active_tab: str | None,
    ) -> tuple | Any:
        """Emit a refresh signal for overview chart only when overview is active."""
        if active_tab != ids.TAB_OVERVIEW:
            return no_update

        if time_range_store is None:
            return no_update

        return TimestampStore.create(success=True)
