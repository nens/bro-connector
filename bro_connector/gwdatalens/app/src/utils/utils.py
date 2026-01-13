import functools
import logging
import time
from typing import Any, Callable

from dash import callback_context


def conditional_cache(dec, condition, **kwargs):
    def decorator(func):
        if not condition:
            # Return the function unchanged, not decorated.
            return func
        return dec(**kwargs)(func)

    return decorator


def log_callback(
    log_time: bool = True,
    log_inputs: bool = True,
    log_outputs: bool = True,
    log_trigger: bool = True,
    log_level: int = logging.DEBUG,
):
    """Decorator to log Dash callback execution details.

    Respects the global CALLBACK_LOGGING configuration. When disabled globally,
    this decorator has zero overhead and returns the function unchanged.

    Parameters
    ----------
    log_time : bool, optional
        Log execution time, by default True
    log_inputs : bool, optional
        Log input values, by default True
    log_outputs : bool, optional
        Log output values, by default True
    log_trigger : bool, optional
        Log which component triggered the callback, by default True
    log_level : int, optional
        Logging level to use, by default logging.DEBUG

    Returns
    -------
    Callable
        Decorated function with logging (or unmodified function if globally disabled)

    Notes
    -----
    To enable callback logging globally, set CALLBACK_LOGGING=True in ConfigDefaults
    or via environment variable GWDATALENS_CALLBACK_LOGGING=true.

    Examples
    --------
    >>> @app.callback(...)
    ... @log_callback(log_time=True, log_inputs=True, log_outputs=False)
    ... def my_callback(input_val):
    ...     return process(input_val)

    >>> # Log everything at INFO level
    ... @app.callback(...)
    ... @log_callback(log_level=logging.INFO)
    ... def important_callback(val):
    ...     return val * 2
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Check global configuration at runtime (not decoration time)
            try:
                from gwdatalens.app.config import config

                callback_logging_enabled = config.get("CALLBACK_LOGGING", False)
            except ImportError:
                # Fallback if config not available
                callback_logging_enabled = False

            # If callback logging is disabled globally, skip all logging
            if not callback_logging_enabled:
                return func(*args, **kwargs)

            logger = logging.getLogger(func.__module__)

            # Build log message parts
            log_parts = [f"Callback: {func.__name__}"]

            # Log trigger information
            if log_trigger and callback_context.triggered:
                trigger_info = callback_context.triggered[0]
                prop_id = trigger_info.get("prop_id", "unknown")
                log_parts.append(f"Triggered by: {prop_id}")

            # Log inputs
            if log_inputs and (args or kwargs):
                inputs_str = []
                if args:
                    inputs_str.append(f"args={_format_values(args)}")
                if kwargs:
                    inputs_str.append(f"kwargs={_format_values(kwargs)}")
                log_parts.append(f"Inputs: {', '.join(inputs_str)}")

            # Log callback entry
            logger.log(log_level, " | ".join(log_parts))

            # Execute callback with timing
            start_time = time.perf_counter() if log_time else None
            try:
                result = func(*args, **kwargs)

                # Log execution time
                if log_time:
                    elapsed = (time.perf_counter() - start_time) * 1000
                    logger.log(
                        log_level,
                        f"Callback: {func.__name__} | Completed in {elapsed:.2f}ms",
                    )

                # Log outputs
                if log_outputs:
                    logger.log(
                        log_level,
                        f"Callback: {func.__name__} | Output: {_format_values(result)}",
                    )

                return result

            except Exception as e:
                # Log errors with timing if enabled
                if log_time:
                    elapsed = (time.perf_counter() - start_time) * 1000
                    logger.error(
                        f"Callback: {func.__name__} | Failed after {elapsed:.2f}ms | "
                        f"Error: {type(e).__name__}: {e}"
                    )
                else:
                    logger.error(
                        f"Callback: {func.__name__} | Failed | "
                        f"Error: {type(e).__name__}: {e}"
                    )
                raise

        return wrapper

    return decorator


def _format_values(obj: Any, max_length: int = 200) -> str:
    """Format values for logging, truncating if too long.

    Parameters
    ----------
    obj : Any
        Object to format
    max_length : int, optional
        Maximum string length before truncation, by default 200

    Returns
    -------
    str
        Formatted string representation
    """
    try:
        # Handle common Dash data structures
        if isinstance(obj, dict):
            if len(obj) == 0:
                return "{}"
            # For large dicts, show keys and count
            if len(obj) > 5:
                keys = list(obj.keys())[:3]
                return f"{{keys: {keys}..., {len(obj)} items}}"
            formatted = str(obj)
        elif isinstance(obj, (list, tuple)):
            if len(obj) == 0:
                return "[]" if isinstance(obj, list) else "()"
            # For large lists, show count and type of first item
            if len(obj) > 10:
                first_type = type(obj[0]).__name__ if obj else "empty"
                return f"[{first_type} x {len(obj)} items]"
            formatted = str(obj)
        elif obj is None:
            return "None"
        else:
            formatted = str(obj)

        # Truncate long strings
        if len(formatted) > max_length:
            return formatted[: max_length - 3] + "..."
        return formatted

    except Exception:
        # Fallback for objects that can't be easily formatted
        return f"<{type(obj).__name__}>"
