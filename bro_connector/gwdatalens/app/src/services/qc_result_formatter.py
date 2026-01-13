"""Data transformation for quality control results.

Handles formatting of raw traval detection results into
presentation-ready dataframes with proper columns,
status flags, and translations.
"""

import logging

from pandas import DataFrame, Series

from gwdatalens.app.config import config
from gwdatalens.app.constants import ColumnNames, QCFlags
from gwdatalens.app.exceptions import EmptyResultError
from gwdatalens.app.messages import t_

logger = logging.getLogger(__name__)


class QCResultFormatter:
    """Formats raw traval detection results for presentation.

    Responsible for:
    - Adding QC columns (flagged, status, comment)
    - Status translations (NL ↔ EN)
    - Locale-specific formatting
    - Status propagation logic

    This class isolates data transformation logic
    from detection and visualization.
    """

    # Status translation mapping

    def format_results(
        self,
        timeseries_df: DataFrame,
        detector_results: DataFrame,
        detector_comments: Series,
        qualifier_column: str = None,
        only_unvalidated: bool = False,
    ) -> DataFrame:
        """Format detection results into QC dataframe.

        Parameters
        ----------
        timeseries_df : DataFrame
            Original time series with value and qualifier columns
        detector_results : DataFrame
            Raw detection results from traval.Detector
        detector_comments : Series
            Comments from detection
        qualifier_column : str
            Name of the qualifier column in timeseries
        only_unvalidated : bool, optional
            Whether to only show unvalidated observations, by default False

        Returns
        -------
        DataFrame
            Formatted QC dataframe with all required columns

        Raises
        ------
        ValueError
            If all observations already validated and only_unvalidated=True
        """
        logger.info("Formatting QC results")

        # Combine timeseries with detection results
        df = timeseries_df.join(detector_results)

        # Add id column for row tracking
        df[ColumnNames.ID] = range(df.index.size)

        # Initialize flagged column: 1 = flagged, 0 = not flagged
        df[ColumnNames.FLAGGED] = QCFlags.NOT_FLAGGED
        df.loc[detector_comments.index, ColumnNames.FLAGGED] = QCFlags.FLAGGED

        # Add comments from detection
        df[ColumnNames.COMMENT] = ""
        df.loc[detector_comments.index, ColumnNames.COMMENT] = detector_comments

        # Set index name
        df.index.name = ColumnNames.DATETIME

        # Process incoming status from database
        self._process_incoming_status(df, qualifier_column)

        # Initialize and set QC status
        self._initialize_qc_status(df)

        # Handle only_unvalidated filtering
        if only_unvalidated:
            self._filter_unvalidated(df)

        df[ColumnNames.CATEGORY] = ""  # for QC Protocol category

        logger.info(
            "Formatted %d observations, %d flagged",
            len(df),
            df[ColumnNames.FLAGGED].sum(),
        )

        return df

    def _process_incoming_status(self, df: DataFrame, qualifier_column: str) -> None:
        """Process and translate incoming qualifier status.

        Parameters
        ----------
        df : DataFrame
            QC dataframe to update (modified in-place)
        qualifier_column : str
            Name of the qualifier column
        """
        df["incoming_status_quality_control"] = df[qualifier_column]

        # Translate to English if needed
        if config.get("LOCALE") == "en":
            df[ColumnNames.INCOMING_STATUS_QUALITY_CONTROL] = df[
                ColumnNames.INCOMING_STATUS_QUALITY_CONTROL
            ].map(QCFlags.BRO_STATUS_TRANSLATION_NL_TO_EN)

    def _initialize_qc_status(self, df: DataFrame) -> None:
        """Initialize QC status based on incoming status and detection.

        Status propagation logic:
        1. Start with empty QC status
        2. Preserve reliable/unreliable/undecided statuses from database
        3. Mark flagged observations as unreliable (suggestion)
        4. Mark non-flagged, non-validated as reliable

        Parameters
        ----------
        df : DataFrame
            QC dataframe to update (modified in-place)
        """
        df[ColumnNames.STATUS_QUALITY_CONTROL] = ""

        # Mask for observations with existing validated status
        validated_mask = df["incoming_status_quality_control"].isin(
            [
                t_("general.reliable"),
                t_("general.unreliable"),
                t_("general.undecided"),
            ]
        )

        # Preserve existing validated status
        df.loc[validated_mask, ColumnNames.STATUS_QUALITY_CONTROL] = df.loc[
            validated_mask, ColumnNames.INCOMING_STATUS_QUALITY_CONTROL
        ]

        # Mark flagged as unreliable (suggestion for review)
        df.loc[df[ColumnNames.FLAGGED] == 1, ColumnNames.STATUS_QUALITY_CONTROL] = t_(
            "general.unreliable"
        )

        # Mark all non-flagged without status as reliable
        unvalidated_mask = (df[ColumnNames.FLAGGED] == 0) & (
            df[ColumnNames.STATUS_QUALITY_CONTROL] == ""
        )
        df.loc[unvalidated_mask, ColumnNames.STATUS_QUALITY_CONTROL] = t_(
            "general.reliable"
        )

    def _filter_unvalidated(self, df: DataFrame) -> None:
        """Filter to show only unvalidated observations.

        Parameters
        ----------
        df : DataFrame
            QC dataframe to update (modified in-place)

        Raises
        ------
        ValueError
            If all observations are already validated
        """
        # Mark already-validated observations as "skip" (-1)
        validated_mask = df[ColumnNames.INCOMING_STATUS_QUALITY_CONTROL].isin(
            [
                t_("general.reliable"),
                t_("general.unreliable"),
                t_("general.undecided"),
            ]
        )

        if validated_mask.sum() == len(df):
            raise EmptyResultError(
                "All observations are already validated %s" % df.index.name
            )

        # Clear data for validated observations (they appear but are skipped)
        df.loc[validated_mask, ColumnNames.FLAGGED] = QCFlags.SKIP
        df.loc[validated_mask, ColumnNames.COMMENT] = ""
        df.loc[validated_mask, ColumnNames.STATUS_QUALITY_CONTROL] = ""

        # NOTE: We don't filter the dataframe itself to avoid sync issues
        # between table/chart selections. Instead we mark them as skip (-1).
