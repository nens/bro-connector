import base64
import io
import pickle
from copy import deepcopy

import i18n
import pandas as pd
import traval
from dash import ALL, Input, Output, Patch, State, ctx, dcc, html, no_update, MATCH
from dash.exceptions import PreventUpdate
from ..src.components.qc_rules_form import (
    derive_form_parameters,
    generate_kwargs_from_func,
    generate_traval_rule_components,
)
from traval import rulelib

from ..src.components import ids
from ..src.components.overview_chart import plot_obs


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
    def update_ruleset_values(val, disabled):
        if not disabled:
            (idx, rule, param) = ctx.triggered_id["index"].split("-")
            ruledict = data.traval._ruleset.get_rule(stepname=rule)
            ruledict["kwargs"][param] = val
            data.traval._ruleset.update_rule(**ruledict)
            return [str(val)]
        else:
            return no_update

    # @app.callback(
    #     Output(ids.TRAVAL_OUTPUT, "children", allow_duplicate=True),
    #     Input(ids.TRAVAL_RULES_FORM, "children"),
    #     prevent_initial_call=True,
    # )
    # def update_ruleset(rules):
    #     return data.traval._ruleset.to_json()

    @app.callback(
        Output(ids.QC_CHART, "figure"),
        Input(ids.QC_DROPDOWN_SELECTION, "value"),
        Input(ids.QC_DROPDOWN_ADDITIONAL, "value"),
        State(ids.QC_DROPDOWN_ADDITIONAL, "disabled"),
    )
    def plot_qc_time_series(value, additional_values, disabled):
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
            return plot_obs([name] + additional, data)

    @app.callback(
        Output(ids.QC_DROPDOWN_ADDITIONAL, "disabled", allow_duplicate=True),
        Output(ids.QC_DROPDOWN_ADDITIONAL, "options"),
        Input(ids.QC_DROPDOWN_SELECTION, "value"),
        prevent_initial_call=True,
    )
    def enable_additional_dropdown(value):
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
        Output(ids.TRAVAL_RULES_FORM, "children", allow_duplicate=True),
        Output(ids.TRAVAL_RESET_RULESET_BUTTON, "disabled", allow_duplicate=True),
        Input({"type": "clear-button", "index": ALL}, "n_clicks"),
        State(ids.TRAVAL_RULES_FORM, "children"),
        prevent_initial_call=True,
    )
    def delete_rule(n_clicks, rules):
        if all(v is None for v in n_clicks):
            raise PreventUpdate
        keep = []
        for rule in rules:
            if rule["props"]["id"]["index"] != ctx.triggered_id["index"]:
                keep.append(rule)
            else:
                data.traval._ruleset.del_rule(ctx.triggered_id["index"].split("-")[0])

            data.traval._ruleset.del_rule("combine_results")
            data.traval._ruleset.add_rule(
                "combine_results",
                rulelib.rule_combine_nan_or,
                apply_to=tuple(range(1, len(keep) + 1)),
            )
        return keep, False

    @app.callback(
        Output(ids.TRAVAL_RULES_FORM, "children", allow_duplicate=True),
        Output(ids.TRAVAL_RESET_RULESET_BUTTON, "disabled", allow_duplicate=True),
        Input(ids.TRAVAL_ADD_RULE_BUTTON, "n_clicks"),
        State(ids.TRAVAL_ADD_RULE_DROPDOWN, "value"),
        State(ids.TRAVAL_RULES_FORM, "children"),
        prevent_initial_call=True,
    )
    def add_rule(n_clicks, rule_to_add, current_rules):
        try:
            rule_number = (
                int(current_rules[-1]["props"]["id"]["index"].split("-")[-1]) + 1
            )
        except IndexError:
            rule_number = 0

        func = getattr(rulelib, rule_to_add)
        rule = {"name": rule_to_add, "kwargs": generate_kwargs_from_func(func)}
        irow = generate_traval_rule_components(rule, rule_number)

        # add to ruleset
        data.traval._ruleset.del_rule("combine_results")
        data.traval._ruleset.add_rule(
            rule["name"], func, apply_to=0, kwargs=rule["kwargs"]
        )
        data.traval._ruleset.add_rule(
            "combine_results",
            rulelib.rule_combine_nan_or,
            apply_to=tuple(range(1, len(current_rules) + 1)),
        )

        patched_children = Patch()
        patched_children.append(irow)
        return patched_children, False

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
        Output(ids.TRAVAL_RESET_RULESET_BUTTON, "disabled", allow_duplicate=True),
        Output(ids.ALERT, "is_open", allow_duplicate=True),
        Output(ids.ALERT, "color", allow_duplicate=True),
        Output(ids.ALERT_BODY, "children", allow_duplicate=True),
        Input(ids.QC_DROPDOWN_SELECTION, "value"),
        prevent_initial_call=True,
    )
    def display_rules_for_series(name):
        # reset ruleset to original version
        # data.traval._ruleset = deepcopy(data.traval.ruleset)

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
                True,
                "danger",
                f"Error! Could not load parameter(s) for: {[e[0] for e in errors]}",
            )
        else:
            return (
                values,
                input_types,
                disableds,
                steps,
                tooltips,
                False,
                False,
                None,
                None,
            )

    @app.callback(
        Output(ids.TRAVAL_RULES_FORM, "children", allow_duplicate=True),
        Input(ids.TRAVAL_RESET_RULESET_BUTTON, "n_clicks"),
        State(ids.QC_DROPDOWN_SELECTION, "value"),
        prevent_initial_call=True,
    )
    def reset_ruleset_to_current_default(n_clicks, name):
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

    @app.callback(
        Output(ids.TRAVAL_ADD_RULE_BUTTON, "disabled"),
        Input(ids.TRAVAL_ADD_RULE_DROPDOWN, "value"),
    )
    def activate_add_rule_button(value):
        if value is not None:
            return False
        return True

    @app.callback(
        Output(ids.TRAVAL_RULES_FORM, "children", allow_duplicate=True),
        Output(ids.ALERT, "is_open", allow_duplicate=True),
        Output(ids.ALERT, "color", allow_duplicate=True),
        Output(ids.ALERT_BODY, "children", allow_duplicate=True),
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

                data.traval.ruleset = ruleset
                data.traval._ruleset = ruleset

                nrules = len(data.traval._ruleset.rules) - 1
                form_components = []
                idx = 0
                for i in range(1, nrules + 1):
                    irule = data.traval._ruleset.get_rule(istep=i)
                    irow = generate_traval_rule_components(irule, idx)
                    form_components.append(irow)
                    idx += 1

                return form_components, True, "success", "Loaded ruleset"
            except Exception as e:
                return no_update, True, "warning", f"Could not load ruleset: {e}"
        elif contents is None:
            raise PreventUpdate

    @app.callback(
        Output(ids.DOWNLOAD_TRAVAL_RULESET, "data"),
        Input(ids.TRAVAL_EXPORT_RULESET_BUTTON, "n_clicks"),
        State(ids.SELECTED_OSERIES_STORE, "data"),
        prevent_initial_call=True,
    )
    def export_ruleset(n_clicks, name):
        timestr = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestr}_traval_ruleset_{name[0]}.pickle"
        if data.traval._ruleset is not None:
            ruleset = data.traval._ruleset.get_resolved_ruleset(name)

            def to_pickle(f):
                """Version of to_pickle that works with dcc Download component."""
                ruleset["name"] = name
                pickle.dump(ruleset, f)

            return dcc.send_bytes(to_pickle, filename=filename)

    @app.callback(
        Output(ids.DOWNLOAD_TRAVAL_PARAMETERS_CSV, "data"),
        Input(ids.TRAVAL_EXPORT_PARAMETERS_CSV_BUTTON, "n_clicks"),
        State(ids.SELECTED_OSERIES_STORE, "data"),
        prevent_initial_call=True,
    )
    def export_parameters_csv(n_clicks, name):
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

    @app.callback(
        # Output(ids.QC_RESULT_TABLE, "data"),
        Output(ids.QC_CHART, "figure", allow_duplicate=True),
        Output(ids.TRAVAL_RESULT_FIGURE_STORE, "data"),
        Output(ids.TRAVAL_RESULT_TABLE_STORE, "data"),
        Output(ids.QC_DROPDOWN_ADDITIONAL, "value"),
        Output(ids.QC_DROPDOWN_ADDITIONAL, "disabled", allow_duplicate=True),
        Input(ids.QC_RUN_TRAVAL_BUTTON, "n_clicks"),
        State(ids.QC_DROPDOWN_SELECTION, "value"),
        State(ids.QC_DATEPICKER_TMIN, "date"),
        State(ids.QC_DATEPICKER_TMAX, "date"),
        State(ids.QC_RUN_ONLY_UNVALIDATED_CHECKBOX, "value"),
        background=True,
        running=[
            (Output(ids.QC_RUN_TRAVAL_BUTTON, "disabled"), True, False),
            (Output(ids.QC_CANCEL_BUTTON, "disabled"), False, True),
        ],
        cancel=[Input(ids.QC_CANCEL_BUTTON, "n_clicks")],
        prevent_initial_call=True,
    )
    def run_traval(n_clicks, name, tmin, tmax, only_unvalidated):
        if n_clicks:
            gmw_id, tube_id = name.split("-")
            result, figure = data.traval.run_traval(
                gmw_id, tube_id, tmin=tmin, tmax=tmax, only_unvalidated=only_unvalidated
            )
            # NOTE: it would be prettier to return the figure once, and somehow trigger
            # the loading state of the figure
            return (
                figure,
                figure,
                result.reset_index().to_dict("records"),
                None,
                True,
            )
        else:
            raise PreventUpdate

    @app.callback(
        Output(ids.QC_CHART, "figure", allow_duplicate=True),
        Input(ids.TRAVAL_RESULT_FIGURE_STORE, "data"),
        Input(ids.TRAVAL_RESULT_TABLE_STORE, "data"),
        prevent_initial_call=True,
    )
    def update_traval_figure(figure, table):
        if figure is not None:
            # set result table
            df = pd.DataFrame(table).set_index("datetime")
            df.index = pd.to_datetime(df.index)
            data.traval.traval_result = df
            return figure
        else:
            # data.traval.traval_result = None
            return no_update
