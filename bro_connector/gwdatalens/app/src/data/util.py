import logging

import numpy as np
import pandas as pd
import traval

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
    ml, raw, ci=0.99, tmin=None, tmax=None, smoothfreq=None, savedir=None
):
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
        logger.debug(f"Load prediction interval from file: pi_{ml.name}.pkl")
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
        logger.debug(f"Compute prediction interval with model: {ml.name}")
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
