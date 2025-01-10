import json
import os

import i18n
import pandas as pd
import pastas as ps
from dash import Input, Output, State, ctx, no_update
from dash.exceptions import PreventUpdate
from packaging.version import parse
from pastas.extensions import register_plotly
from pastas.io.pas import PastasEncoder
from pastastore.version import __version__ as PASTASTORE_VERSION

from gwdatalens.app.src.components import ids

register_plotly()

PASTASTORE_GT_1_7_1 = parse(PASTASTORE_VERSION) > parse("1.7.1")

# %% MODEL TAB


def register_model_callbacks(app, data):
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
        prevent_initial_call=True,
    )
    def generate_model(n_clicks, value, tmin, tmax, use_only_validated):
        """Generate a time series model based on user input and update the stored copy.

        Parameters
        ----------
        n_clicks : int
            Number of clicks on the button that triggers the model generation.
        value : str
            Identifier for the time series in the format "gmw_id-tube_id".
        tmin : str
            Minimum timestamp for the model in a format recognized by `pd.Timestamp`.
        tmax : str
            Maximum timestamp for the model in a format recognized by `pd.Timestamp`.
        use_only_validated : bool
            Flag indicating whether to use only validated data points.

        Returns
        -------
        tuple
            A tuple containing:
            - plotly.graph_objs._figure.Figure: Plotly figure of the model results.
            - plotly.graph_objs._figure.Figure: Plotly figure of the model diagnostics.
            - str: JSON representation of the generated model.
            - bool: Flag to enable or disable the save button.
            - tuple: Alert information containing:
                - bool: Flag to show or hide the alert.
                - str: Alert color ("success" or "danger").
                - str: Alert message.

        Raises
        ------
        PreventUpdate
            If `n_clicks` is None or `value` is None.
        """
        if n_clicks is not None:
            if value is not None:
                try:
                    tmin = pd.Timestamp(tmin)
                    tmax = pd.Timestamp(tmax)
                    # get time series
                    if "-" in value:
                        gmw_id, tube_id = value.split("-")
                    elif "_" in value:
                        gmw_id, tube_id = value.split("_")
                    else:
                        raise ValueError(
                            "Error splitting name into monitoring well ID "
                            f"and tube number: {value}"
                        )
                    ts = data.db.get_timeseries(gmw_id, tube_id)
                    if use_only_validated:
                        mask = ts.loc[:, data.db.qualifier_column] == "goedgekeurd"
                        ts = ts.loc[mask, data.db.value_column].dropna()
                    else:
                        ts = ts.loc[:, data.db.value_column].dropna()

                    if value in data.pstore.oseries_names:
                        # update stored copy
                        data.pstore.update_oseries(ts, value)
                    else:
                        # add series to database
                        metadata = data.db.gmw_gdf.loc[value].to_dict()
                        data.pstore.add_oseries(ts, value, metadata)
                        print(
                            f"Head time series '{value}' added to pastastore database."
                        )

                    if pd.isna(tmin):
                        tmin = ts.index[0]
                    if pd.isna(tmax):
                        tmax = ts.index[-1]

                    # get meteorological info, if need be, and pastastore is up-to-date
                    if PASTASTORE_GT_1_7_1:
                        data.get_knmi_data(value)

                    # create model
                    ml = ps.Model(ts)
                    data.pstore.add_recharge(ml)
                    ml.solve(freq="D", tmin=tmin, tmax=tmax, report=False)
                    ml.add_noisemodel(ps.ArNoiseModel())
                    ml.solve(
                        freq="D",
                        tmin=tmin,
                        tmax=tmax,
                        report=False,
                        initial=False,
                    )
                    # store generated model
                    mljson = json.dumps(ml.to_dict(), cls=PastasEncoder)
                    return (
                        ml.plotly.results(tmin=tmin, tmax=tmax),
                        ml.plotly.diagnostics(),
                        mljson,
                        False,  # enable save button
                        (
                            True,  # show alert
                            "success",  # alert color
                            f"Created time series model for {value}.",
                        ),  # empty alert message
                    )
                except Exception as e:
                    return (
                        no_update,
                        no_update,
                        None,
                        True,  # disable save button
                        (
                            True,  # show alert
                            "danger",  # alert color
                            f"Error {e}",  # alert message
                        ),
                    )
            else:
                raise PreventUpdate
        else:
            raise PreventUpdate

    @app.callback(
        Output(ids.ALERT_SAVE_MODEL, "data"),
        Input(ids.MODEL_SAVE_BUTTON, "n_clicks"),
        State(ids.PASTAS_MODEL_STORE, "data"),
        prevent_initial_call=True,
    )
    def save_model(n_clicks, mljson):
        """Save a model from a JSON string when a button is clicked.

        Parameters
        ----------
        n_clicks : int
            The number of times the save button has been clicked.
        mljson : str
            The JSON string representation of the model to be saved.

        Returns
        -------
        tuple
            A tuple containing a boolean indicating success, a string for the alert
            type, and a message string.

        Raises
        ------
        PreventUpdate
            If `n_clicks` is None or `mljson` is None.
        """
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
        Output(ids.MODEL_RESULTS_CHART_2, "data"),
        Output(ids.MODEL_DIAGNOSTICS_CHART_2, "data"),
        Output(ids.MODEL_SAVE_BUTTON_2, "data"),
        Output(ids.ALERT_PLOT_MODEL_RESULTS, "data"),
        Output(ids.MODEL_DATEPICKER_TMIN, "date"),
        Output(ids.MODEL_DATEPICKER_TMAX, "date"),
        Input(ids.MODEL_DROPDOWN_SELECTION, "value"),
        prevent_initial_call=True,
    )
    def plot_model_results(value):
        """Plot the results and diagnostics of a time series model.

        Parameters
        ----------
        value : str or None
            The identifier of the model to be plotted. If None, no model is selected.

        Returns
        -------
        tuple
            A tuple containing:
            - plotly.graph_objs.Figure: The plotly figure of the model results.
            - plotly.graph_objs.Figure: The plotly figure of the model diagnostics.
            - bool: A flag indicating whether to activate model save button.
            - tuple: A tuple containing:
                - bool: A flag indicating if an alert should be shown.
                - str: The color of the alert ('success' or 'warning').
                - str: The alert message.
            - datetime.datetime or None: The minimum time of the model settings,
              or None if not available.
            - datetime.datetime or None: The maximum time of the model settings,
              or None if not available.

        Raises
        ------
        Exception
            If there is an error in retrieving or plotting the model.
        """
        if value is not None:
            try:
                ml = data.pstore.get_models(value)
                return (
                    ml.plotly.results(),
                    ml.plotly.diagnostics(),
                    True,
                    (
                        True,  # show alert
                        "success",  # alert color
                        f"Loaded time series model '{value}' from PastaStore.",
                    ),
                    ml.settings["tmin"].to_pydatetime(),
                    ml.settings["tmax"].to_pydatetime(),
                )
            except Exception as e:
                return (
                    {"layout": {"title": i18n.t("general.no_model")}},
                    {"layout": {"title": i18n.t("general.no_model")}},
                    True,
                    (
                        True,  # show alert
                        "warning",  # alert color
                        (
                            f"No model available for {value}. "
                            f"Click 'Generate Model' to create one. Error: {e}"
                        ),
                    ),
                    None,
                    None,
                )
        elif value is None:
            return (
                {"layout": {"title": i18n.t("general.no_model")}},
                {"layout": {"title": i18n.t("general.no_model")}},
                True,
                (
                    False,  # show alert
                    "success",  # alert color
                    "",  # empty message
                ),
                None,
                None,
            )

    @app.callback(
        Output(ids.MODEL_RESULTS_CHART, "figure"),
        Input(ids.MODEL_RESULTS_CHART_1, "data"),
        Input(ids.MODEL_RESULTS_CHART_2, "data"),
        prevent_initial_call=True,
    )
    def update_model_results_chart(*figs, **kwargs):
        """Updates the model result plot.

        Parameters
        ----------
        *figs : tuple
            tuple(s) of name and figure dictionary.
        **kwargs : dict
            callback_context

        Returns
        -------
        figure: dict
            The figure corresponding to the triggered input.

        Raises
        ------
        PreventUpdate
            If no figures are provided.
        """
        if len(kwargs) > 0:
            ctx_ = kwargs["callback_context"]
            triggered_id = ctx_.triggered[0]["prop_id"].split(".")[0]
            inputs_list = ctx_.inputs_list
        else:
            triggered_id = ctx.triggered_id
            inputs_list = ctx.inputs_list
        if any(figs):
            for i in range(len(inputs_list)):
                if inputs_list[i]["id"] == triggered_id:
                    break
            figure = figs[i]
            return figure
        else:
            raise PreventUpdate

    @app.callback(
        Output(ids.MODEL_DIAGNOSTICS_CHART, "figure"),
        Input(ids.MODEL_DIAGNOSTICS_CHART_1, "data"),
        Input(ids.MODEL_DIAGNOSTICS_CHART_2, "data"),
        prevent_initial_call=True,
    )
    def update_model_diagnostics_chart(*figs, **kwargs):
        """Updates the model diagnostics chart based on the triggered input.

        Parameters
        ----------
        *figs : tuple
            A variable length tuple of figures to be potentially updated.
        **kwargs : dict
            callback_context

        Returns
        -------
        figure : dict
            The updated figure corresponding to the triggered input.

        Raises
        ------
        PreventUpdate
            If no figures are provided in the `figs` argument.
        """
        if len(kwargs) > 0:
            ctx_ = kwargs["callback_context"]
            triggered_id = ctx_.triggered[0]["prop_id"].split(".")[0]
            inputs_list = ctx_.inputs_list
        else:
            triggered_id = ctx.triggered_id
            inputs_list = ctx.inputs_list

        if any(figs):
            for i in range(len(inputs_list)):
                if inputs_list[i]["id"] == triggered_id:
                    break
            figure = figs[i]
            return figure
        else:
            raise PreventUpdate

    @app.callback(
        Output(ids.MODEL_SAVE_BUTTON, "disabled"),
        Input(ids.MODEL_SAVE_BUTTON_1, "data"),
        Input(ids.MODEL_SAVE_BUTTON_2, "data"),
        prevent_initial_call=True,
    )
    def toggle_model_save_button(*b, **kwargs):
        """Toggles the model save button based on the provided inputs.

        Parameters
        ----------
        *b : tuple
            tuple of booleans indicating triggered state of button.
        **kwargs : dict
            callback_context

        Returns
        -------
        bool
            whether button is enabled or disabled.

        Raises
        ------
        PreventUpdate
            If none of the inputs are triggered.
        """
        if len(kwargs) > 0:
            ctx_ = kwargs["callback_context"]
            triggered_id = ctx_.triggered[0]["prop_id"].split(".")[0]
            inputs_list = ctx_.inputs_list
        else:
            triggered_id = ctx.triggered_id
            inputs_list = ctx.inputs_list

        if any(boolean is not None for boolean in b):
            for i in range(len(inputs_list)):
                if inputs_list[i]["id"] == triggered_id:
                    break
            return b[i]
        else:
            raise PreventUpdate
