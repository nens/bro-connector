"""Time series data service.

Handles fetching, transforming, and preparing time series data
for visualization and analysis. Separates data access logic from
callback orchestration.
"""

import logging
from collections.abc import Sequence

import numpy as np
import pandas as pd
from gwdatalens.app.constants import ColumnNames
from gwdatalens.app.exceptions import TimeSeriesError

logger = logging.getLogger(__name__)


class TimeSeriesService:
    """Service for time series operations.

    Encapsulates business logic for:
    - Fetching time series data
    - Data transformations
    - Measurement counting
    - Distance calculations

    Parameters
    ----------
    data_source : PostgreSQLDataSource
        Data source instance providing database access
    """

    def __init__(self, data_source):
        """Initialize with data source."""
        self.db = data_source

    def get_timeseries_for_observation_well(
        self,
        wid: int,
        observation_type: str | Sequence[str] | None = "reguliereMeting",
        columns: list[str] | None = None,
        tmin: str | None = None,
        tmax: str | None = None,
    ) -> pd.DataFrame:
        """Get time series for a well.

        Parameters
        ----------
        wid : int
            Well internal ID
        observation_type : str, sequence or None
            Observation type(s) to fetch. Provide None to load all types.
        columns : list of str, optional
            Specific columns to return
        tmin : str or None, optional
            ISO-8601 date string; only measurements at or after this timestamp
            are returned.
        tmax : str or None, optional
            ISO-8601 date string; only measurements at or before this timestamp
            are returned.

        Returns
        -------
        pd.DataFrame
            Time series data
        """
        try:
            ts = self.db.get_timeseries(
                wid,
                observation_type=observation_type,
                columns=columns,
                tmin=tmin,
                tmax=tmax,
            )
            return ts
        except Exception as e:
            msg = "Failed to get series for well %s: %s"
            logger.exception(msg, wid, e)
            raise TimeSeriesError(msg, wid, e) from e

    def get_series_for_multiple_wells(
        self,
        wids: list[int],
        observation_type: str | Sequence[str] | None = "reguliereMeting",
        tmin: str | None = None,
        tmax: str | None = None,
    ) -> dict[int, pd.DataFrame]:
        """Get time series for multiple wells.

        Parameters
        ----------
        wids : list of int
            List of well internal IDs
        observation_type : str
            Type of observation to fetch
        tmin : str or None, optional
            ISO-8601 date string lower bound.
        tmax : str or None, optional
            ISO-8601 date string upper bound.

        Returns
        -------
        dict
            Dictionary mapping wid to time series DataFrame
        """
        series_dict = {}
        for wid in wids:
            try:
                ts = self.get_timeseries_for_observation_well(
                    wid, observation_type, tmin=tmin, tmax=tmax
                )
                if ts is not None and not ts.empty:
                    series_dict[wid] = ts
            # allow failed results, so single well failure does not crash app
            except Exception as e:
                logger.warning("Skipping well %s: %s", wid, e)
                continue
        return series_dict

    def count_measurements(self) -> pd.DataFrame:
        """Get measurement counts per tube.

        Returns
        -------
        pd.DataFrame
            Measurement counts indexed by well and tube
        """
        return self.db.count_measurements_per_tube()

    def check_if_wells_have_data(self, wids: list[int]) -> bool:
        """Check if any wells in list have observation data.

        Parameters
        ----------
        wids : list of int
            Well internal IDs

        Returns
        -------
        bool
            True if any well has data
        """
        hasobs = self.db.list_observation_wells_with_data[ColumnNames.ID].tolist()
        return np.any(np.isin(wids, hasobs))

    def get_timeseries_with_column(
        self,
        wid: int,
        column: str | None = None,
        observation_type: str = "reguliereMeting",
    ) -> pd.DataFrame:
        """Get time series with specific column.

        Parameters
        ----------
        wid : int
            Well internal ID
        column : str, optional
            Column name (defaults to value_column from data source)
        observation_type : str
            Type of observation

        Returns
        -------
        pd.DataFrame
            Time series with specified column
        """
        if column is None:
            column = self.db.value_column
        return self.db.get_timeseries(
            wid, column=column, observation_type=observation_type
        )

    def get_validated_timeseries(
        self, wid: int, qualifier_value: str = "goedgekeurd"
    ) -> pd.Series:
        """Get time series filtered to validated observations only.

        Parameters
        ----------
        wid : int
            Well internal ID
        qualifier_value : str
            Qualifier value to filter for (default "goedgekeurd")

        Returns
        -------
        pd.Series
            Validated time series values
        """
        ts = self.db.get_timeseries(wid)
        mask = ts.loc[:, self.db.qualifier_column] == qualifier_value
        return ts.loc[mask, self.db.value_column].dropna()

    def get_timeseries_values(self, wid: int) -> pd.Series:
        """Get time series value column only.

        Parameters
        ----------
        wid : int
            Well internal ID

        Returns
        -------
        pd.Series
            Time series values
        """
        ts = self.db.get_timeseries(wid, columns=[self.db.value_column])
        return ts.dropna()

    def _invalidate_cache_for_wid(self, wid: int) -> None:
        """Remove all cache entries that belong to a given well ID.

        ``cachetools.cachedmethod`` uses ``methodkey`` by default, which strips
        ``self`` before building the key.  The first positional argument
        (``wid``) therefore lands at index 0.  Calls with extra parameters such
        as *tmin*, *tmax*, or *observation_type* produce longer keys that also
        start with ``wid``.  Iterating over a snapshot of the keys and removing
        every entry whose first element equals *wid* covers all call variants.

        Parameters
        ----------
        wid : int
            Well internal ID whose cached entries should be evicted.
        """
        if not (hasattr(self.db, "use_cache") and self.db.use_cache):
            return
        stale_keys = [k for k in list(self.db._cache.keys()) if k[0] == wid]
        for key in stale_keys:
            del self.db._cache[key]
        logger.debug("Evicted %d cache entries for wid=%s", len(stale_keys), wid)

    def save_correction(self, wids: list[int], corrections_df: pd.DataFrame) -> None:
        """Save manual corrections to database.

        Parameters
        ----------
        corrections_df : pd.DataFrame
            Corrections data to save
        """
        self.db.save_correction(corrections_df)
        for wid in wids:
            self._invalidate_cache_for_wid(wid)
        logger.info("Saved %d corrections", len(corrections_df))

    def reset_correction(self, wids, corrections_df: pd.DataFrame) -> None:
        """Reset manual corrections in database.

        Parameters
        ----------
        corrections_df : pd.DataFrame
            Corrections to reset
        """
        self.db.reset_correction(corrections_df)
        for wid in wids:
            self._invalidate_cache_for_wid(wid)
        logger.info("Reset %d corrections", len(corrections_df))

    def save_qualifier(self, wid: int, qualifiers_df: pd.DataFrame) -> None:
        """Save qualifiers to database.

        Parameters
        ----------
        qualifiers_df : pd.DataFrame
            Qualifier data to save
        """
        # delete cached copy after saving new qualifiers
        self.db.save_qualifier(qualifiers_df)
        self._invalidate_cache_for_wid(wid)
        logger.info("Saved %d qualifiers", len(qualifiers_df))
