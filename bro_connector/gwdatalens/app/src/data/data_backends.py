"""Data source abstraction layer for groundwater monitoring data.

Provides abstract interface (DataSourceTemplate) for pluggable backends:
- PostgreSQLDataSource: Production PostgreSQL database
- HydropandasDataSource: In-memory hydropandas collections

This module orchestrates database connections, metadata building,
and time series retrieval while delegating specific responsibilities
to specialized modules.
"""

import logging
import os
import pickle
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from functools import cached_property
from typing import Any, List, Optional, Union

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import Transformer
from sqlalchemy import bindparam, func, select, update
from sqlalchemy.orm import Session

from gwdatalens.app.constants import ColumnNames, DatabaseFields, UnitConversion
from gwdatalens.app.messages import t_
from gwdatalens.app.src.data import datamodel, sql
from gwdatalens.app.src.data.database_connector import DatabaseConnector
from gwdatalens.app.src.data.metadata_builder import (
    TUBE_NUMBER_FORMAT,
    GMWMetadataBuilder,
)
from gwdatalens.app.src.data.spatial_transformer import SpatialTransformer
from gwdatalens.app.src.data.util import EPSG_28992, WGS84
from gwdatalens.app.validators import validate_not_empty, validate_single_result

logger = logging.getLogger(__name__)

GMW_METADATA_COLUMNS = [
    ColumnNames.WELL_STATIC_ID,
    ColumnNames.BRO_ID,
    ColumnNames.WELL_CODE,
    ColumnNames.WELL_NITG_CODE,
    ColumnNames.TUBE_NUMBER,
    ColumnNames.DISPLAY_NAME,
    ColumnNames.ID,
]


class DataSourceTemplate(ABC):
    """Abstract base class for a data source class.

    This class defines the interface for the data source class, which includes
    methods for retrieving metadata, listing measurement locations, and
    getting time series data from a data source (e.g. database).

    Methods
    -------
    gmw_gdf : gpd.GeoDataFrame
        Get head observations metadata as GeoDataFrame.
    list_locations: List[str]
        List of measurement location names.
    list_observation_wells: List[str]
        List of observation well names.
    list_observation_wells_with_data_sorted_by_distance : List[str]
        List of observation well names, sorted by distance.
    get_timeseries : pd.DataFrame
        Get time series.
    save_qualifier :
        Save error detection (traval) result in database.
    """

    @property
    @abstractmethod
    def gmw_gdf(self) -> gpd.GeoDataFrame:
        """Get head observations metadata as GeoDataFrame.

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame containing head observations locations and metadata.
        """

    @property
    @abstractmethod
    def list_observation_wells_with_data(self) -> List[str]:
        """List of measurement location names.

        Returns
        -------
        List[str]
            List of measurement location names.
        """

    @abstractmethod
    def list_observation_wells_with_data_sorted_by_distance(self, wid) -> List[str]:
        """List of measurement location names, sorted by distance.

        Parameters
        ----------
        wid : int
            internal id of observation well

        Returns
        -------
        List[str]
            List of measurement location names, sorted by distance from `wid`.
        """

    @abstractmethod
    def get_timeseries(
        self,
        wid: int,
        tube_id: int,
        observation_type: Optional[str] = None,
    ) -> pd.DataFrame:
        """Get time series.

        Parameters
        ----------
        wid_id : str
            id of the observation well
        tube_id : int
            tube number of the observation well
        observation_type : str, optional
            type of observation, for BRO "reguliereMeting" or "controlemeting"

        Returns
        -------
        pd.DataFrame
            time series of head observations.
        """

    @abstractmethod
    def save_qualifier(self, df: pd.DataFrame) -> None:
        """Save error detection (traval) result after manual review.

        Parameters
        ----------
        df : pd.DataFrame
            dataframe containig error detection results after manual review.
        """

    @property
    @abstractmethod
    def backend(self):
        """Backend of the data source."""


class PostgreSQLDataSource(DataSourceTemplate):
    """DataSource class connecting to Provincie Zeelands PostgreSQL database.

    Composition-based architecture with delegated responsibilities:
    - DatabaseConnector: database connection management
    - GMWMetadataBuilder: metadata enrichment
    - SpatialTransformer: coordinate transformations

    Parameters
    ----------
    config : dict
        Configuration dictionary containing database connection parameters.

    Attributes
    ----------
    connector : DatabaseConnector
        Database connection handler
    metadata_builder : GMWMetadataBuilder
        Metadata construction and enrichment
    value_column : str
        Column name for the value field (containing the observations)
    qualifier_column : str
        Column name for the qualifier field
    source : str
        Source identifier, default is "zeeland".
    """

    backend = "postgresql"

    def __init__(self, config: dict):
        """Initialize PostgreSQL data source.

        Parameters
        ----------
        config : dict
            Database configuration dictionary
        """
        self.connector = DatabaseConnector(config)
        self.metadata_builder = GMWMetadataBuilder(
            self.connector,
            spatial_transformer=SpatialTransformer(),
        )

        self.value_column = DatabaseFields.FIELD_CALCULATED_VALUE
        self.qualifier_column = DatabaseFields.FIELD_STATUS_QUALITY_CONTROL
        self.source = "zeeland"

    @property
    def engine(self):
        """Get database engine from connector."""
        return self.connector.engine

    @cached_property
    def gmw_gdf(self) -> gpd.GeoDataFrame:
        """Get metadata as GeoDataFrame.

        Returns
        -------
        gpd.GeoDataFrame
            A GeoDataFrame containing the metadata of piezometers.
        """
        return self._gmw_gdf()

    def _gmw_gdf(self) -> gpd.GeoDataFrame:
        """Build and enrich groundwater monitoring well GeoDataFrame.

        Returns
        -------
        gpd.GeoDataFrame
            Enriched GeoDataFrame with all metadata
        """
        # Build base metadata
        gdf = self.metadata_builder.build_gmw_metadata()

        # Add measurement counts
        count = self.count_measurements_per_tube()

        # Enrich metadata
        gdf = self.metadata_builder.enrich_metadata(gdf, count)

        # Sort and index
        gdf = gdf.sort_values(
            ["location_name", ColumnNames.TUBE_NUMBER],
            ascending=[True, True],
        )
        gdf[ColumnNames.ID] = np.arange(len(gdf))
        gdf.index = gdf[ColumnNames.ID]

        return gdf

    def get_tube_numbers(self, wid=None, query=None, return_ids=False):
        """Get tube numbers for a given well.

        Parameters
        ----------
        wid : int, optional
            Well ID from gmw_gdf
        query : dict, optional
            Query parameters to find the well
        return_ids : bool, optional
            If True, return internal IDs instead of names

        Returns
        -------
        list or pd.Index
            Tube names or IDs
        """
        if wid is not None:
            well_static_id = self.gmw_gdf.loc[wid, ColumnNames.WELL_STATIC_ID]
            location_name = self.gmw_gdf.at[wid, ColumnNames.LOCATION_NAME]
        elif query is not None:
            sel = self.query_gdf(**query)
            row = validate_single_result(sel, context="well lookup")
            well_static_id = row[ColumnNames.WELL_STATIC_ID]
            location_name = row[ColumnNames.LOCATION_NAME]
        else:
            raise ValueError("Either 'wid' or 'query' must be provided.")

        stmt = sql.sql_get_tube_numbers_for_location(well_static_id=well_static_id)
        names = self.connector.execute_query(stmt)

        names = location_name + names.map(lambda s: f"-{s:{TUBE_NUMBER_FORMAT}}")
        if return_ids:
            return self.query_gdf(display_name=names.tolist(), operator="in").index
        else:
            return names.squeeze("columns").to_list()

    @cached_property
    def list_locations(self) -> pd.DataFrame:
        # # Get unique locations
        # stmt = sql.sql_get_unique_locations()
        # with self.engine.connect() as con:
        #     locs = pd.read_sql(stmt, con=con)

        gr = self.gmw_gdf.groupby(ColumnNames.WELL_STATIC_ID)
        cols = [
            ColumnNames.WELL_STATIC_ID,
            ColumnNames.BRO_ID,
            ColumnNames.WELL_CODE,
            ColumnNames.WELL_NITG_CODE,
            "location_name",
            ColumnNames.ID,
        ]
        locs = gr.first().reset_index().loc[:, cols]
        locs["ntubes"] = gr[ColumnNames.TUBE_STATIC_ID].count().values
        locs["hasdata"] = gr["metingen"].sum().values > 0

        return locs

    @cached_property
    def list_observation_wells(self) -> List[str]:
        """Return a list of observation wells.

        Returns
        -------
        List[str]
            List of measurement location names.
        """
        return self.gmw_gdf[ColumnNames.DISPLAY_NAME].tolist()

    @cached_property
    def list_observation_wells_with_data(self) -> pd.DataFrame:
        """Return a list of locations that contain groundwater level dossiers.

        Each location is defines by a tuple of length 2: bro_id/well_code and tube_id.

        Returns
        -------
        List[str]
            List of measurement location names.
        """
        # get all groundwater level dossiers
        mask = self.gmw_gdf["metingen"] > 0

        return self.gmw_gdf.loc[mask, GMW_METADATA_COLUMNS]

    def list_observation_wells_with_data_sorted_by_distance(self, wid) -> List[str]:
        """List locations sorted by their distance from a given location.

        Parameters
        ----------
        wid : int
            the id of the location to compute distances from.

        Returns
        -------
        pd.DataFrame
            A DataFrame containing the locations sorted by distance.
        """
        # only locations with data:
        gdf = self.gmw_gdf.copy()
        gdf = gdf.loc[gdf["metingen"] > 0]

        try:
            p = gdf.loc[wid, "coordinates"]
        except KeyError as e:
            raise KeyError(
                f"Location id '{wid}' is not in database or has no data."
            ) from e

        gdf.drop(wid, inplace=True)
        dist = gdf.distance(p)
        dist.name = "distance"
        distsorted = gdf.join(dist, how="right").sort_values("distance", ascending=True)
        return distsorted

    def get_wellcode(self, wid=None, query=None):
        if wid is not None:
            well_code = self.gmw_gdf.at[wid, ColumnNames.WELL_CODE]
            tube_number = self.gmw_gdf.at[wid, ColumnNames.TUBE_NUMBER]
        elif query is not None:
            sel = self.query_gdf(
                **query, columns=[ColumnNames.WELL_CODE, ColumnNames.TUBE_NUMBER]
            )
            row = validate_single_result(sel, context="well code lookup")
            well_code = row[ColumnNames.WELL_CODE]
            tube_number = row[ColumnNames.TUBE_NUMBER]
        else:
            raise ValueError("Either 'wid' or 'query' must be provided.")
        if isinstance(well_code, str) and len(well_code) > 0:
            return well_code + f"-{tube_number:03g}"
        else:
            return ""

    def wellcode_to_broid(self, well_code):
        query = {}
        if "-" in well_code:
            # split well_code into bro_id and tube_id
            parts = well_code.split("-")
            query[ColumnNames.WELL_CODE] = parts[0]
            query[ColumnNames.TUBE_NUMBER] = int(parts[-1])
            tube_number = query[ColumnNames.TUBE_NUMBER]
        else:
            query[ColumnNames.WELL_CODE] = well_code
            tube_number = None

        bro_id = self.query_gdf(**query, columns=ColumnNames.BRO_ID)
        validate_not_empty(bro_id, context=f"bro_id lookup for well code '{well_code}'")
        if pd.isna(bro_id).all():
            raise ValueError(f"No bro_id available for well code '{well_code}'.")
        else:
            return bro_id.astype(str).iloc[0] + (
                f"-{tube_number:03g}" if tube_number else ""
            )

    def broid_to_wellcode(self, bro_id):
        query = {}
        if "-" in bro_id:
            # split bro_id into bro_id and tube_id
            parts = bro_id.split("-")
            query[ColumnNames.BRO_ID] = parts[0]
            query[ColumnNames.TUBE_NUMBER] = int(parts[-1])
            tube_number = query[ColumnNames.TUBE_NUMBER]
        else:
            query[ColumnNames.BRO_ID] = bro_id
            tube_number = None

        well_code = self.query_gdf(**query, columns=ColumnNames.WELL_CODE)
        validate_not_empty(well_code, context=f"well code lookup for bro_id '{bro_id}'")
        if pd.isna(well_code).all():
            raise ValueError(f"No well_code available for well code '{well_code}'.")
        else:
            return well_code.astype(str).iloc[0] + (
                f"-{tube_number:03g}" if tube_number else ""
            )

    def query_gdf(
        self,
        query: str | None = None,
        operator: str = "==",
        columns: Optional[List[str] | str] = None,
        **kwargs,
    ) -> gpd.GeoDataFrame:
        """Query the gmw_gdf with a pandas query string.

        Parameters
        ----------
        query : str
            pandas query string to filter the gmw_gdf.
        columns : list of str or str, optional
            columns to return, by default None (all columns)
        **kwargs : dict
            key-value pairs to build a query string.

        Returns
        -------
        gpd.GeoDataFrame
            Filtered GeoDataFrame.
        """
        if query is not None:
            qgdf = self.gmw_gdf.query(query)
        else:
            template = "({} {} @{})"
            query = " and ".join(
                [template.format(k, operator, k) for k in kwargs.keys()]
            )
            qgdf = self.gmw_gdf.query(query, local_dict=kwargs)
        if columns is not None:
            qgdf = qgdf.loc[:, columns]
        return qgdf

    def get_corresponding_value(self, to: str = None, **kwargs):
        if not isinstance(to, str):
            raise TypeError("'to' must be a string.")
        q = self.query_gdf(**kwargs, columns=to)
        validate_not_empty(
            q, context=f"entry for '{list(kwargs.items())[0] if kwargs else 'unknown'}'"
        )
        try:
            return q.item()
        except (AttributeError, ValueError) as e:
            raise ValueError(
                f"Query did not return a single value for column '{to}'."
            ) from e

    def get_internal_id(self, **kwargs):
        return self.get_corresponding_value(to=ColumnNames.ID, **kwargs)

    def get_timeseries(
        self,
        wid: Optional[int] = None,
        query: Optional[dict[str:Any]] = None,
        observation_type="reguliereMeting",
        column: Optional[Union[List[str], str]] = None,
    ) -> pd.Series | pd.DataFrame:
        """Return a Pandas Series for the measurements for given bro-id and tube-id.

        Values returned im m. Return None when there are no measurements.

        Parameters
        ----------
        wid : int
            id of the observation well
        query : dict, optional
            query to select observation well, by default None
        observation_type : str, optional
            type of observation, by default "reguliereMeting". Options are
            "reguliereMeting", "controlemeting".
        column : str, optional
            column to return, by default None

        Returns
        -------
        pd.Series
            time series of head observations.
        """
        if wid is not None:
            well_static_id = self.gmw_gdf.at[wid, ColumnNames.WELL_STATIC_ID]
            tube_static_id = int(self.gmw_gdf.at[wid, ColumnNames.TUBE_STATIC_ID])
            display_name = self.gmw_gdf.at[wid, ColumnNames.DISPLAY_NAME]
        elif query is not None:
            sel = self.query_gdf(
                **query,
                columns=[
                    ColumnNames.WELL_STATIC_ID,
                    ColumnNames.TUBE_STATIC_ID,
                    ColumnNames.DISPLAY_NAME,
                ],
            )
            row = validate_single_result(sel, context="timeseries lookup")
            well_static_id = row[ColumnNames.WELL_STATIC_ID]
            tube_static_id = int(row[ColumnNames.TUBE_STATIC_ID])
            display_name = row[ColumnNames.DISPLAY_NAME]
        else:
            raise ValueError("Either 'wid' or 'query' must be provided.")

        logger.info(
            "Loading time series for %s (gmw_id: %s, tube_id: %s, obstype: %s) ...",
            display_name,
            well_static_id,
            tube_static_id,
            observation_type,
        )
        stmt = sql.sql_get_timeseries(
            well_static_id=well_static_id,
            tube_static_id=tube_static_id,
            observation_type=observation_type,
        )
        df = self.connector.execute_query(stmt, index_col="measurement_time")

        if (
            df.loc[:, self.value_column].isna().all()
            and observation_type != "controlemeting"
        ):
            logger.warning(
                "Timeseries %s has no data in %s!", display_name, self.value_column
            )

        if self.value_column == ColumnNames.FIELD_VALUE:
            # make sure all measurements are in m
            mask = df["field_value_unit"] == "cm"
            if mask.any():
                df.loc[mask, ColumnNames.FIELD_VALUE] *= UnitConversion.CM_TO_M
                df.loc[mask, "field_value_unit"] = "m"

            # convert all other measurements to NaN
            mask = ~(df["field_value_unit"].isna() | (df["field_value_unit"] == "m"))
            if mask.any():
                df.loc[mask, self.value_column] = np.nan
            # msg = "Other units than m or cm not supported yet"
            # assert (df["field_value_unit"] == "m").all(), msg

        # make index DateTimeIndex
        if df.index.dtype == "O":
            df.index = pd.to_datetime(df.index, utc=True)
        df.index = df.index.tz_localize(None)
        df.index.name = display_name

        # drop dupes
        df = df.loc[~df.index.duplicated(keep="first")]

        if column is not None:
            return df.loc[:, column]
        else:
            return df

    def count_measurements_per_tube(self):
        """Count measurements per tube from database.

        Returns
        -------
        pd.DataFrame
            DataFrame indexed by (well_static_id, tube_static_id) with measurement
            counts
        """
        stmt = sql.sql_count_measurements()
        df = self.connector.execute_query(stmt)

        return df.set_index(
            [ColumnNames.WELL_STATIC_ID, ColumnNames.TUBE_STATIC_ID]
        ).loc[:, ["metingen", "controlemetingen"]]

    def count_measurements_per_tube_old(self, fast=True) -> pd.Series:
        """Count the number of measurements per filter.

        Returns
        -------
        pd.Series
            A pandas Series containing the count of measurements in each time series.
        """
        if fast:
            subq = (
                select(
                    datamodel.MeasurementTvp.observation_id,
                    func.count(datamodel.MeasurementTvp.measurement_tvp_id).label(
                        "metingen"
                    ),
                )
                .group_by(datamodel.MeasurementTvp.observation_id)
                .subquery()
            )

            stmt = (
                select(
                    datamodel.WellStatic.groundwater_monitoring_well_static_id,
                    datamodel.WellStatic.internal_id,
                    datamodel.WellStatic.bro_id,
                    datamodel.WellStatic.well_code,
                    datamodel.WellStatic.nitg_code,
                    datamodel.TubeStatic.tube_number,
                    func.sum(subq.c.metingen).label("metingen"),
                )
                .join(
                    datamodel.Observation,
                    datamodel.Observation.observation_id == subq.c.observation_id,
                )
                .join(
                    datamodel.ObservationMetadata,
                    datamodel.ObservationMetadata.observation_metadata_id
                    == datamodel.Observation.observation_metadata_id,
                )
                .join(
                    datamodel.GroundwaterLevelDossier,
                    datamodel.GroundwaterLevelDossier.groundwater_level_dossier_id
                    == datamodel.Observation.groundwater_level_dossier_id,
                )
                .join(
                    datamodel.TubeStatic,
                    datamodel.TubeStatic.groundwater_monitoring_tube_static_id
                    == datamodel.GroundwaterLevelDossier.groundwater_monitoring_tube_id,
                )
                .join(
                    datamodel.WellStatic,
                    datamodel.WellStatic.groundwater_monitoring_well_static_id
                    == datamodel.TubeStatic.groundwater_monitoring_well_static_id,
                )
                .filter(
                    datamodel.ObservationMetadata.observation_type == "reguliereMeting"
                )
                .group_by(
                    datamodel.WellStatic.groundwater_monitoring_well_static_id,
                    datamodel.WellStatic.internal_id,
                    datamodel.WellStatic.bro_id,
                    datamodel.WellStatic.well_code,
                    datamodel.WellStatic.nitg_code,
                    datamodel.TubeStatic.tube_number,
                )
            )
            with self.engine.connect() as con:
                count = pd.DataFrame(con.execute(stmt).mappings().all())
        else:
            stmt = (
                select(
                    datamodel.WellStatic.groundwater_monitoring_well_static_id,
                    datamodel.WellStatic.internal_id,
                    datamodel.WellStatic.bro_id,
                    datamodel.WellStatic.well_code,
                    datamodel.WellStatic.nitg_code,
                    datamodel.TubeStatic.tube_number,
                    func.count(
                        func.distinct(datamodel.MeasurementTvp.measurement_time)
                    ).label("metingen"),
                )
                .join(datamodel.Observation)
                .join(datamodel.ObservationMetadata)
                .join(datamodel.GroundwaterLevelDossier)
                .join(datamodel.TubeStatic)
                .join(datamodel.WellStatic)
                .group_by(
                    datamodel.WellStatic.groundwater_monitoring_well_static_id,
                    datamodel.WellStatic.bro_id,
                    datamodel.WellStatic.nitg_code,
                    datamodel.TubeStatic.tube_number,
                )
                .filter(
                    datamodel.ObservationMetadata.observation_type == "reguliereMeting"
                )
            )
            with self.engine.connect() as con:
                count = pd.read_sql(stmt, con=con)
        return count

    def save_qualifier(self, df):
        """Save qualifier information to the database.

        Parameters
        ----------
        df : pandas.DataFrame
            The DataFrame containing the qualifier data to be saved. It must include
            the following columns:
            - DatabaseFields.FIELD_MEASUREMENT_TVP_ID
            - DatabaseFields.FIELD_STATUS_QUALITY_CONTROL
            - DatabaseFields.FIELD_CENSOR_REASON_DATALENS
            - DatabaseFields.FIELD_CENSOR_REASON
            - DatabaseFields.VALUE_LIMIT
        """
        df = self.set_qc_fields_for_database(df)

        param_map = {
            "b_measurement_point_metadata_id": (
                DatabaseFields.FIELD_MEASUREMENT_POINT_METADATA_ID
            ),
            "b_status_quality_control": DatabaseFields.FIELD_STATUS_QUALITY_CONTROL,
            "b_status_quality_control_reason_datalens": (
                DatabaseFields.FIELD_CENSOR_REASON_DATALENS
            ),
            "b_censor_reason": DatabaseFields.FIELD_CENSOR_REASON,
            "b_value_limit": DatabaseFields.FIELD_VALUE_LIMIT,
        }
        params = []
        for row in df.to_dict("records"):
            param_dict = {alias: row[col] for alias, col in param_map.items()}
            # ORM bulk update requires PK with actual column name
            param_dict[DatabaseFields.FIELD_MEASUREMENT_POINT_METADATA_ID] = row[
                DatabaseFields.FIELD_MEASUREMENT_POINT_METADATA_ID
            ]
            params.append(param_dict)

        stmt = (
            update(datamodel.MeasurementPointMetadata)
            .where(
                datamodel.MeasurementPointMetadata.measurement_point_metadata_id
                == bindparam("b_measurement_point_metadata_id")
            )
            .values(
                {
                    datamodel.MeasurementPointMetadata.status_quality_control: bindparam(  # noqa
                        "b_status_quality_control"
                    ),
                    datamodel.MeasurementPointMetadata.status_quality_control_reason_datalens: bindparam(  # noqa
                        "b_status_quality_control_reason_datalens"
                    ),
                    datamodel.MeasurementPointMetadata.censor_reason: bindparam(
                        "b_censor_reason"
                    ),
                    datamodel.MeasurementPointMetadata.value_limit: bindparam(
                        "b_value_limit"
                    ),
                }
            )
        )
        with Session(self.engine) as session:
            session.execute(
                stmt, params, execution_options={"synchronize_session": False}
            )
            session.commit()

    def save_correction(self, df):
        """Save correction information to the database.

        Parameters
        ----------
        df : pandas.DataFrame
            The DataFrame containing the correction data to be saved. It must include
            the following columns:
            - measurement_tvp_id: identifier of the measurement to correct
            - corrected_value: new value to save to calculated_value
            - comment: reason for the correction (saved to correction_reason)

        Notes
        -----
        This method:
        - Saves the original calculated_value to value_to_be_corrected
        - Updates calculated_value with the corrected_value
        - Saves the comment to correction_reason
        - Records the current timestamp to correction_time
        """
        # Prepare the updates
        params = []
        for _, row in df.iterrows():
            # Convert numpy types to Python native types
            measurement_tvp_id = int(row["measurement_tvp_id"])
            original_calc_value = row.get("original_calculated_value")
            if original_calc_value is not None and pd.notna(original_calc_value):
                original_calc_value = float(original_calc_value)

            corrected_value = row["corrected_value"]
            if corrected_value is not None and pd.notna(corrected_value):
                corrected_value = float(corrected_value)

            param = {
                "b_measurement_tvp_id": measurement_tvp_id,
                ColumnNames.INITIAL_CALCULATED_VALUE: original_calc_value,
                ColumnNames.CALCULATED_VALUE: corrected_value,
                ColumnNames.CORRECTION_REASON: row.get("comment", ""),
                ColumnNames.CORRECTION_TIME: datetime.now(timezone.utc),
            }
            # include PK with actual column name for ORM bulk update
            param[DatabaseFields.FIELD_MEASUREMENT_TVP_ID] = measurement_tvp_id
            params.append(param)

        # Execute batch update
        stmt = (
            update(datamodel.MeasurementTvp)
            .where(
                datamodel.MeasurementTvp.measurement_tvp_id
                == bindparam("b_measurement_tvp_id")
            )
            .values(
                {
                    ColumnNames.INITIAL_CALCULATED_VALUE: bindparam(
                        ColumnNames.INITIAL_CALCULATED_VALUE
                    ),
                    ColumnNames.CALCULATED_VALUE: bindparam(
                        ColumnNames.CALCULATED_VALUE
                    ),
                    ColumnNames.CORRECTION_REASON: bindparam("correction_reason"),
                    ColumnNames.CORRECTION_TIME: bindparam("correction_time"),
                }
            )
            .execution_options(synchronize_session=False)
        )
        with Session(self.engine) as session:
            session.execute(stmt, params)
            session.commit()

    def reset_correction(self, df):
        """Reset correction information in the database.

        Parameters
        ----------
        df : pandas.DataFrame
            The DataFrame containing the corrections to reset. It must include
            the following column:
            - measurement_tvp_id: identifier of the measurement to reset

        Notes
        -----
        This method:
        - Restores calculated_value from value_to_be_corrected
        - Clears correction_reason, value_to_be_corrected, and correction_time
        """
        # Prepare the reset updates
        params = []
        for _, row in df.iterrows():
            # Convert numpy types to Python native types
            measurement_tvp_id = int(row["measurement_tvp_id"])
            value_to_be_corrected = row.get(ColumnNames.INITIAL_CALCULATED_VALUE)
            if value_to_be_corrected is not None and pd.notna(value_to_be_corrected):
                value_to_be_corrected = float(value_to_be_corrected)

            param = {
                "b_measurement_tvp_id": measurement_tvp_id,
                ColumnNames.CALCULATED_VALUE: value_to_be_corrected,
                ColumnNames.INITIAL_CALCULATED_VALUE: None,
                ColumnNames.CORRECTION_REASON: None,
                ColumnNames.CORRECTION_TIME: None,
            }
            # include PK with actual column name for ORM bulk update
            param[DatabaseFields.FIELD_MEASUREMENT_TVP_ID] = measurement_tvp_id
            params.append(param)

        # Execute batch update
        stmt = (
            update(datamodel.MeasurementTvp)
            .where(
                datamodel.MeasurementTvp.measurement_tvp_id
                == bindparam("b_measurement_tvp_id")
            )
            .values(
                {
                    ColumnNames.CALCULATED_VALUE: bindparam(
                        ColumnNames.CALCULATED_VALUE
                    ),
                    ColumnNames.INITIAL_CALCULATED_VALUE: bindparam(
                        ColumnNames.INITIAL_CALCULATED_VALUE
                    ),
                    ColumnNames.CORRECTION_REASON: bindparam("correction_reason"),
                    ColumnNames.CORRECTION_TIME: bindparam("correction_time"),
                }
            )
            .execution_options(synchronize_session=False)
        )
        with Session(self.engine) as session:
            session.execute(stmt, params)
            session.commit()

    def set_qc_fields_for_database(self, df, mask=None):
        if mask is None:
            mask = np.ones(df.index.size, dtype=bool)

        # approved obs
        mask2 = df.loc[:, self.qualifier_column].isin(
            [
                t_("general.reliable"),
                t_("general.unknown"),
            ]
        )
        if mask.any():
            df.loc[mask & mask2, DatabaseFields.FIELD_CENSOR_REASON_DATALENS] = None
            df.loc[mask & mask2, DatabaseFields.FIELD_CENSOR_REASON] = None
            df.loc[mask & mask2, DatabaseFields.FIELD_VALUE_LIMIT] = None

        # flagged obs: create censor_reason_datalens
        mask2 = df.loc[:, self.qualifier_column].isin(
            [
                t_("general.unreliable"),
                t_("general.undecided"),
            ]
        )
        if mask2.any():
            df.loc[mask & mask2, DatabaseFields.FIELD_CENSOR_REASON_DATALENS] = df.loc[
                mask & mask2, ["comment", "category"]
            ].apply(lambda s: ",".join(s), axis=1)

        return df


class HydropandasDataSource(DataSourceTemplate):
    """DataSource using Hydropandas ObservationCollection (in-memory, read-only).

    This source loads groundwater monitoring well data from a hydropandas
    ObservationCollection, which can be created from BRO or other sources.
    Data is stored in-memory as DataFrames, not in a database.

    Parameters
    ----------
    extent : tuple, optional
        Extent (x_min, x_max, y_min, y_max) for BRO data filtering
    oc : hydropandas.ObservationCollection, optional
        Pre-loaded observation collection; if None, will load from file or BRO
    fname : str, optional
        Path to pickled observation collection file
    source : str, optional
        Data source, "bro" or "dino". Default is "bro".
    **kwargs
        Additional arguments passed to hydropandas.read_bro
    """

    backend = "hydropandas"

    def __init__(self, extent=None, oc=None, fname=None, source="bro", **kwargs):
        if oc is None:
            if fname is None:
                fname = "obs_collection.zip"
            if os.path.isfile(fname):
                oc = pd.read_pickle(fname)
            else:
                import hydropandas as hpd

                if source == "bro":
                    oc = hpd.read_bro(extent, **kwargs)
                    with open(fname, "wb") as file:
                        pickle.dump(oc, file)
                else:
                    raise ValueError(
                        f"Automatic download for source='{source}' not supported."
                    )

        self.source = source
        if self.source == "bro":
            self.value_column = "values"
            self.qualifier_column = "qualifier"
        else:
            self.value_column = "stand_m_tov_nap"
            self.qualifier_column = "bijzonderheid"

        self.oc = oc
        logger.info(
            f"Initialized HydropandasDataSource from {source} with {len(oc)} locations"
        )

    @cached_property
    def gmw_gdf(self) -> gpd.GeoDataFrame:
        return self._gmw_to_gdf()

    @cached_property
    def list_observation_wells(self) -> List[str]:
        """Return a list of all observation wells.

        Returns
        -------
        List[str]
            List of measurement location names (bro_id).
        """
        return self.gmw_gdf[ColumnNames.BRO_ID].tolist()

    def _gmw_to_gdf(self):
        """Return all groundwater monitoring wells (gmw) as a GeoDataFrame.

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame containing groundwater monitoring well locations and metadata
        """
        oc = self.oc
        use_cols = oc.columns.difference({"obs"})
        gdf = gpd.GeoDataFrame(
            oc.loc[:, use_cols], geometry=gpd.points_from_xy(oc.x, oc.y)
        )
        columns = {
            "monitoring_well": ColumnNames.BRO_ID,
            "screen_bottom": ColumnNames.SCREEN_BOT,
            "tube_nr": ColumnNames.TUBE_NUMBER,
            "tube_top": ColumnNames.TUBE_TOP_POSITION,
        }
        gdf = gdf.rename(columns=columns)
        gdf[ColumnNames.WELL_NITG_CODE] = ""

        # add location data in RD and lat/lon in WGS84
        transformer = Transformer.from_proj(EPSG_28992, WGS84, always_xy=False)
        gdf.loc[:, ["lon", "lat"]] = np.vstack(
            transformer.transform(gdf["x"].values, gdf["y"].values)
        ).T

        # add number of measurements
        gdf["metingen"] = self.oc.stats.n_observations
        gdf[ColumnNames.BRO_ID] = gdf.index.tolist()

        # sort data
        gdf.sort_values(
            [ColumnNames.BRO_ID, ColumnNames.TUBE_NUMBER],
            ascending=[True, True],
            inplace=True,
        )

        # add id
        gdf[ColumnNames.ID] = range(gdf.index.size)

        return gdf

    @cached_property
    def list_observation_wells_with_data(self) -> gpd.GeoDataFrame:
        """Return a list of locations that contain groundwater level dossiers.

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame with locations that have measurements.
        """
        oc = self.oc
        # Filter to only locations with data
        mask = [not x.dropna(how="all").empty for x in oc["obs"]]
        indices_with_data = oc[mask].index.tolist()

        # Return relevant columns from gmw_gdf
        cols = [
            ColumnNames.BRO_ID,
            ColumnNames.WELL_CODE,
            ColumnNames.WELL_NITG_CODE,
            ColumnNames.TUBE_NUMBER,
            ColumnNames.DISPLAY_NAME,
            ColumnNames.ID,
        ]
        return self.gmw_gdf.loc[
            self.gmw_gdf[ColumnNames.BRO_ID].isin(indices_with_data), cols
        ]

    def list_observation_wells_with_data_sorted_by_distance(self, name):
        """List locations sorted by their distance from a given location.

        Parameters
        ----------
        name : str
            the bro_id of the location to compute distances from.

        Returns
        -------
        gpd.GeoDataFrame
            A GeoDataFrame containing the locations sorted by distance.
        """
        gdf = self.gmw_gdf.copy()
        # Filter to only locations with data
        oc = self.oc
        mask = [not x.dropna(how="all").empty for x in oc["obs"]]
        indices_with_data = oc[mask].index.tolist()
        gdf = gdf.loc[gdf[ColumnNames.BRO_ID].isin(indices_with_data)]

        p = gdf.loc[gdf[ColumnNames.BRO_ID] == name, "geometry"].iloc[0]
        gdf = gdf.loc[gdf[ColumnNames.BRO_ID] != name].copy()
        dist = gdf.distance(p)
        dist.name = "distance"
        result = gdf.join(dist, how="left").sort_values("distance", ascending=True)
        return result

    def get_timeseries(
        self,
        wid: Optional[int] = None,
        query: Optional[dict] = None,
        observation_type="reguliereMeting",
        column: Optional[Union[List[str], str]] = None,
    ) -> pd.Series | pd.DataFrame:
        """Return a Pandas Series/DataFrame for the measurements.

        Values returned in m. Return empty Series when there are no measurements.

        Parameters
        ----------
        wid : int, optional
            id of the observation well (index from gmw_gdf)
        query : dict, optional
            query dict to select observation well
        observation_type : str, optional
            type of observation, by default "reguliereMeting"
        column : str or list, optional
            specific column(s) to return

        Returns
        -------
        pd.Series or pd.DataFrame
            time series of head observations.
        """
        # empty return for controlemeting
        if observation_type == "controlemeting":
            return pd.Series()

        # Get the well/tube info
        if wid is not None:
            bro_id = self.gmw_gdf.at[wid, ColumnNames.BRO_ID]
            tube_number = self.gmw_gdf.at[wid, ColumnNames.TUBE_NUMBER]
        elif query is not None:
            sel = self.query_gdf(**query)
            row = validate_single_result(sel, context="well translation")
            bro_id = row[ColumnNames.BRO_ID]
            tube_number = row[ColumnNames.TUBE_NUMBER]
        else:
            raise ValueError("Either 'wid' or 'query' must be provided.")

        # Build name based on source format
        if self.source == "bro":
            name = f"{bro_id}_{tube_number}"  # hydropandas bro format
        elif self.source == "dino":
            name = f"{bro_id}-{tube_number:03g}"  # dino format
        else:
            raise ValueError(f"Unknown source: {self.source}")

        try:
            obs_series = self.oc.loc[name, "obs"]
        except KeyError:
            # Return empty DataFrame if no data
            return pd.DataFrame()

        columns = [self.value_column, self.qualifier_column]
        df = pd.DataFrame(obs_series.loc[:, columns])

        if column is not None:
            return df.loc[:, column]
        else:
            return df

    def query_gdf(
        self,
        query: Optional[str] = None,
        operator: str = "==",
        columns: Optional[Union[List[str], str]] = None,
        **kwargs,
    ) -> gpd.GeoDataFrame:
        """Query the gmw_gdf with filtering.

        Parameters
        ----------
        query : str, optional
            pandas query string to filter the gmw_gdf.
        operator : str
            comparison operator for kwargs-based filtering
        columns : list of str or str, optional
            columns to return, by default None (all columns)
        **kwargs : dict
            key-value pairs to build a filter query.

        Returns
        -------
        gpd.GeoDataFrame
            Filtered GeoDataFrame.
        """
        if query is not None:
            qgdf = self.gmw_gdf.query(query)
        elif len(kwargs) > 0:
            # Filter using kwargs
            qgdf = self.gmw_gdf.copy()
            for key, value in kwargs.items():
                if operator == "==":
                    if isinstance(value, list):
                        qgdf = qgdf.loc[qgdf[key].isin(value)]
                    else:
                        qgdf = qgdf.loc[qgdf[key] == value]
                elif operator == "in":
                    qgdf = qgdf.loc[qgdf[key].isin(value)]
                else:
                    raise ValueError(f"Unsupported operator: {operator}")
        else:
            qgdf = self.gmw_gdf.copy()

        if columns is not None:
            if isinstance(columns, str):
                qgdf = qgdf.loc[:, [columns]]
            else:
                qgdf = qgdf.loc[:, columns]

        return qgdf

    def get_corresponding_value(self, to: str = None, **kwargs):
        """Translate from one identifier to another.

        Parameters
        ----------
        to : str
            Column name to translate to
        **kwargs
            Filtering criteria

        Returns
        -------
        value
            The translated value
        """
        if not isinstance(to, str):
            raise TypeError("'to' must be a string.")
        q = self.query_gdf(**kwargs, columns=to)
        validate_not_empty(
            q,
            context=(
                "corresponding entry for "
                f"'{list(kwargs.items())[0] if kwargs else 'unknown'}'"
            ),
        )
        try:
            return q.iloc[0][to]
        except (AttributeError, ValueError, IndexError) as e:
            raise ValueError(
                f"Query did not return a single value for column '{to}'."
            ) from e

    def get_internal_id(self, **kwargs):
        """Get the internal id (index) based on query criteria.

        Parameters
        ----------
        **kwargs
            Query criteria

        Returns
        -------
        int
            The index from gmw_gdf
        """
        q = self.query_gdf(**kwargs)
        validate_not_empty(q, context=f"internal ID lookup for {kwargs}")
        return q.index[0]

    def save_qualifier(self, df: pd.DataFrame) -> None:
        """Save qualifier information (no-op for HydropandasDataSource).

        Parameters
        ----------
        df : pd.DataFrame
            The DataFrame containing the qualifier data to be saved.

        Notes
        -----
        HydropandasDataSource is read-only. Export to CSV if modifications needed.
        """
        logger.warning(
            "HydropandasDataSource is read-only. Qualifier changes not saved. "
            "Export to CSV if modifications needed."
        )
