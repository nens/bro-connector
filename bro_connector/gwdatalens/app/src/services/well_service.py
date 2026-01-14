"""Well configuration and metadata service.

Handles well configuration data, tube information, and
metadata transformations for display and analysis.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import geopandas as gpd
import pandas as pd

from gwdatalens.app.constants import ColumnNames
from gwdatalens.app.exceptions import EmptyResultError, QueryError
from gwdatalens.app.validators import validate_not_empty

logger = logging.getLogger(__name__)


class WellService:
    """Service for well configuration and metadata operations.

    Encapsulates business logic for:
    - Well configuration data
    - Tube metadata
    - Well selection and filtering
    - Metadata formatting

    Parameters
    ----------
    data_source : PostgreSQLDataSource
        Data source instance providing database access
    """

    def __init__(self, data_source):
        """Initialize with data source."""
        self.db = data_source

    def get_well_configuration(self, wid: int) -> pd.DataFrame:
        """Get well configuration for all tubes at a location.

        Parameters
        ----------
        wid : int
            Location internal ID

        Returns
        -------
        pd.DataFrame
            Configuration data with screen depths, ground level, etc.
        """
        try:
            names = self.db.get_tube_numbers(wid)
            wids = (
                self.db.query_gdf(
                    display_name=names, operator="in", columns=[ColumnNames.ID]
                )
                .squeeze(axis="columns")
                .tolist()
            )

            usecols = [
                ColumnNames.TUBE_TOP_POSITION,
                ColumnNames.GROUND_LEVEL_POSITION,
                ColumnNames.SCREEN_TOP,
                ColumnNames.SCREEN_BOT,
                ColumnNames.DISPLAY_NAME,
            ]
            df = self.db.gmw_gdf.loc[wids, usecols].set_index(ColumnNames.DISPLAY_NAME)
            return df
        except KeyError as e:
            msg = "Failed to get well configuration for %s"
            logger.exception(msg, wid)
            raise QueryError(msg, wid) from e
        # not sure what other exceptions may arise here, but pass onto
        # caller which will handle the unknown exception.
        except Exception as e:
            logger.exception("Unknown error for %s: %s", wid, e)
            raise

    def get_wells_with_data_sorted_by_distance(
        self, wid: int, max_results: Optional[int] = None
    ) -> gpd.GeoDataFrame:
        """Get wells sorted by distance from reference well.

        Parameters
        ----------
        wid : int
            Reference well ID
        max_results : int, optional
            Limit number of results

        Returns
        -------
        gpd.GeoDataFrame
            Wells sorted by distance with distance column
        """
        try:
            gdf = self.db.list_observation_wells_with_data_sorted_by_distance(wid)
            if max_results is not None:
                gdf = gdf.head(max_results)
            return gdf
        except KeyError as e:
            logger.exception("Well %s not found or has no data: %s", wid, e)
            raise

    def get_tube_ids_from_names(self, tube_names: List[str]) -> List[int]:
        """Convert tube names to internal IDs.

        Parameters
        ----------
        tube_names : list of str
            Tube display names

        Returns
        -------
        list of int
            Internal IDs
        """
        try:
            wids = (
                self.db.query_gdf(
                    display_name=tube_names, operator="in", columns=[ColumnNames.ID]
                )
                .squeeze(axis="columns")
                .tolist()
            )
            return wids
        except Exception as e:
            msg = "Failed to convert tube names to IDs: %s"
            logger.exception(msg, e)
            raise EmptyResultError(msg) from e

    def get_tubes_for_location(self, wid: int) -> List[str]:
        """Get all tube names for a location.

        Parameters
        ----------
        wid : int
            Location internal ID

        Returns
        -------
        list of str
            Tube display names
        """
        try:
            names = self.db.get_tube_numbers(wid)
            return names
        except ValueError as e:
            msg = "No tubes found for location %s"
            logger.exception(msg, wid)
            raise QueryError(msg, wid) from e
        except Exception as e:
            msg = "Failed to get tubes for location %s: %s"
            logger.exception(msg, wid, e)
            raise EmptyResultError(msg, wid, e) from e

    def get_tubes_as_dropdown_options(self, wid: int) -> List[Dict[str, Any]]:
        """Get tubes for location formatted as dropdown options.

        Parameters
        ----------
        wid : int
            Location internal ID

        Returns
        -------
        list of dict
            Dropdown options for tubes
        """
        try:
            names = self.db.get_tube_numbers(wid)
            tubes_df = self.db.query_gdf(
                display_name=names,
                operator="in",
                columns=[ColumnNames.ID, ColumnNames.DISPLAY_NAME],
            )
            options = [
                {"label": row[ColumnNames.DISPLAY_NAME], "value": row[ColumnNames.ID]}
                for _, row in tubes_df.iterrows()
            ]
            return options
        # app should continue to work when getting dropdown options fails
        # for any reason
        except Exception as e:
            logger.exception(
                "Failed to get tubes as dropdown options for %s: %s", wid, e
            )
            return []

    def format_wells_as_options(
        self, wid: int, max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Format nearby wells as dropdown options.

        Parameters
        ----------
        wid : int
            Reference well ID
        max_results : int, optional
            Limit number of options

        Returns
        -------
        list of dict
            Dropdown options with labels showing distance
        """
        try:
            locs = self.get_wells_with_data_sorted_by_distance(wid, max_results)
            options = [
                {
                    "label": (
                        f"{row[ColumnNames.DISPLAY_NAME]} ({row.distance / 1e3:.1f} km)"
                    ),
                    "value": row[ColumnNames.ID],
                }
                for _, row in locs.iterrows()
            ]
            return options
        # app should continue to work when getting dropdown options fails
        # for any reason
        except Exception as e:
            logger.exception(
                "Failed to get wells sorted by distance for %s: %s", wid, e
            )
            return []

    def get_well_metadata_for_display(
        self, wids: List[int], columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """Get well metadata formatted for table display.

        Parameters
        ----------
        wids : list of int
            Well internal IDs
        columns : list of str, optional
            Specific columns to include

        Returns
        -------
        pd.DataFrame
            Metadata ready for display
        """
        if columns is None:
            columns = [
                ColumnNames.ID,
                ColumnNames.DISPLAY_NAME,
                ColumnNames.WELL_CODE,
                ColumnNames.BRO_ID,
                ColumnNames.WELL_NITG_CODE,
                ColumnNames.WELL_STATIC_ID,
                ColumnNames.TUBE_NUMBER,
                ColumnNames.SCREEN_TOP,
                ColumnNames.SCREEN_BOT,
                ColumnNames.X,
                ColumnNames.Y,
                ColumnNames.NUMBER_OF_OBSERVATIONS,
            ]

        try:
            gdf = self.db.gmw_gdf.copy()
            return gdf.loc[wids, columns]
        # app should always continue to work, even if something goes wrong
        except KeyError:
            msg = "Missing columns for wells %s"
            logger.exception(msg, wids)
            return pd.DataFrame()
        except Exception as e:
            logger.exception("Failed to get metadata for wells %s: %s", wids, e)
            return pd.DataFrame()

    def get_selected_wells_from_map_data(
        self, selected_data: Dict[str, Any]
    ) -> Tuple[Optional[List[str]], Optional[List[int]]]:
        """Extract well names and IDs from Dash map selection data.

        Parameters
        ----------
        selected_data : dict
            Plotly selectedData from map component

        Returns
        -------
        tuple
            (names, wids) or (None, None) if no selection
        """
        if selected_data is None:
            return None, None

        try:
            pts = pd.DataFrame(selected_data.get("points", []))
            validate_not_empty(pts, context="map selection points")
            mask = pts["curveNumber"] == 1  # wells with data
            names = pts.loc[mask, "text"].tolist()
            wids = pts.loc[mask, "pointNumber"].tolist()
            return names, wids
        except EmptyResultError:
            return None, None

    def prepare_map_selection_data(self, wids: List[int]) -> Dict[str, Any]:
        """Prepare selection data for map highlighting.

        Parameters
        ----------
        wids : list of int
            Well internal IDs to select

        Returns
        -------
        dict
            Plotly selectedData structure
        """
        try:
            dfm = self.db.gmw_gdf.loc[wids].copy()
            # Assign correct trace index:
            # trace 0 for wells without data, trace 1 for wells with data
            dfm["curveNumber"] = (dfm["metingen"] > 0).astype(int)

            selected_data = {
                "points": [
                    {
                        "curveNumber": dfm["curveNumber"].loc[i],
                        "pointNumber": dfm[ColumnNames.ID].loc[i],
                        "pointIndex": dfm[ColumnNames.ID].loc[i],
                        "lon": dfm["lon"].loc[i],
                        "lat": dfm["lat"].loc[i],
                        "text": dfm[ColumnNames.DISPLAY_NAME].loc[i],
                    }
                    for i in wids
                ]
            }
            return selected_data
        except KeyError as e:
            logger.exception("Failed to prepare map selection for %s: %s", wids, e)
            return {"points": []}

    def get_locations_list(self) -> pd.DataFrame:
        """Get list of all unique locations.

        Returns
        -------
        pd.DataFrame
            Location summary with tube counts and data availability
        """
        return self.db.list_locations

    def query_wells(
        self, columns: Optional[List[str]] = None, **query_kwargs
    ) -> gpd.GeoDataFrame:
        """Query wells with flexible filters.

        Parameters
        ----------
        columns : list of str, optional
            Columns to return
        **query_kwargs
            Query parameters (e.g., well_code="ABC", tube_number=1)

        Returns
        -------
        gpd.GeoDataFrame
            Filtered wells
        """
        return self.db.query_gdf(columns=columns, **query_kwargs)

    def get_well_name(self, wid: int) -> str:
        """Get display name for a well.

        Parameters
        ----------
        wid : int
            Well internal ID

        Returns
        -------
        str
            Display name
        """
        try:
            return self.db.gmw_gdf.loc[wid, ColumnNames.DISPLAY_NAME]
        except Exception as e:
            logger.exception("Failed to get name for well %s: %s", wid, e)
            return f"Well {wid}"

    def get_well_names(self, wids: List[int]) -> List[str]:
        """Get display names for multiple wells.

        Parameters
        ----------
        wids : list of int
            Well internal IDs

        Returns
        -------
        list of str
            Display names
        """
        try:
            return self.db.gmw_gdf.loc[wids, ColumnNames.DISPLAY_NAME].tolist()
        except Exception as e:
            logger.exception("Failed to get names for wells %s: %s", wids, e)
            return [f"Well {wid}" for wid in wids]

    def get_all_well_ids(self) -> List[int]:
        """Get all well IDs in the database.

        Returns
        -------
        list of int
            All well internal IDs
        """
        return self.db.gmw_gdf.index.tolist()

    def get_wells_by_display_name(self, names: List[str]) -> pd.Series:
        """Get well IDs from display names.

        Parameters
        ----------
        names : list of str
            Display names

        Returns
        -------
        pd.Series
            Series mapping names to IDs
        """
        try:
            return (
                self.db.gmw_gdf.set_index(ColumnNames.DISPLAY_NAME)
                .loc[names, [ColumnNames.ID]]
                .squeeze("columns")
            )
        except Exception as e:
            logger.exception("Failed to get wells by display names %s: %s", names, e)
            return pd.Series(dtype=int)

    def get_well_metadata(self, wid: int) -> Dict[str, Any]:
        """Get complete metadata for a well.

        Parameters
        ----------
        wid : int
            Well internal ID

        Returns
        -------
        dict
            Well metadata
        """
        try:
            return self.db.gmw_gdf.loc[wid].to_dict()
        except Exception as e:
            logger.exception("Failed to get metadata for well %s: %s", wid, e)
            return {}

    def get_wells_subset(self, wids: List[int]) -> gpd.GeoDataFrame:
        """Get GeoDataFrame subset for specific wells.

        Parameters
        ----------
        wids : list of int
            Well internal IDs

        Returns
        -------
        gpd.GeoDataFrame
            Subset of wells
        """
        try:
            return self.db.gmw_gdf.loc[wids].copy()
        except Exception as e:
            logger.exception("Failed to get subset for wells %s: %s", wids, e)
            return gpd.GeoDataFrame()
