import json
import os

import i18n
import pandas as pd
import pastas as ps
from dash import Input, Output, State, no_update
from dash.exceptions import PreventUpdate
from pastas.extensions import register_plotly
from pastas.io.pas import PastasEncoder

from ..src.components import ids

register_plotly()


# %% MODEL TAB


def register_model_callbacks(app, data):
    @app.callback(
        Output(ids.MODEL_RESULTS_CHART, "figure", allow_duplicate=True),
        Output(ids.MODEL_DIAGNOSTICS_CHART, "figure", allow_duplicate=True),
        Output(ids.PASTAS_MODEL_STORE, "data"),
        Output(ids.MODEL_SAVE_BUTTON, "disabled", allow_duplicate=True),
        Output(ids.ALERT, "is_open", allow_duplicate=True),
        Output(ids.ALERT, "color", allow_duplicate=True),
        Output(ids.ALERT_BODY, "children", allow_duplicate=True),
        Input(ids.MODEL_GENERATE_BUTTON, "n_clicks"),
        State(ids.MODEL_DROPDOWN_SELECTION, "value"),
        State(ids.MODEL_DATEPICKER_TMIN, "date"),
        State(ids.MODEL_DATEPICKER_TMAX, "date"),
        prevent_initial_call=True,
    )
    def generate_model(n_clicks, value, tmin, tmax):
        if n_clicks is not None:
            if value is not None:
                try:
                    tmin = pd.Timestamp(tmin)
                    tmax = pd.Timestamp(tmax)
                    ml = data.pstore.create_model(value, add_recharge=True)
                    ml.solve(freq="D", tmin=tmin, tmax=tmax, report=False, noise=False)
                    ml.solve(
                        freq="D",
                        tmin=tmin,
                        tmax=tmax,
                        noise=True,
                        report=False,
                        initial=False,
                    )
                    mljson = json.dumps(
                        ml.to_dict(), cls=PastasEncoder
                    )  # store generated model
                    return (
                        ml.plotly.results(),
                        ml.plotly.diagnostics(),
                        mljson,
                        False,  # enable save button
                        True,  # show alert
                        "success",  # alert color
                        f"Created time series model for {value}.",  # empty alert message
                    )
                except Exception as e:
                    return (
                        no_update,
                        no_update,
                        None,
                        True,  # disable save button
                        True,  # show alert
                        "danger",  # alert color
                        f"Error {e}",  # alert message
                    )
            else:
                raise PreventUpdate
        else:
            raise PreventUpdate

    @app.callback(
        Output(ids.ALERT, "is_open", allow_duplicate=True),
        Output(ids.ALERT, "color", allow_duplicate=True),
        Output(ids.ALERT_BODY, "children", allow_duplicate=True),
        Input(ids.MODEL_SAVE_BUTTON, "n_clicks"),
        State(ids.PASTAS_MODEL_STORE, "data"),
        prevent_initial_call=True,
    )
    def save_model(n_clicks, mljson):
        if n_clicks is None:
            raise PreventUpdate
        if mljson is not None:
            with open("temp.pas", "w") as f:
                f.write(mljson)
            ml = ps.io.load("temp.pas")
            os.remove("temp.pas")
            try:
                data.pstore.add_model(ml, overwrite=True)
                return (
                    True,
                    "success",
                    f"Success! Saved model for {ml.oseries.name} in Pastastore!",
                )
            except Exception as e:
                return (
                    True,
                    "danger",
                    f"Error! Model for {ml.oseries.name} not saved: {e}!",
                )
        else:
            raise PreventUpdate

    @app.callback(
        Output(ids.MODEL_RESULTS_CHART, "figure", allow_duplicate=True),
        Output(ids.MODEL_DIAGNOSTICS_CHART, "figure", allow_duplicate=True),
        Output(ids.MODEL_SAVE_BUTTON, "disabled", allow_duplicate=True),
        Output(ids.ALERT, "is_open", allow_duplicate=True),
        Output(ids.ALERT, "color", allow_duplicate=True),
        Output(ids.ALERT_BODY, "children", allow_duplicate=True),
        Output(ids.MODEL_DATEPICKER_TMIN, "date"),
        Output(ids.MODEL_DATEPICKER_TMAX, "date"),
        Input(ids.MODEL_DROPDOWN_SELECTION, "value"),
        prevent_initial_call=True,
    )
    def plot_model_results(value):
        if value is not None:
            try:
                ml = data.pstore.get_models(value)
                return (
                    ml.plotly.results(),
                    ml.plotly.diagnostics(),
                    True,
                    True,  # show alert
                    "success",  # alert color
                    f"Loaded time series model '{value}' from PastaStore.",  # empty alert message
                    ml.settings["tmin"].to_pydatetime(),
                    ml.settings["tmax"].to_pydatetime(),
                )
            except Exception as _:
                return (
                    {"layout": {"title": i18n.t("general.no_model")}},
                    {"layout": {"title": i18n.t("general.no_model")}},
                    True,
                    True,  # show alert
                    "warning",  # alert color
                    f"No model available for {value}. Click 'Generate Model' to create one.",
                    None,
                    None,
                )
        elif value is None:
            return (
                {"layout": {"title": i18n.t("general.no_model")}},
                {"layout": {"title": i18n.t("general.no_model")}},
                True,
                False,  # show alert
                "success",  # alert color
                "",  # empty message
                None,
                None,
            )
