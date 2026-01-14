"""Groundwater monitoring well metadata construction and enrichment.

Builds and enriches GMW metadata from database queries, including
spatial transformations, screen positions, and display names.
"""

from typing import Optional

import geopandas as gpd
import pandas as pd

from gwdatalens.app.constants import ColumnNames
from gwdatalens.app.src.data import sql
from gwdatalens.app.src.data.database_connector import DatabaseConnector
from gwdatalens.app.src.data.spatial_transformer import SpatialTransformer

# Module-level constants
TUBE_NUMBER_FORMAT = "03g"


class GMWMetadataBuilder:
    """Constructs and enriches groundwater monitoring well metadata.

    Responsible for:
    - Querying well metadata from database
    - Validating coordinate systems
    - Calculating screen positions
    - Formatting location and display names

    Parameters
    ----------
    connector : DatabaseConnector
        Database connection handler
    spatial_transformer : SpatialTransformer, optional
        Spatial transformer for coordinate operations
    """

    def __init__(
        self,
        connector: DatabaseConnector,
        spatial_transformer: Optional[SpatialTransformer] = None,
    ):
        """Initialize metadata builder."""
        self.connector = connector
        self.spatial_transformer = spatial_transformer or SpatialTransformer()

    def build_gmw_metadata(self) -> gpd.GeoDataFrame:
        """Build raw GMW metadata from database.

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame with raw GMW metadata

        Raises
        ------
        ValueError
            If non-RD coordinate systems are found
        """
        stmt = sql.sql_get_gmws()
        gdf = self.connector.execute_geodataframe_query(stmt)
        return gdf

    @staticmethod
    def add_screen_positions(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Calculate screen top and bottom positions.

        Parameters
        ----------
        gdf : gpd.GeoDataFrame
            GeoDataFrame with tube position and length data

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame with added screen_top and screen_bot columns
        """
        gdf[ColumnNames.SCREEN_TOP] = (
            gdf[ColumnNames.TUBE_TOP_POSITION] - gdf[ColumnNames.PLAIN_TUBE_PART_LENGTH]
        )
        gdf[ColumnNames.SCREEN_BOT] = (
            gdf[ColumnNames.SCREEN_TOP] - gdf[ColumnNames.SCREEN_LENGTH]
        )
        return gdf

    @staticmethod
    def add_location_names(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Add location and display names to GeoDataFrame.

        Parameters
        ----------
        gdf : gpd.GeoDataFrame
            GeoDataFrame with location identifiers

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame with added location_name and display_name columns
        """
        gdf["location_name"] = (
            gdf[ColumnNames.WELL_CODE]
            .fillna(gdf[ColumnNames.BRO_ID])
            .fillna(gdf[ColumnNames.WELL_NITG_CODE])
            .fillna(gdf[ColumnNames.WELL_STATIC_ID].astype(str))
        )
        gdf[ColumnNames.DISPLAY_NAME] = (
            gdf["location_name"]
            + "-"
            + gdf[ColumnNames.TUBE_NUMBER].apply(lambda x: f"{x:{TUBE_NUMBER_FORMAT}}")
        )
        return gdf

    def enrich_metadata(
        self,
        gdf: gpd.GeoDataFrame,
        measurement_counts: Optional[pd.DataFrame] = None,
    ) -> gpd.GeoDataFrame:
        """Enrich metadata with screen positions, names, and spatial data.

        Parameters
        ----------
        gdf : gpd.GeoDataFrame
            Raw metadata GeoDataFrame
        measurement_counts : pd.DataFrame, optional
            DataFrame with measurement counts per tube

        Returns
        -------
        gpd.GeoDataFrame
            Enriched GeoDataFrame
        """
        # Add derived fields
        gdf = self.add_screen_positions(gdf)
        gdf = self.add_location_names(gdf)

        # Add measurement counts if provided
        if measurement_counts is not None:
            gdf = gdf.join(
                measurement_counts,
                on=[ColumnNames.WELL_STATIC_ID, ColumnNames.TUBE_STATIC_ID],
                how="left",
            )
            gdf["metingen"] = gdf["metingen"].fillna(0).astype(int)
        else:
            gdf["metingen"] = 0

        # Add spatial data
        gdf = self.spatial_transformer.add_wgs84_to_gdf(gdf)

        return gdf
