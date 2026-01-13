import base64
import io
import logging
import pickle
from typing import Any

import pandas as pd
import traval
from dash import (
    ALL,
    MATCH,
    Input,
    Output,
    State,
    dcc,
    html,
    no_update,
)
from dash.exceptions import PreventUpdate

from gwdatalens.app.constants import ConfigDefaults
from gwdatalens.app.exceptions import (
    EmptyResultError,
)
from gwdatalens.app.messages import ErrorMessages, SuccessMessages, t_
from gwdatalens.app.src.components import ids
from gwdatalens.app.src.components.overview_chart import plot_obs
from gwdatalens.app.src.components.qc_rules_form import (
    derive_form_parameters,
    generate_traval_rule_components,
)
from gwdatalens.app.src.services import QCService, TimeSeriesService, WellService
from gwdatalens.app.src.utils import log_callback
from gwdatalens.app.src.utils.callback_helpers import (
    AlertBuilder,
    CallbackResponse,
    EmptyFigure,
    extract_trigger_id,
    get_callback_context,
)
from gwdatalens.app.validators import validate_not_empty

logger = logging.getLogger(__name__)


# %% TRAVAL TAB
def register_qc_callbacks(app, data):
    qc_service = QCService(data.qc, data.db)
    well_service = WellService(data.db)
    ts_service = TimeSeriesService(data.db)

    def _get_trigger_index(triggered_id, inputs_list):
        for i, item in enumerate(inputs_list):
            if item["id"] == triggered_id:
                return i
        return 0

    @app.callback(
        Output(
            {"type": "rule_input_tooltip", "index": MATCH},
            "children",
            allow_duplicate=True,
        ),
        Input({"type": "rule_input", "index": MATCH}, "value"),
        Input({"type": "rule_input", "index": MATCH}, "disabled"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def update_ruleset_values(val: Any, disabled: bool, **kwargs) -> list[str]:
        """Update the values of a ruleset."""
        if disabled:
            return no_update

        ctx_obj = get_callback_context(**kwargs)
        triggered_id = extract_trigger_id(ctx_obj, parse_json=True)
        _, rule_name, param = triggered_id["index"].split("-")
        qc_service.update_rule_parameter(rule_name, param, val)
        return [str(val)]

    @app.callback(
        Output(ids.QC_CHART_STORE_1, "data"),
        Input(ids.QC_DROPDOWN_SELECTION, "value"),
        Input(ids.QC_DROPDOWN_ADDITIONAL, "value"),
        # State(ids.QC_DROPDOWN_ADDITIONAL, "disabled"),  # NOTE: not sure what for?
        State(ids.TRAVAL_RESULT_FIGURE_STORE, "data"),
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def plot_qc_time_series(
        value: int | None,
        additional_values: list[int] | None,
        traval_figure: tuple | None,
    ) -> dict:
        """Plot time series.

        Parameters
        ----------
        value : str or None
            The primary series to plot. If None, a message indicating no series is
            selected will be returned.
        additional_values : list or None
            Additional series to include in the plot. If None, no additional series
            will be included.
        traval_figure : tuple or None
            A tuple containing a stored name and a traval-result figure. If the stored
            name matches the primary series name, the traval-figure will be returned.

        Returns
        -------
        dict
            A dictionary representing the plot layout or the pre-generated figure if
            available.
        """
        if value is None:
            return EmptyFigure.no_selection()

        additional = additional_values or []

        if traval_figure is not None:
            stored_name, figure = traval_figure
            if stored_name == value:
                return figure

        return plot_obs([value] + additional, data)

    @app.callback(
        Output(ids.QC_DROPDOWN_ADDITIONAL_DISABLED_1, "data"),
        Output(ids.QC_DROPDOWN_ADDITIONAL, "options"),
        Input(ids.QC_DROPDOWN_SELECTION, "value"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def enable_additional_dropdown(wid: int | None) -> tuple[bool, list[dict] | Any]:
        """Enable or disable an additional time series dropdown based.

        Parameters
        ----------
        value : str or None
            A string representing a location identifier or None.

        Returns
        -------
        tuple
            A tuple containing a boolean and a list of dictionaries. The boolean
            indicates whether the dropdown should be disabled (True) or enabled (False).
            The list of dictionaries contains the options for the dropdown, where each
            dictionary has a 'label' and a 'value' key.
        """
        if wid is None:
            return True, no_update

        options = well_service.format_wells_as_options(wid)
        return False, options

    @app.callback(
        Output(ids.QC_DATEPICKER_TMIN, "disabled"),
        Output(ids.QC_DATEPICKER_TMIN, "date"),
        Output(ids.QC_DATEPICKER_TMAX, "disabled"),
        Output(ids.QC_DATEPICKER_TMAX, "date"),
        Input(ids.QC_DROPDOWN_SELECTION, "value"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def enable_datepickers(wid: int | None) -> tuple[bool, Any, bool, Any]:
        """Enable datepickers and set dates when a well is selected.

        Parameters
        ----------
        wid : int or None
            Internal ID of the selected well.

        Returns
        -------
        tuple
            (tmin_disabled, tmin_date, tmax_disabled, tmax_date)
        """
        if wid is None:
            return True, None, True, None

        try:
            ts = ts_service.get_timeseries_with_column(wid)
            validate_not_empty(ts, context="time series for date range")

            start_date = ts.index[0].to_pydatetime()
            end_date = ts.index[-1].to_pydatetime()
            return False, start_date, False, end_date
        except EmptyResultError:
            logger.warning("No time series data for well %s", wid)
            return True, None, True, None
        except Exception as e:
            logger.exception("Error enabling datepickers for well %s: %s", wid, e)
            return True, None, True, None

    @app.callback(
        Output(ids.TRAVAL_RULES_FORM_STORE_1, "data"),
        Output(ids.TRAVAL_RESET_RULESET_BUTTON_STORE_1, "data"),
        Input({"type": "clear-button", "index": ALL}, "n_clicks"),
        State({"type": "clear-button", "index": ALL}, "n_clicks"),
        State(ids.TRAVAL_RULES_FORM, "children"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def delete_rule(
        n_clicks: list[int | None],
        _clickstate: list[int | None],
        rules: list[dict],
        **kwargs,
    ) -> tuple[list[dict], bool]:
        """Delete a rule from the ruleset when its clear button is clicked."""
        if all(v is None for v in n_clicks):
            raise PreventUpdate

        ctx_obj = get_callback_context(**kwargs)
        triggered_id = extract_trigger_id(ctx_obj, parse_json=True)
        keep = [
            rule
            for rule in rules
            if rule["props"]["id"]["index"] != triggered_id["index"]
        ]
        qc_service.delete_rule_from_ruleset(triggered_id["index"])
        return keep, False

    @app.callback(
        Output(ids.TRAVAL_RULES_FORM_STORE_2, "data"),
        Output(ids.TRAVAL_RESET_RULESET_BUTTON_STORE_2, "data"),
        Input(ids.TRAVAL_ADD_RULE_BUTTON, "n_clicks"),
        State(ids.TRAVAL_ADD_RULE_DROPDOWN, "value"),
        State(ids.TRAVAL_RULES_FORM, "children"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def add_rule(
        n_clicks: int | None, rule_to_add: str, current_rules: list[dict]
    ) -> tuple[list[dict], bool]:
        """Add a new rule to the current set of rules."""
        if not n_clicks:
            raise PreventUpdate

        try:
            rule_number = (
                int(current_rules[-1]["props"]["id"]["index"].split("-")[-1]) + 1
            )
        except IndexError:
            rule_number = 0

        rule = qc_service.add_rule_to_ruleset(rule_to_add)
        irow = generate_traval_rule_components(
            rule, rule_number, well_service=well_service
        )
        current_rules.append(irow)
        return current_rules, False

    @app.callback(
        Output({"type": "rule_input", "index": ALL}, "value"),
        Output({"type": "rule_input", "index": ALL}, "type"),
        Output({"type": "rule_input", "index": ALL}, "disabled"),
        Output({"type": "rule_input", "index": ALL}, "step"),
        Output(
            {"type": "rule_input_tooltip", "index": ALL},
            "children",
            allow_duplicate=True,
        ),
        Output(ids.TRAVAL_RESET_RULESET_BUTTON_STORE_3, "data"),
        Output(ids.ALERT_DISPLAY_RULES_FOR_SERIES, "data"),
        Input(ids.QC_DROPDOWN_SELECTION, "value"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def display_rules_for_series(
        wid: int | None,
    ) -> tuple[list, list, list, list, list, bool, tuple]:
        """Display rules for a given series name.

        Parameters
        ----------
        wid : int
            The internal id of the series for which to display rules.

        Returns
        -------
        tuple
            A tuple containing:
            - values : list
                List of derived values for each rule.
            - input_types : list
                List of input types for each rule.
            - disableds : list
                List indicating whether each input is disabled.
            - steps : list
                List of step values for each rule.
            - tooltips : list
                List of tooltips for each rule.
            - bool
                Enable/disable reset rule button.
            - alert tuple
                A tuple containing:
                - bool
                    show alert
                - str or None
                    The type of alert to display if there were errors.
                - str or None
                    The error message if there were errors.
        """
        values = []
        input_types = []
        disableds = []
        steps = []
        tooltips = []
        nrules = len(qc_service.traval._ruleset.rules) - 1
        errors = []

        name = well_service.get_well_name(wid) if wid is not None else None
        for i in range(1, nrules + 1):
            irule = qc_service.get_rule_from_ruleset(istep=i)
            irule_orig = qc_service.traval.ruleset.get_rule(istep=i)
            orig_kwargs = irule_orig.get("kwargs", {}) or {}
            for k, v in irule["kwargs"].items():
                # savedir is not rendered as an input; skip to keep output lengths aligned
                if irule["name"] == "pastas" and k == "savedir":
                    continue
                vorig = orig_kwargs.get(k)
                derived_value = v
                if callable(vorig) and name is not None:
                    try:
                        derived_value = vorig(name)
                    except KeyError:
                        logger.exception(
                            "No parameter for rule %s.%s, series %s",
                            irule["name"],
                            k,
                            name,
                        )
                        errors.append(f"{irule['name']}: {k}")
                    # generic exception for other potential errors
                    except Exception as e:
                        logger.error(
                            "Could not derive parameter for rule %s.%s, "
                            "for time series %s",
                            irule["name"],
                            k,
                            name,
                        )
                        raise e

                value, input_type, disabled, step = derive_form_parameters(
                    derived_value
                )
                tooltips.append(str(value))
                values.append(value)
                input_types.append(input_type)
                disableds.append(disabled)
                steps.append(step)

        alert = (
            AlertBuilder.danger(f"Error! Could not load parameter(s) for: {errors}")
            if errors
            else AlertBuilder.no_alert()
        )

        return (
            values,
            input_types,
            disableds,
            steps,
            tooltips,
            False,
            alert,
        )

    @app.callback(
        Output(ids.TRAVAL_RULES_FORM_STORE_3, "data"),
        Input(ids.TRAVAL_RESET_RULESET_BUTTON, "n_clicks"),
        State(ids.QC_DROPDOWN_SELECTION, "value"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def reset_ruleset_to_current_default(
        n_clicks: int | None, name: str | None
    ) -> list[dict]:
        """Resets the ruleset to its current default and generates form components.

        Parameters
        ----------
        n_clicks : int
            The number of clicks on the reset button. If None, the function
            raises PreventUpdate.
        name : str
            The name of the series for which the ruleset is being reset.

        Returns
        -------
        list
            A list of form components generated from the ruleset.

        Raises
        ------
        PreventUpdate
            If `n_clicks` is None.
        """
        if n_clicks is None:
            raise PreventUpdate

        form_components = []
        nrules = len(qc_service.traval.ruleset.rules) - 1

        qc_service.reset_ruleset_to_default()

        idx = 0
        for i in range(1, nrules + 1):
            irule = qc_service.traval.ruleset.get_rule(istep=i)
            irow = generate_traval_rule_components(irule, idx, series_name=name)
            form_components.append(irow)
            idx += 1
        return form_components

    @app.callback(
        Output(ids.TRAVAL_ADD_RULE_BUTTON, "disabled"),
        Input(ids.TRAVAL_ADD_RULE_DROPDOWN, "value"),
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def activate_add_rule_button(value: Any) -> bool:
        """Set the state of the "Add Rule" button.

        Parameters
        ----------
        value : any
            The input value to evaluate.

        Returns
        -------
        bool
            False if the value is not None, otherwise True.
        """
        if value is not None:
            return False
        return True

    @app.callback(
        Output(ids.TRAVAL_RULES_FORM_STORE_4, "data"),
        Output(ids.ALERT_LOAD_RULESET, "data"),
        Input(ids.TRAVAL_LOAD_RULESET_BUTTON, "contents"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def load_ruleset(contents: str | None) -> tuple[list[dict] | Any, tuple]:
        """Get input timeseries data.

        Parameters
        ----------
        contents : str
            64bit encoded input data

        Returns
        -------
        series : pandas.Series
            input series data
        """
        if contents is None:
            raise PreventUpdate

        try:
            _content_type, content_string = contents.split(",")
            decoded = base64.b64decode(content_string)
            rules = pickle.load(io.BytesIO(decoded))

            ruleset = traval.RuleSet(name=rules.pop("name"))
            ruleset.rules.update(rules)

            qc_service.traval._ruleset = ruleset

            nrules = len(qc_service.traval._ruleset.rules) - 1
            form_components = []
            idx = 0
            for i in range(1, nrules + 1):
                irule = qc_service.traval._ruleset.get_rule(istep=i)
                irow = generate_traval_rule_components(
                    irule, idx, well_service=well_service
                )
                form_components.append(irow)
                idx += 1

            return form_components, AlertBuilder.success(
                t_(SuccessMessages.RULESET_LOADED)
            )
        except Exception as e:
            logger.warning("Failed to load ruleset: %s", e, exc_info=True)
            return no_update, AlertBuilder.warning(
                t_(ErrorMessages.RULESET_LOAD_ERROR, error=str(e))
            )

    @app.callback(
        Output(ids.DOWNLOAD_TRAVAL_RULESET, "data"),
        Input(ids.TRAVAL_EXPORT_RULESET_BUTTON, "n_clicks"),
        State(ids.SELECTED_OSERIES_STORE, "data"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def export_ruleset(n_clicks: int | None, wid: list[int] | None) -> Any:
        """Export the current ruleset to a pickle file.

        Parameters
        ----------
        n_clicks : int
            The number of times the export button has been clicked. Used to trigger
            function.
        wid : list of int
            internal id of the well

        Returns
        -------
        dcc.send_bytes
            A Dash component that triggers the download of the ruleset as a pickle file.

        Notes
        -----
        The filename of the exported ruleset will be in the format:
        'YYYYMMDD_HHMMSS_traval_ruleset_<name>.pickle', where <name> is the name
        of the time series.
        """
        timestr = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        name = well_service.get_well_name(wid).squeeze()
        filename = f"{timestr}_traval_ruleset_{name}.pickle"
        if qc_service.traval._ruleset is not None:
            ruleset = qc_service.get_resolved_ruleset_for_series(name)
            rules = ruleset.rules

            def to_pickle(f):
                """Version of to_pickle that works with dcc Download component."""
                rules["name"] = name
                pickle.dump(rules, f)

            return dcc.send_bytes(to_pickle, filename=filename)

    @app.callback(
        Output(ids.DOWNLOAD_TRAVAL_PARAMETERS_CSV, "data"),
        Input(ids.TRAVAL_EXPORT_PARAMETERS_CSV_BUTTON, "n_clicks"),
        State(ids.SELECTED_OSERIES_STORE, "data"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def export_parameters_csv(n_clicks: int | None, wid: list[int] | None) -> Any:
        """Export travel parameters to a CSV file.

        This function generates a CSV file containing travel parameters based on the
        provided ruleset. The filename is generated using the current timestamp and
        the name of the time series.

        Parameters
        ----------
        n_clicks : int
            The number of times the export button has been clicked.
        name : list of str
            A list containing the name of the time series.

        Returns
        -------
        dcc.send_string
            A Dash component that triggers the download of the generated CSV file.
        """
        timestr = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        name = well_service.get_well_name(wid).squeeze()
        filename = f"{timestr}_traval_parameters_{name}.csv"
        if qc_service.traval._ruleset is not None:
            ruleset = qc_service.get_resolved_ruleset_for_series(name)
            traval_params = traval.TravalParameters.from_ruleset(ruleset)
            return dcc.send_string(traval_params.to_csv, filename=filename)

    @app.callback(
        Output(ids.QC_COLLAPSE_CONTENT, "is_open"),
        Output(ids.QC_COLLAPSE_BUTTON, "children"),
        Input(ids.QC_COLLAPSE_BUTTON, "n_clicks"),
        State(ids.QC_COLLAPSE_CONTENT, "is_open"),
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def toggle_collapse(n: int | None, is_open: bool) -> tuple[bool, str]:
        """Toggles the collapse state of the parameters form.

        Parameters
        ----------
        n : int or None
            The number of times the button has been clicked.
        is_open : bool
            The current state of the collapse. `True` if the collapse is open,
            `False` otherwise.

        Returns
        -------
        tuple
            A tuple containing the new state of the collapse (`bool`).
        """
        if n:
            if not is_open:
                button_text = [
                    html.I(className="fa-solid fa-chevron-down"),
                    " " + t_("general.hide_parameters"),
                ]
                return not is_open, button_text
            else:
                button_text = [
                    html.I(className="fa-solid fa-chevron-right"),
                    " " + t_("general.show_parameters"),
                ]
                return not is_open, button_text
        # button_text = [
        #     html.I(className="fa-solid fa-chevron-left"),
        #     " Show parameters",
        # ]
        return is_open, no_update

    # @app.callback(
    #     Output(ids.LOADING_QC_CHART_STORE_1, "data"),
    #     Output(ids.RUN_TRAVAL_STORE, "data"),
    #     Input(ids.QC_RUN_TRAVAL_BUTTON, "n_clicks"),
    # )
    # def trigger_traval_run_and_loading_state(n_clicks):
    #     if n_clicks:
    #         return pd.Timestamp.now().isoformat(), n_clicks
    #     else:
    #         raise PreventUpdate

    @app.callback(
        # NOTE: Remove first output for DJANGO
        # Output(ids.QC_CHART, "figure", allow_duplicate=True),
        Output(ids.TRAVAL_RESULT_FIGURE_STORE, "data"),
        Output(ids.TRAVAL_RESULT_TABLE_STORE, "data"),
        Output(ids.QC_DROPDOWN_ADDITIONAL, "value"),
        Output(ids.QC_DROPDOWN_ADDITIONAL_DISABLED_2, "data"),
        Output(ids.ALERT_RUN_TRAVAL, "data"),
        # Output(ids.LOADING_QC_CHART_STORE_2, "data"),
        Input(ids.QC_RUN_TRAVAL_BUTTON, "n_clicks"),
        # Input(ids.RUN_TRAVAL_STORE, "data"),
        State(ids.QC_DROPDOWN_SELECTION, "value"),
        State(ids.QC_DATEPICKER_TMIN, "date"),
        State(ids.QC_DATEPICKER_TMAX, "date"),
        State(ids.QC_RUN_ONLY_UNVALIDATED_CHECKBOX, "value"),
        running=[(Output(ids.LOADING_QC_CHART, "display"), "show", "auto")],
        background=False,
        # NOTE: only used if background is True
        # running=[
        #     (Output(ids.QC_RUN_TRAVAL_BUTTON, "disabled"), True, False),
        #     (Output(ids.QC_CANCEL_BUTTON, "disabled"), False, True),
        # ],
        # cancel=[Input(ids.QC_CANCEL_BUTTON, "n_clicks")],
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def run_traval(
        n_clicks: int | None,
        wid: int | None,
        tmin: str | None,
        tmax: str | None,
        only_unvalidated: list[bool],
    ) -> tuple[tuple[str, dict], dict, None, bool, tuple]:
        """Run the error detection process based on the provided parameters.

        Parameters
        ----------
        n_clicks : int
            The number of clicks to trigger the function.
        wid : int
            The internal id of the time series.
        tmin : float
            The start time.
        tmax : float
            The end time.
        only_unvalidated : bool
            Flag to indicate whether to run the process only on unvalidated data,
            observations with flags ["nogNietBeoordeeld", "onbekend"]

        Returns
        -------
        tuple
            A tuple containing:
            - (name, figure) : tuple
                The name and the resulting figure from the error detection run.
            - result_dict : dict
                The result of the error detection as a dictionary for the table.
            - None : NoneType
                Value in additional dropdown is reset.
            - bool
                Enable or disable dropdown
            - status_tuple : tuple
                A tuple containing:
                - bool : Flag indicating if there was an error.
                - str : Status level ('success' or 'danger').
                - str : Status message.

        Raises
        ------
        PreventUpdate
            If `n_clicks` is not provided, the update is prevented.
        """
        if not n_clicks:
            raise PreventUpdate

        try:
            result, figure = qc_service.run_traval(
                wid,
                tmin=tmin,
                tmax=tmax,
                only_unvalidated=only_unvalidated,
            )
            return (
                CallbackResponse()
                .add((wid, figure))
                .add(result.reset_index().to_dict("records"))
                .add(None)
                .add(True)
                .add(AlertBuilder.success(t_(SuccessMessages.TRAVAL_RUN_SUCCESS)))
                .build()
            )
        except EmptyResultError:
            # send alert all obs are already validated
            logger.warning("All observations are already checked for %s", wid)
            return (
                CallbackResponse()
                .add(no_update)
                .add(no_update)
                .add(None)
                .add(True)
                .add(
                    AlertBuilder.warning(t_(ErrorMessages.QC_ALL_OBSERVATIONS_CHECKED))
                )
                .build()
            )
        except Exception as e:
            logger.error("Error running traval for %s: %s", wid, e, exc_info=True)
            return (
                CallbackResponse()
                .add(no_update)
                .add(no_update)
                .add(None)
                .add(True)
                .add(
                    AlertBuilder.danger(
                        t_(ErrorMessages.QC_ANALYSIS_FAILED, error=str(e))
                    )
                )
                .build()
            )

    @app.callback(
        Output(ids.QC_CHART_STORE_2, "data"),
        # Output(ids.LOADING_QC_CHART_STORE_2, "data"),
        Input(ids.TRAVAL_RESULT_FIGURE_STORE, "data"),
        Input(ids.TRAVAL_RESULT_TABLE_STORE, "data"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def update_traval_figure(figure, table):
        """Update the traval figure and stored traval result table.

        Parameters
        ----------
        figure : tuple or None
            A tuple containing the figure to be updated. If None, no update is
            performed.
        table : list of dict
            The table data to be converted into a DataFrame and used for updating the
            figure.

        Returns
        -------
        tuple
            A tuple containing the updated figure
        """
        if figure is None or table is None:
            return no_update

        df = pd.DataFrame(table).set_index("datetime")
        df.index = pd.to_datetime(df.index)
        qc_service.traval.traval_result = df
        _, figure = figure
        return figure

    @app.callback(
        Output(ids.QC_DROPDOWN_ADDITIONAL, "disabled"),
        Input(ids.QC_DROPDOWN_ADDITIONAL_DISABLED_1, "data"),
        Input(ids.QC_DROPDOWN_ADDITIONAL_DISABLED_2, "data"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def toggle_qc_dropdown_additional(*disabled, **kwargs):
        """Toggles the active state of the QC dropdown.

        Parameters
        ----------
        *disabled : bool
            Variable length argument list of boolean values indicating the disabled
            state of the input.
        **kwargs : dict
            callback_context

        Returns
        -------
        bool
            enable/disable additional dropdown.

        Raises
        ------
        PreventUpdate
            If no inputs are disabled.
        """
        ctx_obj = get_callback_context(**kwargs)
        triggered_id = ctx_obj.triggered_id
        inputs_list = ctx_obj.inputs_list

        if any(disabled):
            idx = _get_trigger_index(triggered_id, inputs_list)
            return disabled[idx]

        raise PreventUpdate

    @app.callback(
        Output(ids.TRAVAL_RULES_FORM, "children"),
        Input(ids.TRAVAL_RULES_FORM_STORE_1, "data"),
        Input(ids.TRAVAL_RULES_FORM_STORE_2, "data"),
        Input(ids.TRAVAL_RULES_FORM_STORE_3, "data"),
        Input(ids.TRAVAL_RULES_FORM_STORE_4, "data"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def update_traval_rules_form(*forms, **kwargs):
        """Updates the travel rules form.

        Parameters
        ----------
        *forms : tuple
            A variable number of form objects.
        **kwargs : dict
            callback_context

        Returns
        -------
        form
            The updated form object if found, otherwise `no_update`.
        """
        ctx_obj = get_callback_context(**kwargs)
        triggered_id = ctx_obj.triggered_id
        inputs_list = ctx_obj.inputs_list

        idx = _get_trigger_index(triggered_id, inputs_list)
        return forms[idx] if forms[idx] is not None else no_update

    @app.callback(
        Output(ids.TRAVAL_RESET_RULESET_BUTTON, "disabled"),
        Input(ids.TRAVAL_RESET_RULESET_BUTTON_STORE_1, "data"),
        Input(ids.TRAVAL_RESET_RULESET_BUTTON_STORE_2, "data"),
        Input(ids.TRAVAL_RESET_RULESET_BUTTON_STORE_3, "data"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def toggle_reset_ruleset_button(*bools, **kwargs):
        """Toggles the reset ruleset button.

        Parameters
        ----------
        *bools : tuple
            boolean arguments indicating whether button should be enabled or disabled.
        **kwargs : dict
            callback_context

        Returns
        -------
        bool
            enable/disable reset ruleset button.

        Raises
        ------
        PreventUpdate
            If none of the boolean values are not None.
        """
        ctx_obj = get_callback_context(**kwargs)
        triggered_id = ctx_obj.triggered_id
        inputs_list = ctx_obj.inputs_list

        if any(boolean is not None for boolean in bools):
            idx = _get_trigger_index(triggered_id, inputs_list)
            return bools[idx]

        raise PreventUpdate

    # @app.callback(
    #     Output(ids.LOADING_QC_CHART, "display"),
    #     Input(ids.LOADING_QC_CHART_STORE_2, "data"),
    #     Input(ids.LOADING_QC_CHART_STORE_1, "data"),
    #     prevent_initial_call=True,
    # )
    # def toggle_chart_loading_state(*states, **kwargs):
    #     if len(kwargs) > 0:
    #         ctx_ = kwargs["callback_context"]
    #         triggered_id = ctx_.triggered[0]["prop_id"].split(".")[0]
    #         inputs_list = ctx_.inputs_list
    #     else:
    #         triggered_id = ctx.triggered_id
    #         inputs_list = ctx.inputs_list
    #     if any(states):
    #         for i in range(len(ctx.inputs_list)):
    #             if inputs_list[i]["id"] == triggered_id:
    #                 break
    #         return "auto" if i == 0 else "show"
    #     else:
    #         raise PreventUpdate

    @app.callback(
        Output(ids.QC_CHART, "figure"),
        Output(ids.LOADING_QC_CHART, "display"),
        Input(ids.QC_CHART_STORE_1, "data"),
        Input(ids.QC_CHART_STORE_2, "data"),
        prevent_initial_call=True,
    )
    @log_callback(
        log_time=ConfigDefaults.CALLBACK_LOG_TIME,
        log_inputs=ConfigDefaults.CALLBACK_LOG_INPUTS,
        log_outputs=ConfigDefaults.CALLBACK_LOG_OUTPUTS,
        log_trigger=ConfigDefaults.CALLBACK_LOG_TRIGGER,
    )
    def display_qc_chart(*figures, **kwargs):
        """Display a QC chart.

        Parameters
        ----------
        *figures : tuple
            figure objects, figure displayed is determined by the component that
            triggers this callback.
        **kwargs : dict
            callback_context

        Returns
        -------
        tuple
            A tuple containing the selected figure and the string "auto" to set the
            loading state of the chart.

        Raises
        ------
        PreventUpdate
            If no figures are provided.
        """
        ctx_obj = get_callback_context(**kwargs)
        triggered_id = ctx_obj.triggered_id
        inputs_list = ctx_obj.inputs_list

        if any(figures):
            idx = _get_trigger_index(triggered_id, inputs_list)
            fig = figures[idx]
            # NOTE: not sure how it can ever become a list, but it sometimes does...
            if isinstance(fig, list):
                fig = fig[0]
            return fig, "auto"

        raise PreventUpdate
