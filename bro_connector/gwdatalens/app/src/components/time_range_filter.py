"""Global time-range filter component.

Renders a compact, persistent filter bar that appears in the app header and
controls how much historical data is loaded from the database.  The selected
range is persisted in a ``dcc.Store`` (``ids.TIME_RANGE_STORE``) so that all
tabs share the same window without duplicating state.

Store schema
------------
The ``TIME_RANGE_STORE`` holds a plain dict::

    {
        "preset": "last_2_years",   # key in TimeRangeDefaults.PRESETS
        "tmin": "2024-01-01",       # ISO-8601 string or None
        "tmax": None,               # ISO-8601 string or None
    }

When ``preset`` is ``"custom"`` the ``tmin``/``tmax`` values supplied by the
user date pickers are used directly.  For all other presets ``tmin`` is
computed from today's date and the corresponding pandas offset and ``tmax``
is always ``None`` (load up to the most recent measurement).
When ``preset`` is ``"all"`` both ``tmin`` and ``tmax`` are ``None``.
"""

from __future__ import annotations

import dash_bootstrap_components as dbc  # noqa: I001
import pandas as pd
from dash import dcc, html
from gwdatalens.app.constants import TimeRangeDefaults
from gwdatalens.app.messages import t_
from gwdatalens.app.src.components import ids

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def preset_to_tmin(preset: str) -> str | None:
    """Compute the *tmin* ISO-8601 string for a given preset key.

    Parameters
    ----------
    preset : str
        One of the keys in :attr:`TimeRangeDefaults.PRESETS`.

    Returns
    -------
    str or None
        ISO-8601 date string, or ``None`` when the preset has no lower bound
        (i.e. ``"all"``).
    """
    if preset not in TimeRangeDefaults.PRESETS:
        return None
    _, offset = TimeRangeDefaults.PRESETS[preset]
    if offset is None:
        return None
    today = pd.Timestamp.now().normalize()
    tmin_ts = today - pd.tseries.frequencies.to_offset(offset)
    return tmin_ts.strftime("%Y-%m-%d")


def build_time_range_store_value(
    preset: str,
    custom_tmin: str | None = None,
    custom_tmax: str | None = None,
) -> dict:
    """Build the dict that is stored in ``TIME_RANGE_STORE``.

    Parameters
    ----------
    preset : str
        Preset key, e.g. ``"last_2_years"``.
    custom_tmin : str or None
        Used only when ``preset == "custom"``.
    custom_tmax : str or None
        Used only when ``preset == "custom"``.

    Returns
    -------
    dict
        ``{"preset": ..., "tmin": ..., "tmax": ...}``
    """
    if preset == "custom":
        return {"preset": "custom", "tmin": custom_tmin, "tmax": custom_tmax}
    tmin = preset_to_tmin(preset)
    return {"preset": preset, "tmin": tmin, "tmax": None}


def default_store_value() -> dict:
    """Return the default store value based on ``TimeRangeDefaults.DEFAULT_PRESET``."""
    return build_time_range_store_value(TimeRangeDefaults.DEFAULT_PRESET)


# ---------------------------------------------------------------------------
# Component factory
# ---------------------------------------------------------------------------


def render_time_range_filter() -> html.Div:
    """Render the global time-range filter bar.

    Returns a compact row with:
    - A preset dropdown (last month / 3 m / year / 2 years / 5 years / custom / all)
    - Two date-pickers for custom *tmin* / *tmax* (hidden unless "custom" is selected)
    - An "Apply" button

    The component is intended to be placed in the app header so it persists
    across all tab switches.

    Returns
    -------
    html.Div
        Dash layout subtree for the time-range filter.
    """
    preset_options = [
        {"label": t_(label_key), "value": key}
        for key, (label_key, _) in TimeRangeDefaults.PRESETS.items()
    ]
    default_preset = TimeRangeDefaults.DEFAULT_PRESET
    show_apply_button = default_preset == "custom"

    return html.Div(
        id="time-range-filter-container",
        className="d-flex align-items-center gap-2",
        children=[
            html.Label(
                t_("general.time_range_filter_label"),
                className="form-label mb-0",
                style={"font-weight": "600", "white-space": "nowrap"},
            ),
            dcc.Dropdown(
                id=ids.TIME_RANGE_PRESET_DROPDOWN,
                options=preset_options,
                value=default_preset,
                clearable=False,
                maxHeight=320,
                style={"min-width": "160px", "font-size": "0.85rem"},
            ),
            # Custom date pickers — hidden by default, shown when preset=="custom"
            html.Div(
                dcc.DatePickerSingle(
                    id=ids.TIME_RANGE_TMIN_DATEPICKER,
                    placeholder=t_("general.time_range_from"),
                    display_format="YYYY-MM-DD",
                    show_outside_days=True,
                    day_size=28,
                ),
                id="time-range-tmin-col",
                style={"display": "none"},
            ),
            html.Div(
                dcc.DatePickerSingle(
                    id=ids.TIME_RANGE_TMAX_DATEPICKER,
                    placeholder=t_("general.time_range_to"),
                    display_format="YYYY-MM-DD",
                    show_outside_days=True,
                    day_size=28,
                ),
                id="time-range-tmax-col",
                style={"display": "none"},
            ),
            dbc.Button(
                t_("general.time_range_apply"),
                id=ids.TIME_RANGE_APPLY_BUTTON,
                color="primary",
                style={"display": "block" if show_apply_button else "none"},
            ),
        ],
    )
