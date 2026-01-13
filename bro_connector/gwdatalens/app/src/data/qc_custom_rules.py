import logging

import pandas as pd
import pastas as ps
import traval

logger = logging.getLogger(__name__)

CUSTOM_RULE_NAMES = [
    "pastas_obswell",
]


def fit_noise_separate(ml, report=True, **kwargs):
    # first solve without a noisemodel and remember nfev
    ml.solve(report=False, **kwargs)
    nfev = ml.solver.nfev
    # copy the existing parameters, so we can set it back later
    parameters = ml.parameters.copy()
    # fix all other parameters to the optimal value
    for name in parameters.index:
        ml.set_parameter(name, initial=ml.parameters.at[name, "optimal"])
        ml.set_parameter(name, vary=False)
    ml.add_noisemodel(ps.ArNoiseModel())
    # fit noise_alpha in a seperate solve-iteration
    ml.solve(report=False, **kwargs)
    initial_noise_alpha = ml.parameters.at["noise_alpha", "initial"]
    # add extra iterations to nfev
    nfev = nfev + ml.solver.nfev

    # then calculate the jacobian once more with all parameters active
    ml.set_parameter("noise_alpha", initial=ml.parameters.at["noise_alpha", "optimal"])
    # set all paraemeters that were active to active again
    for name in parameters.index:
        ml.set_parameter(name, vary=parameters.at[name, "vary"])
    if "max_nfev" in kwargs:
        kwargs.pop("max_nfev")
    ml.solve(max_nfev=1, report=False, **kwargs)
    # set the initial vailues back to their original values
    for name in parameters.index:
        ml.set_parameter(name, initial=parameters.at[name, "initial"])
    ml.set_parameter("noise_alpha", initial=initial_noise_alpha)
    # and finally we set the nfev to the total of the three iterations
    ml.solver.nfev = nfev + 1
    if report:
        print(ml.fit_report())


def make_rule_pastas_obswell(db):
    def pastas_obswell(
        series,
        other: str = "",
        ci: float = 0.99,
        min_ci: float = 0.0,
        smoothfreq: str = "30D",
    ):
        """Traval rule: Pastas prediction interval based on another series.

        Parameters
        ----------
        series : pd.Series
            Time series to check
        other : pd.Series
            Reference time series with Pastas model
        ci : float, optional
            Confidence interval, by default 0.99
        min_ci : optional, float
            Minimum interval when mean prediction interval < min_ci, by default 0.0
        smoothfreq : str, optional
            Frequency for smoothing prediction interval, by default "30D"

        Returns
        -------
        bool pd.Series
            Mask of out-of-prediction-interval points
        """
        wid = db.get_internal_id(display_name=other)
        ts = db.get_timeseries(wid)[db.value_column].dropna()

        # interpolate time series to daily values by linear interpolation
        new_idx = pd.date_range(
            ts.index[0].round("D"), ts.index[-1].round("D"), freq="D"
        )
        tsi = (
            ts.reindex(ts.index.union(new_idx))
            .interpolate(method="time")
            .bfill()  # fill before start
            .ffill()  # fill at end
            .loc[new_idx]
        )
        tsi.index.name = other

        ml = ps.Model(series, freq="D")
        ml.add_stressmodel(
            ps.StressModel(
                tsi,
                name=tsi.index.name,
                rfunc=ps.One(),
                settings={
                    "fill_nan": "interpolate",
                    "sample_down": "drop",
                },
            )
        )
        tmin = tsi.index[0]
        tmax = tsi.index[-1]
        solver_kwargs = {
            "f_scale": 0.5,
            "loss": "cauchy",
            "warmup": 0,
            "tmin": tmin,
            "tmax": tmax,
            "report": False,
        }
        fit_noise_separate(ml, **solver_kwargs)
        logger.debug(
            "Pastas model '%s' <-- '%s': rsq = %.3f",
            series.index.name,
            other,
            ml.stats.rsq(),
        )
        return traval.rulelib.rule_pastas_outside_pi(
            series,
            ml,
            ci=ci,
            min_ci=min_ci,
            smoothfreq=smoothfreq,
            tmin=tmin,
            tmax=tmax,
        )

    return pastas_obswell
