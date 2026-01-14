"""Callback helper utilities.

Common patterns and utilities for Dash callbacks to reduce
boilerplate and improve consistency.
"""

import logging
from functools import wraps
from typing import Any, Callable, Optional, Tuple

import pandas as pd
from dash.exceptions import PreventUpdate

from gwdatalens.app.config import config
from gwdatalens.app.messages import ErrorMessages, t_

logger = logging.getLogger(__name__)


def prevent_update_if_none(*args):
    """Decorator to prevent callback update if any arg is None.

    Usage:
        @prevent_update_if_none
        def my_callback(value, other_value):
            # Only runs if both values are not None
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*callback_args, **callback_kwargs):
            # Check the actual arguments passed (not decorator args)
            for arg in callback_args:
                if arg is None:
                    raise PreventUpdate
            return func(*callback_args, **callback_kwargs)

        return wrapper

    return decorator


def handle_callback_errors(
    default_return: Any = None, log_error: bool = True
) -> Callable:
    """Decorator to handle callback errors gracefully.

    Parameters
    ----------
    default_return : Any
        Value to return on error
    log_error : bool
        Whether to log the error

    Usage:
        @handle_callback_errors(default_return=(no_update, no_update))
        def my_callback(value):
            # Errors caught and logged
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            # generic exception for catching all callback errors
            except Exception as e:
                if log_error:
                    logger.exception("Error in callback %s: %s", func.__name__, e)
                return default_return

        return wrapper

    return decorator


class AlertBuilder:
    """Builder for alert tuple responses.

    Standardizes alert return format across callbacks.
    """

    @staticmethod
    def success(message: str) -> Tuple[bool, str, str]:
        """Create success alert.

        Returns
        -------
        tuple
            (show=True, type="success", message)
        """
        return (True, "success", message)

    @staticmethod
    def warning(message: str) -> Tuple[bool, str, str]:
        """Create warning alert.

        Returns
        -------
        tuple
            (show=True, type="warning", message)
        """
        return (True, "warning", message)

    @staticmethod
    def danger(message: str) -> Tuple[bool, str, str]:
        """Create danger/error alert.

        Returns
        -------
        tuple
            (show=True, type="danger", message)
        """
        return (True, "danger", message)

    @staticmethod
    def no_alert() -> Tuple[bool, None, None]:
        """Create no-alert response.

        Returns
        -------
        tuple
            (show=False, None, None)
        """
        return (False, None, None)


class TimestampStore:
    """Helper for timestamp-based store updates.

    Used to trigger updates in Dash stores.
    """

    @staticmethod
    def create(success: bool = True) -> Tuple[str, bool]:
        """Create timestamp store data.

        Parameters
        ----------
        success : bool
            Success flag

        Returns
        -------
        tuple
            (timestamp_iso, success)
        """
        return (pd.Timestamp.now().isoformat(), success)


class EmptyFigure:
    """Helper for creating empty placeholder figures."""

    @staticmethod
    def with_message(message: str) -> dict:
        """Create empty figure with a message.

        Parameters
        ----------
        message : str
            Message to display

        Returns
        -------
        dict
            Plotly figure dict
        """
        return {"layout": {"title": {"text": message}}}

    @staticmethod
    def no_selection() -> dict:
        """Figure for no selection state."""
        return EmptyFigure.with_message(t_(ErrorMessages.NO_WELLS_SELECTED))

    @staticmethod
    def no_data() -> dict:
        """Figure for no data state."""
        return EmptyFigure.with_message(t_(ErrorMessages.NO_SERIES_DATA))


class CallbackContext:
    """Helper class to allow attribute-style access to callback context."""

    def __init__(self, callback_context):
        """Initialize with callback context dict.

        Parameters
        ----------
        callback_context : dict
            Dash callback context dict
        """
        self.ctx = callback_context
        self.triggered = self.ctx.triggered
        if self.triggered:
            self.triggered_id = self.ctx.triggered[0]["prop_id"].split(".")[0]
        else:
            self.triggered_id = None
        self.inputs_list = self.ctx.inputs_list


def get_callback_context(**kwargs):
    """Get callback context compatible with both Dash standalone and Django.

    When running standalone Dash, use the ctx object directly.
    When running under Django, parse from kwargs['callback_context'].

    Parameters
    ----------
    **kwargs
        Optional callback_context from Django environment

    Returns
    -------
    object
        Callback context with triggered, triggered_id, and inputs_list attributes
    """
    if len(kwargs) > 0 and "callback_context" in kwargs and config.get("DJANGO_APP"):
        # Django environment - parse from kwargs
        return CallbackContext(kwargs["callback_context"])
    elif not config.get("DJANGO_APP"):
        # Standalone Dash - use ctx
        from dash import ctx

        return ctx
    else:
        raise RuntimeError("Callback context not available.")


def extract_trigger_id(ctx_or_kwargs=None, parse_json: bool = True, **kwargs):
    """Extract triggered component ID from callback context.

    Compatible with both standalone Dash and Django environments.

    Parameters
    ----------
    ctx_or_kwargs : object or None
        Callback context object (for direct use) or None
    parse_json : bool
        Whether to parse JSON pattern IDs
    **kwargs
        Optional callback_context from Django environment

    Returns
    -------
    str or dict
        Triggered component ID

    Examples
    --------
    Standalone Dash:
        triggered_id = extract_trigger_id(ctx)

    Django:
        triggered_id = extract_trigger_id(**kwargs)
    """
    # Get context from either direct arg or kwargs
    if ctx_or_kwargs is None:
        ctx_obj = get_callback_context(**kwargs)
    else:
        ctx_obj = ctx_or_kwargs

    if not ctx_obj.triggered:
        raise PreventUpdate

    trigger_id = ctx_obj.triggered_id

    if parse_json:
        from ast import literal_eval

        try:
            return literal_eval(trigger_id)
        except (ValueError, SyntaxError):
            return trigger_id

    return trigger_id


def validate_selection_limit(
    wids: list, limit: int, error_message_template: str
) -> Optional[Tuple]:
    """Validate selection doesn't exceed limit.

    Parameters
    ----------
    wids : list
        Selected well IDs
    limit : int
        Maximum allowed selections
    error_message_template : str
        Error message with {} placeholder for limit

    Returns
    -------
    tuple or None
        Alert tuple if limit exceeded, None otherwise
    """
    if wids and len(wids) > limit:
        return AlertBuilder.warning(error_message_template.format(limit))
    return None


def extract_selected_points_x(selected_points) -> Optional[list]:
    """Extract x-values from Plotly selectedData structure safely.

    Returns None when selection is missing/empty or lacks "points".
    """
    if not selected_points or "points" not in selected_points:
        return None

    pts = pd.DataFrame(selected_points["points"])
    if pts.empty or "x" not in pts:
        return None

    return pd.to_datetime(pts["x"]).tolist()


class CallbackResponse:
    """Builder for multi-output callback responses.

    Helps construct consistent tuple returns for callbacks.
    """

    def __init__(self):
        """Initialize empty response."""
        self._outputs = []

    def add(self, value: Any) -> "CallbackResponse":
        """Add an output value.

        Parameters
        ----------
        value : Any
            Output value

        Returns
        -------
        self
            For chaining
        """
        self._outputs.append(value)
        return self

    def build(self) -> Tuple:
        """Build final response tuple.

        Returns
        -------
        tuple
            All output values as tuple
        """
        return tuple(self._outputs)

    def add_figure(self, figure: dict) -> "CallbackResponse":
        """Add a figure output."""
        return self.add(figure)

    def add_data(self, data: Any) -> "CallbackResponse":
        """Add a data output."""
        return self.add(data)

    def add_alert(
        self,
        show: bool,
        alert_type: Optional[str] = None,
        message: Optional[str] = None,
    ) -> "CallbackResponse":
        """Add an alert output."""
        return self.add((show, alert_type, message))

    def add_timestamp(self, success: bool = True) -> "CallbackResponse":
        """Add a timestamp store output."""
        return self.add(TimestampStore.create(success))


def dataframe_to_records(df: pd.DataFrame, default_on_empty: Any = None) -> Any:
    """Convert DataFrame to records for Dash tables.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to convert
    default_on_empty : Any
        Value to return if DataFrame is empty

    Returns
    -------
    list or default_on_empty
        Records list or default value
    """
    if df.empty:
        return default_on_empty if default_on_empty is not None else []
    return df.to_dict("records")
