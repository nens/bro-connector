import logging
from copy import deepcopy

import traval
from pandas import DataFrame

from gwdatalens.app.constants import ColumnNames, QCDefaults
from gwdatalens.app.src.services.qc_executor import QCExecutor
from gwdatalens.app.src.services.qc_plotter import QCPlotter
from gwdatalens.app.src.services.qc_result_formatter import QCResultFormatter

logger = logging.getLogger(__name__)


def build_default_ruleset(db, pastastore):
    """Factory for the default traval RuleSet.

    Isolated as a pure function to keep the orchestrator focused on wiring
    and to simplify testing. Requires access to db (for tube top) and
    pastastore (for Pastas models).
    """

    def get_tube_top_level(name):
        return db.query_gdf(
            display_name=name, columns=[ColumnNames.TUBE_TOP_POSITION]
        ).squeeze()

    ruleset = traval.RuleSet(name="default")

    ruleset.add_rule(
        "spikes",
        traval.rulelib.rule_spike_detection,
        apply_to=0,
        kwargs={
            "threshold": QCDefaults.SPIKE_THRESHOLD,
            "spike_tol": QCDefaults.SPIKE_TOLERANCE,
            "max_gap": QCDefaults.SPIKE_MAX_GAP,
        },
    )

    ruleset.add_rule(
        "hardmax",
        traval.rulelib.rule_hardmax,
        apply_to=0,
        kwargs={
            "threshold": lambda name: get_tube_top_level(name),
        },
    )

    ruleset.add_rule(
        "flat_signal",
        traval.rulelib.rule_flat_signal,
        apply_to=0,
        kwargs={
            "window": QCDefaults.FLAT_SIGNAL_WINDOW,
            "min_obs": QCDefaults.FLAT_SIGNAL_MIN_OBS,
            "std_threshold": QCDefaults.FLAT_SIGNAL_STD_THRESHOLD,
        },
    )

    ruleset.add_rule(
        "pastas",
        traval.rulelib.rule_pastas_outside_pi,
        apply_to=0,
        kwargs={
            "ml": lambda name: pastastore.models[name],
            "ci": QCDefaults.PASTAS_CI,
            "min_ci": QCDefaults.PASTAS_MIN_CI,
            "smoothfreq": QCDefaults.PASTAS_CI_SMOOTHFREQ,
            "savedir": QCDefaults.PASTAS_CI_DIR,
        },
    )

    ruleset.add_rule(
        "combine_results",
        traval.rulelib.rule_combine_nan_or,
        apply_to=(1, 2, 3, 4),
    )

    return ruleset


class QCCoordinator:
    """Run QC by coordinating executor/formatter/plotter around traval."""

    def __init__(
        self,
        data_source,
        pastastore=None,
        formatter: QCResultFormatter | None = None,
        plotter: QCPlotter | None = None,
    ):
        self.db = data_source
        self.pastastore = pastastore
        self.formatter = formatter or QCResultFormatter()
        self.plotter = plotter or QCPlotter()

        # initialize rulesets
        self.ruleset = build_default_ruleset(self.db, self.pastastore)
        self._ruleset = deepcopy(self.ruleset)

        # Track plot trace configuration for callback use
        self.last_plot_context = {
            "has_pastas": False,
            "observations_trace_index": 0,
        }

        # store traval result
        self.traval_result: DataFrame | None = None

    def run_traval(
        self,
        wid,
        ruleset=None,
        tmin=None,
        tmax=None,
        only_unvalidated=False,
    ):
        """Orchestrate complete QC workflow: detect → format → visualize.

        Parameters
        ----------
        wid : int
            The internal id of the time series to run traval on.
        ruleset : optional
            The ruleset to apply for the traval process. If None, the default ruleset
            is used.
        tmin : optional
            The minimum timestamp to filter the timeseries data.
        tmax : optional
            The maximum timestamp to filter the timeseries data.
        only_unvalidated : bool, optional
            If True, only unvalidated observations are processed. Default is False.

        Returns
        -------
        df : pandas.DataFrame
            The dataframe containing the traval results, including flags and comments.
        figure : dict
            The plotly figure dict representing the traval results.

        Raises
        ------
        ValueError
            If all observations have already been checked.
        """
        name = self.db.gmw_gdf.loc[wid, ColumnNames.DISPLAY_NAME]
        logger.info("Running QC workflow for %s...", name)

        # Step 1: Load time series data
        ts = self.db.get_timeseries(wid)
        if tmin is not None:
            ts = ts.loc[tmin:]
        if tmax is not None:
            ts = ts.loc[:tmax]

        # Step 2: Extract value series
        series = ts.loc[:, self.db.value_column]
        series.name = name

        # Step 3: Execute detection
        executor = QCExecutor(self._ruleset if ruleset is None else ruleset)
        detector = executor.execute(series)

        # Step 4: Format results
        df = self.formatter.format_results(
            timeseries_df=ts,
            detector_results=executor.get_results_dataframe(),
            detector_comments=executor.get_comments(),
            qualifier_column=self.db.qualifier_column,
            only_unvalidated=only_unvalidated,
        )

        # Step 5: Get additional data for visualization
        ignore = self._get_ignore_indices(df) if only_unvalidated else None
        if "pastas" in self._ruleset.rules or QCDefaults.ALWAYS_SHOW_PASTAS_MODEL:
            ml = self._get_model_or_none(name)
        else:
            ml = None
        manual_obs = self._get_manual_observations(wid)

        # Step 6: Generate visualization
        figure, trace_info = self.plotter.plot_detection_result(
            detector=detector,
            model=ml,
            tmin=tmin,
            tmax=tmax,
            ignore=ignore,
            qualifiers=ts[self.db.qualifier_column],
            additional_series=manual_obs,
        )
        self.last_plot_context = trace_info

        logger.info("QC workflow complete for %s: %d observations", name, df.index.size)
        return df, figure

    def _get_ignore_indices(self, df: DataFrame):
        """Extract indices of already-validated observations.

        Parameters
        ----------
        df : DataFrame
            QC results dataframe

        Returns
        -------
        list or None
            Indices to ignore, or None if none to ignore
        """
        validated_mask = df["flagged"] == -1
        if validated_mask.sum() > 0:
            return df.loc[validated_mask].index
        return None

    def _get_model_or_none(self, name: str):
        """Get model from pastastore, returning None if not available.

        Parameters
        ----------
        name : str
            Model/well name

        Returns
        -------
        object or None
            Model object or None if not found
        """
        if self.pastastore is None:
            return None
        try:
            return self.pastastore.get_models(name)
        # broad exception to catch any model loading issues, and continue without
        # model if load fails
        except Exception as e:
            logger.warning("Could not load model %s: %s", name, e, exc_info=True)
            return None

    def _get_manual_observations(self, wid: int):
        """Get manual observations (controlemeting) for visualization.

        Parameters
        ----------
        wid : int
            Well/tube ID

        Returns
        -------
        Series or None
            Manual observations series or None if empty
        """
        try:
            manual_obs = self.db.get_timeseries(wid, observation_type="controlemeting")[
                self.db.value_column
            ]
            manual_obs.name = "controlemeting"
            if not manual_obs.empty:
                return [manual_obs]
        # broad exception to attempt loading control observations but continue
        # without if load fails
        except Exception as e:
            logger.warning("Could not load manual observations: %s", e, exc_info=True)
        return None

    def plot_traval_result(
        self,
        detector,
        model=None,
        tmin=None,
        tmax=None,
        ignore=None,
        qualifiers=None,
        additional_series=None,
    ):
        """Delegates to QCPlotter for plotting (kept for backward compatibility).

        This method is deprecated. Use plotter.plot_detection_result() directly.

        Parameters
        ----------
        detector : traval.Detector
            The detector object containing the series and detection results.
        model : object, optional
            The time series model, by default None
        tmin : datetime-like, optional
            Plot start time, by default None
        tmax : datetime-like, optional
            Plot end time, by default None
        ignore : list-like, optional
            Indices to ignore, by default None
        qualifiers : Series, optional
            Qualifiers for color coding, by default None
        additional_series : list, optional
            Additional series to plot, by default None

        Returns
        -------
        dict
            Plotly figure dict
        """
        logger.warning(
            "plot_traval_result() is deprecated. "
            "Use plotter.plot_detection_result() instead."
        )
        return self.plotter.plot_detection_result(
            detector=detector,
            model=model,
            tmin=tmin,
            tmax=tmax,
            ignore=ignore,
            qualifiers=qualifiers,
            additional_series=additional_series,
        )
