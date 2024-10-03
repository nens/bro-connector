import base64
import io
import pickle
from ast import literal_eval
from copy import deepcopy
from functools import partial
from inspect import signature

import i18n
import pandas as pd
import traval
from dash import (
    ALL,
    MATCH,
    Input,
    Output,
    State,
    ctx,
    dcc,
    html,
    no_update,
)
from dash import __version__ as DASH_VERSION
from dash.exceptions import PreventUpdate
from packaging.version import parse as parse_version
from traval import rulelib

from gwdatalens.app.src.components import ids
from gwdatalens.app.src.components.overview_chart import plot_obs
from gwdatalens.app.src.components.qc_rules_form import (
    derive_form_parameters,
    generate_kwargs_from_func,
    generate_traval_rule_components,
)


# %% TRAVAL TAB
def register_qc_callbacks(app, data):
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
    def update_ruleset_values(val, disabled, **kwargs):
        """Update the values of a ruleset.

        Parameters
        ----------
        val : any
            The new value for a particular rule.
        disabled : bool
            A flag indicating whether the input field is disabled.
        **kwargs : dict
            Additional keyword arguments, including the callback context.

        Returns
        -------
        list or no_update
            Returns a list containing the new value as a string if the update is
            successful, otherwise returns `no_update`.
        """
        if not disabled:
            if len(kwargs) > 0:
                ctx_ = kwargs["callback_context"]
                triggered_id = literal_eval(ctx_.triggered[0]["prop_id"].split(".")[0])
            else:
                triggered_id = ctx.triggered_id
            (idx, rule, param) = triggered_id["index"].split("-")
            ruledict = data.traval._ruleset.get_rule(stepname=rule)
            ruledict["kwargs"][param] = val
            data.traval._ruleset.update_rule(**ruledict)
            return [str(val)]
        else:
            return no_update

    @app.callback(
        Output(ids.QC_CHART_STORE_1, "data"),
        Input(ids.QC_DROPDOWN_SELECTION, "value"),
        Input(ids.QC_DROPDOWN_ADDITIONAL, "value"),
        State(ids.QC_DROPDOWN_ADDITIONAL, "disabled"),
        State(ids.TRAVAL_RESULT_FIGURE_STORE, "data"),
    )
    def plot_qc_time_series(value, additional_values, disabled, traval_figure):
        """Plot time series.

        Parameters
        ----------
        value : str or None
            The primary series to plot. If None, a message indicating no series is
            selected will be returned.
        additional_values : list or None
            Additional series to include in the plot. If None, no additional series
            will be included.
        disabled : bool
            whether to disable the dropdown.
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
            return {"layout": {"title": "No series selected."}}
        elif disabled:
            raise PreventUpdate
        else:
            if data.db.source == "bro":
                name = value.split("-")[0]
            else:
                name = value
            if additional_values is not None:
                additional = additional_values
            else:
                additional = []

            if traval_figure is not None:
                stored_name, figure = traval_figure
                if stored_name == name:
                    return figure

            return plot_obs([name] + additional, data)

    @app.callback(
        Output(ids.QC_DROPDOWN_ADDITIONAL_DISABLED_1, "data"),
        Output(ids.QC_DROPDOWN_ADDITIONAL, "options"),
        Input(ids.QC_DROPDOWN_SELECTION, "value"),
        prevent_initial_call=True,
    )
    def enable_additional_dropdown(value):
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
        if value is not None:
            # value = value.split("-")
            # value[1] = int(value[1])
            locs = data.db.list_locations_sorted_by_distance(value)
            options = [
                {"label": i + f" ({row.distance / 1e3:.1f} km)", "value": i}
                for i, row in locs.iterrows()
            ]
            return False, options
        else:
            return True, no_update

    @app.callback(
        Output(ids.TRAVAL_RULES_FORM_STORE_1, "data"),
        Output(ids.TRAVAL_RESET_RULESET_BUTTON_STORE_1, "data"),
        Input({"type": "clear-button", "index": ALL}, "n_clicks"),
        State({"type": "clear-button", "index": ALL}, "n_clicks"),
        State(ids.TRAVAL_RULES_FORM, "children"),
        prevent_initial_call=True,
    )
    def delete_rule(n_clicks, clickstate, rules, **kwargs):
        """Deletes a rule from the ruleset based on the delete button that was pressed.

        Parameters
        ----------
        n_clicks : list
            List of click counts for the delete buttons.
        clickstate : any
            The state of the clicks, currently not used in the function.
        rules : list
            List of current rules.
        **kwargs : dict
            Additional keyword arguments, expected to contain 'callback_context'.

        Returns
        -------
        tuple
            A tuple containing the updated list of rules and a boolean flag that
            enables/disables the reset button.

        Raises
        ------
        PreventUpdate
            If all values in `n_clicks` are None.
        """
        if all(v is None for v in n_clicks):
            raise PreventUpdate

        if len(kwargs) > 0:
            ctx_ = kwargs["callback_context"]
            triggered_id = literal_eval(ctx_.triggered[0]["prop_id"].split(".")[0])
        else:
            triggered_id = ctx.triggered_id

        keep = []
        for rule in rules:
            if rule["props"]["id"]["index"] != triggered_id["index"]:
                keep.append(rule)
            else:
                data.traval._ruleset.del_rule(triggered_id["index"].split("-")[0])

            data.traval._ruleset.del_rule("combine_results")
            data.traval._ruleset.add_rule(
                "combine_results",
                rulelib.rule_combine_nan_or,
                apply_to=tuple(range(1, len(keep) + 1)),
            )
        return keep, False

    @app.callback(
        Output(ids.TRAVAL_RULES_FORM_STORE_2, "data"),
        Output(ids.TRAVAL_RESET_RULESET_BUTTON_STORE_2, "data"),
        Input(ids.TRAVAL_ADD_RULE_BUTTON, "n_clicks"),
        State(ids.TRAVAL_ADD_RULE_DROPDOWN, "value"),
        State(ids.TRAVAL_RULES_FORM, "children"),
        prevent_initial_call=True,
    )
    def add_rule(n_clicks, rule_to_add, current_rules):
        """Add a new rule to the current set of rules.

        Parameters
        ----------
        n_clicks : int
            The number of clicks, used to trigger the addition of a rule.
        rule_to_add : str
            The name of the rule to add, which should correspond to a function
            in `rulelib`.
        current_rules : list
            The current list of rules, where each rule is a dictionary containing
            rule properties.

        Returns
        -------
        tuple
            A tuple containing the updated list of rules and a boolean flag set to
            False.

        Raises
        ------
        PreventUpdate
            If `n_clicks` is not provided, indicating no action should be taken.
        """
        if n_clicks:
            try:
                rule_number = (
                    int(current_rules[-1]["props"]["id"]["index"].split("-")[-1]) + 1
                )
            except IndexError:
                rule_number = 0
            func = getattr(rulelib, rule_to_add)
            rule = {"name": rule_to_add, "kwargs": generate_kwargs_from_func(func)}
            rule["func"] = func
            # fill function to get manual observations
            if "manual_obs" in signature(func).parameters:
                rule["kwargs"]["manual_obs"] = partial(
                    data.db.get_timeseries,
                    observation_type="controlemeting",
                    column=data.db.value_column,
                )
            irow = generate_traval_rule_components(rule, rule_number)

            # add to ruleset, if multiple rules present ad combine_results at the end
            if len(current_rules) > 1:
                # remove combine results first if a rule is added
                try:
                    data.traval._ruleset.del_rule("combine_results")
                except KeyError:
                    # no rule combine results, so pass
                    pass
                data.traval._ruleset.add_rule(
                    rule["name"], func, apply_to=0, kwargs=rule["kwargs"]
                )
                data.traval._ruleset.add_rule(
                    "combine_results",
                    rulelib.rule_combine_nan_or,
                    apply_to=tuple(range(1, len(current_rules) + 1)),
                )
            else:
                # remove combine results first if a rule is added
                try:
                    data.traval._ruleset.del_rule("combine_results")
                except KeyError:
                    # no rule combine results, so pass
                    pass
                data.traval._ruleset.add_rule(
                    rule["name"], func, apply_to=0, kwargs=rule["kwargs"]
                )
            current_rules.append(irow)
            return current_rules, False
        else:
            raise PreventUpdate

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
    def display_rules_for_series(name):
        """Display rules for a given series name.

        Parameters
        ----------
        name : str
            The name of the series for which to display rules.

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
        nrules = len(data.traval._ruleset.rules) - 1
        errors = []

        for i in range(1, nrules + 1):
            irule = data.traval._ruleset.get_rule(istep=i)
            for k, v in irule["kwargs"].items():
                if callable(v):
                    if name is not None:
                        try:
                            v = v(name)
                        except Exception as e:
                            errors.append((f"{irule['name']}: {k}", e))

                v, input_type, disabled, step = derive_form_parameters(v)
                tooltips.append(str(v))
                values.append(v)
                input_types.append(input_type)
                disableds.append(disabled)
                steps.append(step)
        if len(errors) > 0:
            return (
                values,
                input_types,
                disableds,
                steps,
                tooltips,
                False,
                (
                    True,
                    "danger",
                    f"Error! Could not load parameter(s) for: {[e[0] for e in errors]}",
                ),
            )
        else:
            return (
                values,
                input_types,
                disableds,
                steps,
                tooltips,
                False,
                (False, None, None),
            )

    @app.callback(
        Output(ids.TRAVAL_RULES_FORM_STORE_3, "data"),
        Input(ids.TRAVAL_RESET_RULESET_BUTTON, "n_clicks"),
        State(ids.QC_DROPDOWN_SELECTION, "value"),
        prevent_initial_call=True,
    )
    def reset_ruleset_to_current_default(n_clicks, name):
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
        if n_clicks is not None:
            form_components = []
            nrules = len(data.traval.ruleset.rules) - 1

            # reset ruleset to original version
            data.traval._ruleset = deepcopy(data.traval.ruleset)

            idx = 0
            for i in range(1, nrules + 1):
                irule = data.traval.ruleset.get_rule(istep=i)
                irow = generate_traval_rule_components(irule, idx, series_name=name)
                form_components.append(irow)
                idx += 1
            return form_components
        else:
            raise PreventUpdate

    @app.callback(
        Output(ids.TRAVAL_ADD_RULE_BUTTON, "disabled"),
        Input(ids.TRAVAL_ADD_RULE_DROPDOWN, "value"),
    )
    def activate_add_rule_button(value):
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
    def load_ruleset(contents):
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
        if contents is not None:
            try:
                content_type, content_string = contents.split(",")
                decoded = base64.b64decode(content_string)
                rules = pickle.load(io.BytesIO(decoded))

                ruleset = traval.RuleSet(name=rules.pop("name"))
                ruleset.rules.update(rules)

                # data.traval.ruleset = ruleset
                data.traval._ruleset = ruleset

                nrules = len(data.traval._ruleset.rules) - 1
                form_components = []
                idx = 0
                for i in range(1, nrules + 1):
                    irule = data.traval._ruleset.get_rule(istep=i)
                    irow = generate_traval_rule_components(irule, idx)
                    form_components.append(irow)
                    idx += 1

                return form_components, (True, "success", "Loaded ruleset")
            except Exception as e:
                return no_update, (True, "warning", f"Could not load ruleset: {e}")
        elif contents is None:
            raise PreventUpdate

    @app.callback(
        Output(ids.DOWNLOAD_TRAVAL_RULESET, "data"),
        Input(ids.TRAVAL_EXPORT_RULESET_BUTTON, "n_clicks"),
        State(ids.SELECTED_OSERIES_STORE, "data"),
        prevent_initial_call=True,
    )
    def export_ruleset(n_clicks, name):
        """Export the current ruleset to a pickle file.

        Parameters
        ----------
        n_clicks : int
            The number of times the export button has been clicked. Used to trigger
            function.
        name : list of str
            A list containing the name of the ruleset to be exported.

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
        filename = f"{timestr}_traval_ruleset_{name[0]}.pickle"
        if data.traval._ruleset is not None:
            ruleset = data.traval._ruleset.get_resolved_ruleset(name)
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
    def export_parameters_csv(n_clicks, name):
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
        filename = f"{timestr}_traval_parameters_{name[0]}.csv"
        if data.traval._ruleset is not None:
            ruleset = data.traval._ruleset.get_resolved_ruleset(name)
            traval_params = traval.TravalParameters.from_ruleset(ruleset)
            return dcc.send_string(traval_params.to_csv, filename=filename)

    @app.callback(
        Output(ids.QC_COLLAPSE_CONTENT, "is_open"),
        Output(ids.QC_COLLAPSE_BUTTON, "children"),
        Input(ids.QC_COLLAPSE_BUTTON, "n_clicks"),
        State(ids.QC_COLLAPSE_CONTENT, "is_open"),
    )
    def toggle_collapse(n, is_open):
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
                    " " + i18n.t("general.hide_parameters"),
                ]
                return not is_open, button_text
            else:
                button_text = [
                    html.I(className="fa-solid fa-chevron-right"),
                    " " + i18n.t("general.show_parameters"),
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
    def run_traval(n_clicks, name, tmin, tmax, only_unvalidated):
        """Run the error detection process based on the provided parameters.

        Parameters
        ----------
        n_clicks : int
            The number of clicks to trigger the function.
        name : str
            The name identifier in the format "gmw_id-tube_id".
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
        if n_clicks:
            if parse_version(DASH_VERSION) >= parse_version("2.17.0"):
                from dash import set_props

                set_props(ids.LOADING_QC_CHART, {"display": "show"})

            gmw_id, tube_id = name.split("-")
            try:
                result, figure = data.traval.run_traval(
                    gmw_id,
                    tube_id,
                    tmin=tmin,
                    tmax=tmax,
                    only_unvalidated=only_unvalidated,
                )
                return (
                    # {"layout": {"title": "Running TRAVAL..."}},  # figure
                    (name, figure),
                    result.reset_index().to_dict("records"),
                    None,
                    True,
                    # "auto"
                    (
                        False,
                        "success",
                        "Traval run succesful",
                    ),
                )
            except Exception as e:
                return (
                    # {"layout": {"title": "Running TRAVAL..."}},  # figure
                    no_update,
                    no_update,
                    None,
                    True,
                    # "auto"
                    (
                        True,
                        "danger",
                        f"Error: {e}",
                    ),
                )
        else:
            raise PreventUpdate

    @app.callback(
        Output(ids.QC_CHART_STORE_2, "data"),
        # Output(ids.LOADING_QC_CHART_STORE_2, "data"),
        Input(ids.TRAVAL_RESULT_FIGURE_STORE, "data"),
        Input(ids.TRAVAL_RESULT_TABLE_STORE, "data"),
        prevent_initial_call=True,
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
        if figure is not None:
            # set result table
            df = pd.DataFrame(table).set_index("datetime")
            df.index = pd.to_datetime(df.index)
            data.traval.traval_result = df
            _, figure = figure
            return (
                figure,
                # "hide",
            )
        else:
            return (
                no_update,
                # "hide",
            )

    @app.callback(
        Output(ids.QC_DROPDOWN_ADDITIONAL, "disabled"),
        Input(ids.QC_DROPDOWN_ADDITIONAL_DISABLED_1, "data"),
        Input(ids.QC_DROPDOWN_ADDITIONAL_DISABLED_2, "data"),
        prevent_initial_call=True,
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
        if len(kwargs) > 0:
            ctx_ = kwargs["callback_context"]
            triggered_id = ctx_.triggered[0]["prop_id"].split(".")[0]
            inputs_list = ctx_.inputs_list
        else:
            triggered_id = ctx.triggered_id
            inputs_list = ctx.inputs_list

        if any(disabled):
            for i in range(len(inputs_list)):
                if inputs_list[i]["id"] == triggered_id:
                    break
            return disabled[i]
        else:
            raise PreventUpdate

    @app.callback(
        Output(ids.TRAVAL_RULES_FORM, "children"),
        Input(ids.TRAVAL_RULES_FORM_STORE_1, "data"),
        Input(ids.TRAVAL_RULES_FORM_STORE_2, "data"),
        Input(ids.TRAVAL_RULES_FORM_STORE_3, "data"),
        Input(ids.TRAVAL_RULES_FORM_STORE_4, "data"),
        prevent_initial_call=True,
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
        if len(kwargs) > 0:
            ctx_ = kwargs["callback_context"]
            triggered_id = ctx_.triggered[0]["prop_id"].split(".")[0]
            inputs_list = ctx_.inputs_list
        else:
            triggered_id = ctx.triggered_id
            inputs_list = ctx.inputs_list

        for i in range(len(inputs_list)):
            if inputs_list[i]["id"] == triggered_id:
                break
        return forms[i] if forms[i] is not None else no_update

    @app.callback(
        Output(ids.TRAVAL_RESET_RULESET_BUTTON, "disabled"),
        Input(ids.TRAVAL_RESET_RULESET_BUTTON_STORE_1, "data"),
        Input(ids.TRAVAL_RESET_RULESET_BUTTON_STORE_2, "data"),
        Input(ids.TRAVAL_RESET_RULESET_BUTTON_STORE_3, "data"),
        prevent_initial_call=True,
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
        if len(kwargs) > 0:
            ctx_ = kwargs["callback_context"]
            triggered_id = ctx_.triggered[0]["prop_id"].split(".")[0]
            inputs_list = ctx_.inputs_list
        else:
            triggered_id = ctx.triggered_id
            inputs_list = ctx.inputs_list

        if any(boolean is not None for boolean in bools):
            for i in range(len(inputs_list)):
                if inputs_list[i]["id"] == triggered_id:
                    break
            return bools[i]
        else:
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
        if len(kwargs) > 0:
            ctx_ = kwargs["callback_context"]
            triggered_id = ctx_.triggered[0]["prop_id"].split(".")[0]
            inputs_list = ctx_.inputs_list
        else:
            triggered_id = ctx.triggered_id
            inputs_list = ctx.inputs_list

        if any(figures):
            for i in range(len(inputs_list)):
                if inputs_list[i]["id"] == triggered_id:
                    break
            fig = figures[i]
            # NOTE: not sure how it can ever become a list, but it sometimes does...
            if isinstance(fig, list):
                fig = fig[0]
            return fig, "auto"
        else:
            raise PreventUpdate
