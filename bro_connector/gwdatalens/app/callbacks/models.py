import json
import logging
import os
from typing import Any

import pandas as pd
import pastas as ps
from dash import Input, Output, State, no_update
from dash.exceptions import PreventUpdate
from packaging.version import parse
from pastas.extensions import register_plotly
from pastas.io.pas import PastasEncoder
from pastastore.version import __version__ as PASTASTORE_VERSION

from gwdatalens.app.constants import ConfigDefaults
from gwdatalens.app.messages import ErrorMessages, SuccessMessages, t_
from gwdatalens.app.src.components import ids
from gwdatalens.app.src.services import TimeSeriesService, WellService
from gwdatalens.app.src.utils import log_callback
from gwdatalens.app.src.utils.callback_helpers import (
    AlertBuilder,
    CallbackResponse,
    EmptyFigure,
    get_callback_context,
)

logger = logging.getLogger(__name__)
register_plotly()

PASTASTORE_GT_1_7_1 = parse(PASTASTORE_VERSION) > parse("1.7.1")

# %% MODEL TAB


def register_model_callbacks(app, data):
    ts_service = TimeSeriesService(data.db)
    well_service = WellService(data.db)

    @app.callback(
        Output(ids.MODEL_RESULTS_CHART_1, "data"),
        Output(ids.MODEL_DIAGNOSTICS_CHART_1, "data"),
        Output(ids.PASTAS_MODEL_STORE, "data"),
        Output(ids.MODEL_SAVE_BUTTON_1, "data"),
        Output(ids.ALERT_GENERATE_MODEL, "data"),
        Input(ids.MODEL_GENERATE_BUTTON, "n_clicks"),
        State(ids.MODEL_DROPDOWN_SELECTION, "value"),
        State(ids.MODEL_DATEPICKER_TMIN, "date"),
        State(ids.MODEL_DATEPICKER_TMAX, "date"),
        State(ids.MODEL_USE_ONLY_VALIDATED, "value"),
        running=[
            (Output(ids.LOADING_MODEL_RESULTS_CHART, "display"), "show", "auto"),
            (Output(ids.LOADING_MODEL_DIAGNOSTICS_CHART, "display"), "show", "auto"),
        ],
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def generate_model(
        n_clicks: int | None,
        wid: int | None,
        tmin: str | None,
        tmax: str | None,
        use_only_validated: bool,
    ) -> tuple[dict, dict, str, dict, tuple]:
        """Generate a time series model based on user input.

        Creates a Pastas model, solves it, and stores it for saving.
        """
        if n_clicks is None or wid is None:
            raise PreventUpdate

        try:
            tmin = pd.Timestamp(tmin)
            tmax = pd.Timestamp(tmax)

            # Get time series via service
            if use_only_validated:
                ts = ts_service.get_validated_timeseries(wid)
            else:
                ts = ts_service.get_timeseries_values(wid)

            # Get well name for model
            name = well_service.get_well_name(wid)

            # Add or update series in pastastore
            if name in data.pastastore.oseries_names:
                data.pastastore.update_oseries(ts, name, force=True)
                logger.info(
                    "Head time series '%s' updated in pastastore database.", name
                )
            else:
                metadata = well_service.get_well_metadata(wid)
                data.pastastore.add_oseries(ts, name, metadata)
                logger.info("Head time series '%s' added to pastastore database.", name)

            # Set time range from data if not specified
            if pd.isna(tmin):
                tmin = ts.index[0]
            if pd.isna(tmax):
                tmax = ts.index[-1]

            # Get meteorological data if available
            if PASTASTORE_GT_1_7_1:
                data.get_knmi_data(name)

            # Create and solve model
            ml = ps.Model(ts)
            data.pastastore.add_recharge(ml)
            ml.solve(freq="D", tmin=tmin, tmax=tmax, report=False)
            ml.add_noisemodel(ps.ArNoiseModel())
            ml.solve(freq="D", tmin=tmin, tmax=tmax, report=False, initial=False)

            # Serialize model
            mljson = json.dumps(ml.to_dict(), cls=PastasEncoder)

            return (
                CallbackResponse()
                .add_figure(ml.plotly.results(tmin=tmin, tmax=tmax))
                .add_figure(ml.plotly.diagnostics())
                .add_data(mljson)
                .add(False)  # enable save button
                .add(AlertBuilder.success(f"Created time series model for {name}."))
                .build()
            )

        # generic exception to catch all errors related to creating a model
        except Exception as e:
            logger.exception("Error generating model for %s: %s", wid, e)
            return (
                CallbackResponse()
                .add(no_update)
                .add(no_update)
                .add(None)
                .add(True)  # disable save button
                .add(AlertBuilder.danger(f"Error: {e}"))
                .build()
            )

    @app.callback(
        Output(ids.ALERT_SAVE_MODEL, "data"),
        Input(ids.MODEL_SAVE_BUTTON, "n_clicks"),
        State(ids.PASTAS_MODEL_STORE, "data"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def save_model(n_clicks: int | None, mljson: str | None) -> tuple:
        """Save a model to Pastastore.

        Deserializes model from JSON and stores it in Pastastore.
        """
        if n_clicks is None or mljson is None:
            raise PreventUpdate

        # Deserialize model from JSON (via temp file - Pastas API limitation)
        with open("temp.pas", "w") as f:
            f.write(mljson)
        ml = ps.io.load("temp.pas")
        os.remove("temp.pas")

        try:
            data.pastastore.add_model(ml, overwrite=True)
            return AlertBuilder.success(
                f"Success! Saved model for {ml.oseries.name} in Pastastore!"
            )
        except Exception as e:
            logger.exception("Error saving model for %s: %s", ml.oseries.name, e)
            return AlertBuilder.danger(
                f"Error! Model for {ml.oseries.name} not saved: {e}!"
            )

    @app.callback(
        Output(ids.MODEL_RESULTS_CHART_2, "data"),
        Output(ids.MODEL_DIAGNOSTICS_CHART_2, "data"),
        Output(ids.MODEL_SAVE_BUTTON_2, "data"),
        Output(ids.ALERT_PLOT_MODEL_RESULTS, "data"),
        Output(ids.MODEL_DATEPICKER_TMIN, "date"),
        Output(ids.MODEL_DATEPICKER_TMAX, "date"),
        Input(ids.MODEL_DROPDOWN_SELECTION, "value"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def plot_model_results(wid: int | None) -> tuple[dict, dict, bool, tuple, Any, Any]:
        """Plot results and diagnostics for a stored model.

        Loads model from Pastastore and displays results.
        """
        if wid is None:
            empty_fig = EmptyFigure.with_message(t_("general.no_model"))
            return (
                CallbackResponse()
                .add_figure(empty_fig)
                .add_figure(empty_fig)
                .add(True)  # disable save button
                .add(AlertBuilder.no_alert())
                .add(None)  # tmin
                .add(None)  # tmax
                .build()
            )

        try:
            name = well_service.get_well_name(wid)
            ml = data.pastastore.get_models(name)

            return (
                CallbackResponse()
                .add_figure(ml.plotly.results())
                .add_figure(ml.plotly.diagnostics())
                .add(True)  # disable save button (model already saved)
                .add(
                    AlertBuilder.success(
                        t_(SuccessMessages.TIMESERIES_LOADED_FROM_PASTASTORE, name=name)
                    )
                )
                .add(ml.settings["tmin"].to_pydatetime())
                .add(ml.settings["tmax"].to_pydatetime())
                .build()
            )

        except Exception as e:
            logger.warning("No model available for %s: %s", name, e)
            empty_fig = EmptyFigure.with_message(t_("general.no_model"))
            return (
                CallbackResponse()
                .add_figure(empty_fig)
                .add_figure(empty_fig)
                .add(True)  # disable save button
                .add(AlertBuilder.warning(t_(ErrorMessages.NO_MODEL_ERROR, name=name)))
                .add(None)  # tmin
                .add(None)  # tmax
                .build()
            )

    @app.callback(
        Output(ids.MODEL_RESULTS_CHART, "figure"),
        Input(ids.MODEL_RESULTS_CHART_1, "data"),
        Input(ids.MODEL_RESULTS_CHART_2, "data"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def update_model_results_chart(*figs: dict, **kwargs: Any) -> dict:
        """Update model results chart from triggered input.

        Switches between generated model (chart_1) and loaded model (chart_2).
        """
        if not any(figs):
            raise PreventUpdate

        ctx_obj = get_callback_context(**kwargs)
        triggered_id = ctx_obj.triggered_id
        inputs_list = ctx_obj.inputs_list

        # Find which input was triggered
        for i, input_item in enumerate(inputs_list):
            if input_item["id"] == triggered_id:
                return figs[i]

        raise PreventUpdate

    @app.callback(
        Output(ids.MODEL_DIAGNOSTICS_CHART, "figure"),
        Input(ids.MODEL_DIAGNOSTICS_CHART_1, "data"),
        Input(ids.MODEL_DIAGNOSTICS_CHART_2, "data"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def update_model_diagnostics_chart(*figs: dict, **kwargs: Any) -> dict:
        """Update model diagnostics chart from triggered input.

        Switches between generated model (chart_1) and loaded model (chart_2).
        """
        if not any(figs):
            raise PreventUpdate

        ctx_obj = get_callback_context(**kwargs)
        triggered_id = ctx_obj.triggered_id
        inputs_list = ctx_obj.inputs_list

        # Find which input was triggered
        for i, input_item in enumerate(inputs_list):
            if input_item["id"] == triggered_id:
                return figs[i]

        raise PreventUpdate

    @app.callback(
        Output(ids.MODEL_SAVE_BUTTON, "disabled"),
        Input(ids.MODEL_SAVE_BUTTON_1, "data"),
        Input(ids.MODEL_SAVE_BUTTON_2, "data"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def toggle_model_save_button(*b: bool | None, **kwargs: Any) -> bool:
        """Toggle model save button enabled/disabled state.

        Disabled when model is loaded from store, enabled after generation.
        """
        if not any(boolean is not None for boolean in b):
            raise PreventUpdate

        ctx_obj = get_callback_context(**kwargs)
        triggered_id = ctx_obj.triggered_id
        inputs_list = ctx_obj.inputs_list

        # Find which input was triggered
        for i, input_item in enumerate(inputs_list):
            if input_item["id"] == triggered_id:
                return b[i]

        raise PreventUpdate
