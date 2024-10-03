from inspect import signature

import dash_bootstrap_components as dbc
import numpy as np
from dash import html

from gwdatalens.app.settings import settings

from ..data import DataInterface
from . import ids

if settings["LOCALE"] == "en":
    from ..data.qc_definitions import rule_explanation_en as rule_explanation
elif settings["LOCALE"] == "nl":
    from ..data.qc_definitions import rule_explanation_nl as rule_explanation


def generate_kwargs_from_func(func):
    """Generate a dictionary of keyword arguments and their default values for a func.

    Parameters
    ----------
    func : function
        The function from which to extract keyword arguments and their default values.

    Returns
    -------
    dict
        A dictionary where the keys are the names of the keyword arguments and the
        values are their default values.
    """
    sig = signature(func)
    kwargs = {}
    for k, v in sig.parameters.items():
        if v.default != v.empty:
            kwargs[k] = v.default
    return kwargs


def derive_form_parameters(v):
    """Derive form parameters based on the type and value of the input.

    Parameters
    ----------
    v : any
        The input value to derive form parameters from. It can be of any type including
        tuple, callable, float, int, np.integer, str, or other types.

    Returns
    -------
    v : str or int
        The processed value, converted to a string if necessary.
    input_type : str
        The type of input, either "text" or "number".
    disabled : bool
        A flag indicating whether the input should be disabled.
    step : float or int or str or None
        The step value for numeric inputs, or "any" for text inputs, or None if
        not applicable.

    Notes
    -----
    - If `v` is a tuple and the first element is callable, the input is disabled
      and converted to a string.
    - If `v` is callable, the input is disabled and converted to a string.
    - If `v` is a float, the input type is "number" and the step is calculated based
      on the number of decimals.
    - If `v` is an integer, the input type is "number" and the step is calculated based
      on the magnitude of the value.
    - If `v` is a string, the input type is "text" and the step is set to "any".
    - For other types, the input is disabled and converted to a string.
    """
    input_type = "text"
    disabled = False
    ndecimals = None
    step = None

    if isinstance(v, tuple) and callable(v[0]):
        input_type = "text"
        disabled = True
        v = str(v)
    elif callable(v):
        v = str(v)
        disabled = True
        input_type = "text"
    elif isinstance(v, float):
        input_type = "number"
        # step = np.min([10 ** np.floor(np.log10(v)) / 2, 10])
        vstr = str(v % 1)
        ndecimals = len(vstr) - vstr.find(".") - 1
        step = 10 ** (-ndecimals) / 2
    elif isinstance(v, (int, np.integer)):
        input_type = "number"
        step = int(np.min([10 ** np.floor(np.log10(v)), 10]))
        if isinstance(v, bool):
            v = int(v)
    elif isinstance(v, str):
        input_type = "text"
        step = "any"
        disabled = False
    else:
        input_type = "text"
        step = None
        v = str(v)
        disabled = True

    return v, input_type, disabled, step


def generate_traval_rule_components(rule, rule_number, series_name=None):
    """Generate components for a travel rule form.

    Parameters
    ----------
    rule : dict
        A dictionary containing rule details. Expected keys are:
        - "name": str, the name of the rule.
        - "func": callable, the function associated with the rule.
        - "kwargs": dict, additional parameters for the rule.
    rule_number : int
        The number of the rule in the sequence.
    series_name : str, optional
        The name of the series, if applicable.

    Returns
    -------
    dbc.Row
        A Dash Bootstrap Component (dbc) Row containing the generated components for
        the rule.
    """
    name = rule["name"]
    ibtn = dbc.Button(
        html.Span(
            [html.I(className="fa-solid fa-x")],
            n_clicks=0,
        ),
        id={"type": "clear-button", "index": f"{name}-{rule_number}"},
        size="sm",
        style={
            "background-color": "darkred",
            "fontSize": "small",
            # "padding": 1,
            "height": "30px",
            "width": "30px",
        },
        type="button",
    )
    lbl = dbc.Label(name, width=1)
    info = dbc.Button(
        html.Span(
            [html.I(className="fa-solid fa-info")],
            id="span-info-button",
            n_clicks=0,
        ),
        style={
            "fontSize": "small",
            "background-color": "#006f92",
            # "padding": 1,
            "height": "30px",
            "width": "30px",
            # "border": None,
            "border-radius": "50%",
            "padding": 0,
            "textAlign": "center",
            "display": "block",
        },
        id={"type": "info-button", "index": f"{name}-{rule_number}"},
    )
    tooltip = dbc.Tooltip(
        children=[
            html.P(f"{name}", style={"margin-bottom": 0}),
            html.P(
                rule_explanation[rule["func"].__name__],
                style={"margin-top": 0, "margin-bottom": 0},
            ),
        ],
        target={"type": "info-button", "index": f"{name}-{rule_number}"},
        placement="right",
    )
    row_components = [ibtn, lbl, info, tooltip]
    idx = rule_number  # input_field_no
    for k, v in rule["kwargs"].items():
        if callable(v):
            if series_name is not None:
                try:
                    v = v(series_name)
                except Exception as _:
                    print(f"Parameter '{rule['name']}: {k}' not defined.")
                    pass
        v, input_type, disabled, step = derive_form_parameters(v)

        ilbl = dbc.Label(k, width=1)
        param_input = []
        param_input.append(
            dbc.Input(
                id={"type": "rule_input", "index": f"{idx}-{name}-{k}"},
                step=step,
                type=input_type,
                placeholder=str(type(v).__name__),
                value=v,
                disabled=disabled,
                size="sm",
                debounce=True,
            )
        )
        param_input.append(
            dbc.Tooltip(
                html.P(
                    v,
                    style={"margin-top": 0, "margin-bottom": 0},
                    id={
                        "type": "rule_input_tooltip",
                        "index": f"{idx}-{name}-{k}",
                    },
                ),
                target={"type": "rule_input", "index": f"{idx}-{name}-{k}"},
                placement="right",
            )
        )
        param = dbc.Col(
            param_input,
            className="me-3",
            width=1,
        )
        row_components += [ilbl, param]
        idx += 1

    irow = dbc.Row(
        row_components,
        className="g-3",
        id={"type": "rule_row", "index": f"{name}-{rule_number}"},
    )
    return irow


def render_traval_form(data: DataInterface, series_name=None):
    """Render a form for displaying and editing TRAVAL rules.

    Parameters
    ----------
    data : DataInterface
        An instance of DataInterface containing the TRAVAL ruleset.
    series_name : str, optional
        The name of the series to which the rules apply, by default None.

    Returns
    -------
    dbc.Form
        A Dash Bootstrap Component form populated with TRAVAL rule components.
    """
    form_components = []
    nrules = len(data.traval._ruleset.rules) - 1

    # reset ruleset to original version
    # data.traval._ruleset = deepcopy(data.traval.ruleset)

    idx = 0
    for i in range(1, nrules + 1):
        irule = data.traval._ruleset.get_rule(istep=i)
        irow = generate_traval_rule_components(irule, idx, series_name=series_name)
        form_components.append(irow)
        idx += 1

    form = dbc.Form(id=ids.TRAVAL_RULES_FORM, children=form_components)
    return form
