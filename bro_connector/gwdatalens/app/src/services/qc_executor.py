"""Pure quality control execution logic for traval detector.

This module handles the core traval detection algorithm execution,
isolated from data access, formatting, and visualization concerns.
"""

import logging
from typing import Optional

import traval
from pandas import Series

logger = logging.getLogger(__name__)


class QCExecutor:
    """Executes traval quality control detection on time series data.

    Responsible for:
    - Running detector with ruleset
    - Extracting detection results
    - Managing detector state

    This class contains ONLY the domain logic for detection,
    with no database access or data transformation.

    Parameters
    ----------
    ruleset : traval.RuleSet
        Ruleset to apply during detection
    """

    def __init__(self, ruleset: traval.RuleSet):
        """Initialize with a ruleset."""
        self.ruleset = ruleset
        self.detector: Optional[traval.Detector] = None

    def execute(self, series: Series) -> traval.Detector:
        """Run quality control detection on a time series.

        Parameters
        ----------
        series : pd.Series
            Time series to analyze
            Must have a name attribute (well/location name)

        Returns
        -------
        traval.Detector
            Detector instance with detection results

        Raises
        ------
        ValueError
            If series is empty or missing name
        """
        if series.empty:
            raise ValueError("Cannot run detection on empty series")
        if not series.name:
            raise ValueError("Series must have a name attribute")

        logger.info("Running QC detection for %s", series.name)
        detector = traval.Detector(series)
        detector.apply_ruleset(self.ruleset)

        self.detector = detector
        return detector

    def get_comments(self) -> Series:
        """Get comment series from latest detection.

        Returns
        -------
        pd.Series
            Comments for flagged observations

        Raises
        ------
        RuntimeError
            If no detection has been run
        """
        if self.detector is None:
            raise RuntimeError("No detection results available. Call execute() first.")
        return self.detector.get_comment_series()

    def get_results_dataframe(self):
        """Get results dataframe from latest detection.

        Returns
        -------
        pd.DataFrame
            Detection results

        Raises
        ------
        RuntimeError
            If no detection has been run
        """
        if self.detector is None:
            raise RuntimeError("No detection results available. Call execute() first.")
        return self.detector.get_results_dataframe()

    def get_corrections(self) -> dict:
        """Get corrections from latest detection.

        Returns
        -------
        dict
            Mapping of step to corrections

        Raises
        ------
        RuntimeError
            If no detection has been run
        """
        if self.detector is None:
            raise RuntimeError("No detection results available. Call execute() first.")
        return self.detector.corrections
