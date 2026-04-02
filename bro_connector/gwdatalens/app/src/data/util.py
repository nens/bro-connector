import logging
from functools import wraps
from typing import Any, Optional, Tuple

import numpy as np
import pandas as pd
import traval

try:
    from cachetools import cachedmethod

    CACHETOOLS_AVAILABLE = True
except (ModuleNotFoundError, ImportError):
    CACHETOOLS_AVAILABLE = False

logger = logging.getLogger("__name__")

# NOTE: this is the correct epsg:28992 definition for plotting backgroundmaps in RD
EPSG_28992 = (
    "+proj=sterea +lat_0=52.15616055555555 +lon_0=5.38763888888889 +k=0.9999079 "
    "+x_0=155000 +y_0=463000 +ellps=bessel "
    "+towgs84=565.417,50.3319,465.552,-0.398957,0.343988,-1.8774,4.0725 +units=m "
    "+no_defs"
)

WGS84 = "proj=longlat datum=WGS84 no_defs ellps=WGS84 towgs84=0,0,0"


def get_model_sim_pi(
    ml: Any,
    raw: pd.DataFrame,
    ci: float = 0.99,
    tmin: Any | None = None,
    tmax: Any | None = None,
    smoothfreq: str | None = None,
    savedir: Any | None = None,
) -> tuple[pd.Series, pd.DataFrame]:
    """Compute time series model simulation and prediction interval.

    Parameters
    ----------
    ml : object
        time series model
    raw : pandas.DataFrame
        DataFrame containing the raw data with an index to be used for interpolation.
    ci : float, optional
        Confidence interval for the prediction interval, by default 0.99.
    tmin : datetime-like, optional
        Minimum time for the simulation and prediction interval, by default None.
    tmax : datetime-like, optional
        Maximum time for the simulation and prediction interval, by default None.
    smoothfreq : str, optional
        Frequency for smoothing the prediction interval bounds, by default None.
    savedir : pathlib.Path or str, optional
        Directory to load the prediction interval from a file, by default None.

    Returns
    -------
    sim_i : pandas.Series
        Series containing the interpolated simulation results.
    pi : pandas.DataFrame
        DataFrame containing the prediction interval with columns ['lower', 'upper'].

    Notes
    -----
    If `savedir` is provided and `ml` is not None, the prediction interval is loaded
    from a file. Otherwise, it is computed using the model.
    """
    if savedir is not None and ml is not None:
        logger.debug("Load prediction interval from file: pi_%s.pkl", ml.name)
        sim = ml.simulate(tmin=tmin, tmax=tmax)
        new_idx = raw.index.union(sim.index)
        df_pi = pd.read_pickle(savedir / f"pi_{ml.name}.pkl")
        pi = pd.DataFrame(index=new_idx, columns=df_pi.columns)
        for i in range(2):
            pi.iloc[:, i] = traval.ts_utils.interpolate_series_to_new_index(
                df_pi.iloc[:, i], new_idx
            )
        # interpolate to observations index
        sim_interp = traval.ts_utils.interpolate_series_to_new_index(sim, new_idx)
        sim_i = pd.Series(index=new_idx, data=sim_interp)
        sim_i.name = "sim"

    elif ml is not None:
        logger.debug("Compute prediction interval with model: %s", ml.name)
        alpha = 1 - float(ci)

        # get prediction interval
        df_pi = ml.solver.prediction_interval(alpha=alpha)

        if not df_pi.empty:
            if smoothfreq is not None:
                df_pi.iloc[:, 0] = traval.ts_utils.smooth_lower_bound(
                    df_pi.iloc[:, 0], smoothfreq=smoothfreq
                )
                df_pi.iloc[:, 1] = traval.ts_utils.smooth_upper_bound(
                    df_pi.iloc[:, 1], smoothfreq=smoothfreq
                )

            if tmin is not None:
                df_pi = df_pi.loc[tmin:]
            if tmax is not None:
                df_pi = df_pi.loc[:tmax]

            sim = ml.simulate(tmin=tmin, tmax=tmax)

            # interpolate to observations index
            new_idx = raw.index.union(sim.index)
            pi = pd.DataFrame(index=new_idx, columns=df_pi.columns)
            for i in range(2):
                pi.iloc[:, i] = traval.ts_utils.interpolate_series_to_new_index(
                    df_pi.iloc[:, i], new_idx
                )

            sim_interp = traval.ts_utils.interpolate_series_to_new_index(sim, new_idx)
            sim_i = pd.Series(index=new_idx, data=sim_interp)
            sim_i.name = "sim"
        else:
            sim_i = pd.Series(index=raw.index, data=np.nan)
            sim_i.name = "sim"

            pi = pd.DataFrame(index=raw.index, columns=["lower", "upper"], data=np.nan)
    else:
        sim_i = pd.Series(index=raw.index, data=np.nan)
        sim_i.name = "sim"

        pi = pd.DataFrame(index=raw.index, columns=["lower", "upper"], data=np.nan)
    return sim_i, pi.astype(float)


def _make_hashable(value):
    """Recursively convert unhashable types to hashable equivalents.

    Lists become tuples, dicts become frozensets of (key, value) pairs.
    All other types are returned as-is.
    """
    if isinstance(value, list):
        return tuple(_make_hashable(v) for v in value)
    if isinstance(value, dict):
        return frozenset((k, _make_hashable(v)) for k, v in value.items())
    return value


def _hashable_key(self, *args, **kwargs):
    """Key function for cachedmethod that tolerates unhashable args/kwargs.

    Mirrors ``cachetools.keys.methodkey``: ``self`` is accepted but excluded
    from the key so that ``k[0]`` is always the first real argument (``wid``).
    Lists and dicts in arguments are converted to hashable equivalents before
    building the key tuple.  Sorted kwargs are appended as flat (name, value)
    pairs after the positional arguments.
    """
    key = tuple(_make_hashable(a) for a in args)
    if kwargs:
        key += tuple(
            item for k, v in sorted(kwargs.items()) for item in (k, _make_hashable(v))
        )
    return key


def conditional_cachedmethod(cache_getter):
    """Decorator to conditionally cache a method using cachetools.cachedmethod.

    This decorator checks the class USE_CACHE flag and only applies caching when
    both cachetools is available and caching is enabled. It also bypasses caching
    when ``query`` is provided in ``kwargs`` because ``query`` can be a
    non-hashable dictionary.

    Uses a custom key function so that list/dict arguments (e.g. ``columns=[...]``)
    are converted to hashable types instead of raising ``TypeError``.

    Parameters
    ----------
    cache_getter : callable
        Function that returns the cache object from self
        (e.g., lambda self: self._cache)
    """

    def decorator(func):
        if not CACHETOOLS_AVAILABLE:
            # No cachetools available - just return the original function
            return func

        # Create the cached version once at decoration time, using a key function
        # that handles unhashable argument types.
        cached_func = cachedmethod(cache_getter, key=_hashable_key)(func)

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if self.use_cache and "query" not in kwargs:
                return cached_func(self, *args, **kwargs)
            else:
                return func(self, *args, **kwargs)

        return wrapper

    return decorator
