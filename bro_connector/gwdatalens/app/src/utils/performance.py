"""Performance profiling utilities for GW DataLens.

Provides tools to measure and report on:
- Database query execution time and result set size
- Serialisation / payload size passed to the Dash frontend
- Callback execution time (decorator-based)
- Front-end round-trip timing helpers

Usage examples
--------------
# Measure a DB call
with measure_db("get_timeseries wid=42"):
    df = db.get_timeseries(42)

# Measure payload size of a plotly figure dict
size_kb = payload_size_kb(figure_dict)

# Decorate a callback function
@profile_callback
def my_callback(value):
    ...

# Run a quick DB benchmark from a script / interactive session
results = benchmark_timeseries_load(db, wids=[1, 2, 3])
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Sequence
from contextlib import contextmanager
from functools import wraps
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Context-manager helpers
# ---------------------------------------------------------------------------


@contextmanager
def measure_db(label: str = "query", log_level: int = logging.DEBUG):
    """Context manager that logs the wall-clock time for a block of code.

    Parameters
    ----------
    label : str
        Human-readable label printed in the log line.
    log_level : int
        Python logging level (default INFO).

    Yields
    ------
    dict
        Mutable result dictionary with key ``"elapsed_s"`` filled in after
        the block exits.

    Examples
    --------
    >>> with measure_db("load wid=1") as r:
    ...     df = db.get_timeseries(1)
    >>> print(r["elapsed_s"])
    """
    result: dict[str, Any] = {"elapsed_s": None, "label": label}
    t0 = time.perf_counter()
    try:
        yield result
    finally:
        elapsed = time.perf_counter() - t0
        result["elapsed_s"] = elapsed
        logger.log(log_level, "[PERF] %s — %.3f s", label, elapsed)


# ---------------------------------------------------------------------------
# Payload / data-size helpers
# ---------------------------------------------------------------------------


def dataframe_size_kb(df: pd.DataFrame) -> float:
    """Return the estimated memory size of a DataFrame in kilobytes.

    Parameters
    ----------
    df : pd.DataFrame

    Returns
    -------
    float
        Approximate size in kilobytes (deep memory usage).
    """
    return df.memory_usage(deep=True).sum() / 1024


def payload_size_kb(obj: Any) -> float:
    """Return the JSON-serialised size of *obj* in kilobytes.

    This mirrors the data volume that Dash sends over the WebSocket /
    HTTP trigger to the frontend.

    Parameters
    ----------
    obj : Any
        Any JSON-serialisable object (e.g. a Plotly figure dict, a list of
        records, or a ``dcc.Store`` value).

    Returns
    -------
    float
        Size in kilobytes.
    """
    try:
        serialised = json.dumps(obj, default=str)
    except (TypeError, ValueError):
        serialised = str(obj)
    return len(serialised.encode("utf-8")) / 1024


def figure_trace_stats(figure: dict[str, Any]) -> dict[str, Any]:
    """Return basic statistics about a Plotly figure.

    Parameters
    ----------
    figure : dict
        Plotly figure dictionary (as produced by ``go.Figure().to_dict()``).

    Returns
    -------
    dict
        Dictionary with keys:
        - ``n_traces``: number of traces
        - ``total_points``: total number of data points across all traces
        - ``payload_kb``: estimated JSON payload size in kilobytes
    """
    traces = figure.get("data", [])
    n_traces = len(traces)
    total_points = 0
    for trace in traces:
        x = trace["x"]
        total_points += len(x)
    return {
        "n_traces": n_traces,
        "total_points": total_points,
        "payload_kb": payload_size_kb(figure),
    }


# ---------------------------------------------------------------------------
# Callback profiling decorator
# ---------------------------------------------------------------------------


def profile_callback(func):
    """Decorator that logs execution time and output payload size for a callback.

    Wraps a Dash callback function. Logs at INFO level:
    - Time taken to run (seconds)
    - Estimated JSON payload size of the return value (kilobytes)

    Usage
    -----
    @app.callback(...)
    @profile_callback
    def my_callback(...):
        ...
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - t0
        size_kb = payload_size_kb(result)
        logger.info(
            "[PERF] callback %s — %.3f s | output ~%.1f KB",
            func.__name__,
            elapsed,
            size_kb,
        )
        return result

    return wrapper


# ---------------------------------------------------------------------------
# Benchmark helpers
# ---------------------------------------------------------------------------


def benchmark_timeseries_load(
    db,
    wids: Sequence[int],
    observation_type: str | None = "reguliereMeting",
    tmin: pd.Timestamp | None = None,
    tmax: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Benchmark time-series loading from the database for a list of well IDs.

    Measures wall-clock DB query time and returns a summary DataFrame.

    Parameters
    ----------
    db : PostgreSQLDataSource
        Data source instance.
    wids : sequence of int
        Internal well IDs to benchmark.
    observation_type : str, optional
        Observation type to load.
    tmin : pd.Timestamp, optional
        Start of the time window.
    tmax : pd.Timestamp, optional
        End of the time window.

    Returns
    -------
    pd.DataFrame
        One row per well with columns:
        ``wid``, ``n_rows``, ``n_cols``, ``elapsed_s``,
        ``df_size_kb``, ``tmin_actual``, ``tmax_actual``.

    Examples
    --------
    >>> from gwdatalens.app.src.utils.performance import benchmark_timeseries_load
    >>> results = benchmark_timeseries_load(db, wids=[1, 2, 3, 4, 5])
    >>> print(results.to_string())
    """
    rows: list[dict[str, Any]] = []
    for wid in wids:
        with measure_db(f"load wid={wid}") as r:
            try:
                df = db.get_timeseries(
                    wid,
                    observation_type=observation_type,
                    tmin=tmin,
                    tmax=tmax,
                )
                n_rows = len(df)
                n_cols = df.shape[1] if df is not None and not df.empty else 0
                t_actual_min = df.index.min() if n_rows else None
                t_actual_max = df.index.max() if n_rows else None
                size_kb = dataframe_size_kb(df) if df is not None else 0.0
            except Exception as exc:  # noqa: BLE001
                logger.warning("Benchmark wid=%s failed: %s", wid, exc)
                n_rows = n_cols = size_kb = 0
                t_actual_min = t_actual_max = None

        rows.append(
            {
                "wid": wid,
                "n_rows": n_rows,
                "n_cols": n_cols,
                "elapsed_s": r["elapsed_s"],
                "df_size_kb": size_kb,
                "tmin_actual": t_actual_min,
                "tmax_actual": t_actual_max,
            }
        )

    return pd.DataFrame(rows).set_index("wid")


def benchmark_plot_obs(
    wids: Sequence[int],
    data,
    tmin: pd.Timestamp | None = None,
    tmax: pd.Timestamp | None = None,
) -> dict[str, Any]:
    """Benchmark the full plot_obs pipeline (DB + figure construction).

    Parameters
    ----------
    wids : sequence of int
        Well IDs to plot.
    data : DataManager
        DataManager instance.
    tmin : pd.Timestamp, optional
        Start of the time window passed to plot_obs.
    tmax : pd.Timestamp, optional
        End of the time window passed to plot_obs.

    Returns
    -------
    dict
        Keys: ``elapsed_s``, ``n_traces``, ``total_points``, ``payload_kb``.

    Examples
    --------
    >>> from gwdatalens.app.src.utils.performance import benchmark_plot_obs
    >>> stats = benchmark_plot_obs([1], data)
    >>> print(stats)
    """
    from gwdatalens.app.src.components.overview_chart import plot_obs

    with measure_db(f"plot_obs wids={list(wids)}") as r:
        figure = plot_obs(list(wids), data, tmin=tmin, tmax=tmax)

    stats = figure_trace_stats(figure)
    stats["elapsed_s"] = r["elapsed_s"]
    return stats
