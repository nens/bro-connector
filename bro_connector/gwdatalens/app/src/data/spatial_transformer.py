"""Spatial coordinate transformation utilities.

Handles coordinate system transformations and spatial enrichment
for groundwater monitoring well data.
"""

from typing import Tuple

import geopandas as gpd
import numpy as np
from pyproj import Transformer

from gwdatalens.app.src.data.util import EPSG_28992, WGS84


class SpatialTransformer:
    """Handles coordinate transformations and spatial operations.

    Responsible for:
    - Coordinate system transformations
    - Distance calculations
    - Spatial metadata enrichment

    Parameters
    ----------
    from_crs : str
        Source coordinate reference system (EPSG code)
    to_crs : str
        Target coordinate reference system (EPSG code)
    """

    def __init__(self, from_crs=EPSG_28992, to_crs=WGS84):
        """Initialize spatial transformer."""
        self.transformer = Transformer.from_proj(from_crs, to_crs, always_xy=False)

    def transform_to_wgs84(
        self, x: np.ndarray, y: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Transform coordinates from RD to WGS84.

        Parameters
        ----------
        x : np.ndarray
            X coordinates in RD
        y : np.ndarray
            Y coordinates in RD

        Returns
        -------
        Tuple[np.ndarray, np.ndarray]
            Tuple of (lon, lat) arrays in WGS84
        """
        return self.transformer.transform(x, y)

    @staticmethod
    def add_wgs84_to_gdf(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Add WGS84 coordinates to GeoDataFrame.

        Parameters
        ----------
        gdf : gpd.GeoDataFrame
            GeoDataFrame with RD coordinates

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame with added lon/lat columns
        """
        gdf["x"] = gdf.geometry.x
        gdf["y"] = gdf.geometry.y
        transformer = SpatialTransformer()
        gdf.loc[:, ["lon", "lat"]] = np.vstack(
            transformer.transform_to_wgs84(gdf["x"].values, gdf["y"].values)
        ).T
        return gdf
