import logging
import os
import pickle
from abc import ABC, abstractmethod
from functools import cached_property, lru_cache
from typing import List, Tuple
from urllib.parse import quote
import geopandas as gpd
import i18n
import numpy as np
import pandas as pd
from pyproj import Transformer
from sqlalchemy import create_engine, func, select, update
from sqlalchemy.orm import Session

from . import datamodel
from .util import EPSG_28992, WGS84

logger = logger = logging.getLogger(__name__)


class DataSourceTemplate(ABC):
    @property
    @abstractmethod
    def gmw_gdf(self) -> gpd.GeoDataFrame:
        """Get head observations metadata as GeoDataFrame.

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame containing head observations locations and metadata.
        """

    @abstractmethod
    def list_locations(self) -> List[str]:
        """List of measurement location names.

        Returns
        -------
        List[str]
            List of measurement location names.
        """

    @abstractmethod
    def list_locations_sorted_by_distance(self, name) -> List[str]:
        """List of measurement location names, sorted by distance.

        Parameters
        ----------
        name : str
            name of location to compute distances from

        Returns
        -------
        List[str]
            List of measurement location names, sorted by distance from `name`.
        """

    @abstractmethod
    def get_timeseries(self, gmw_id: str, tube_id: int) -> pd.Series:
        """Get time series.

        Parameters
        ----------
        gmw_id : str
            id of the observation well
        tube_id : int
            tube number of the observation well

        Returns
        -------
        pd.Series
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


class DataSource(DataSourceTemplate):
    def __init__(self, config):
        # init connection to database OR just read in some data from somewhere
        # Connect to database using psycopg2
        self.config = config
        try:
            self.engine = self._engine()
            logger.info("Database connected successfully")
            # NOTE: use for background callbacks
            # self.engine.dispose()
        except Exception as e:
            print(e)
            logger.error("Database not connected successfully")

        self.value_column = "field_value"
        self.qualifier_column = "status_quality_control"
        self.source = "zeeland"

    def _engine(self):
        config = self.config
        user = config.get('user')
        password = config.get('password')
        host = config.get('host')
        port = config.get('port')
        database = config.get('database')

        if not all([user, password, host, port, database]):
            raise ValueError("Database configuration is incomplete")

        # URL-encode the password
        encoded_password = quote(password, safe='')

        connection_string = (
            f"postgresql+psycopg2://{user}:{encoded_password}@{host}:{port}/{database}"
        )

        return create_engine(
            connection_string,
            connect_args={"options": "-csearch_path=gmw,gld,public"},
        )

    @cached_property
    def gmw_gdf(self) -> gpd.GeoDataFrame:
        return self._gmw_to_gdf()

    def _gmw_to_gdf(self):
        """
        Return all unique piezometers as a (Geo)DataFrame.

        Returns
        -------
        gdf : a (Geo)Pandas(Geo)DataFrame
            a (Geo)DataFrame with a unique index, describing the well-name and the tube-
            number, and at least the following columns:
                screen_top
                screen_bot
                lat
                lon
        """
        stmt = (
            select(
                datamodel.Well.bro_id,
                datamodel.Well.nitg_code,
                datamodel.TubeStatic.tube_number,
                datamodel.TubeDynamic.tube_top_position,
                datamodel.TubeDynamic.plain_tube_part_length,
                datamodel.TubeStatic.screen_length,
                datamodel.Well.coordinates,
                datamodel.Well.reference_system,
            )
            .join(datamodel.TubeStatic)
            .join(datamodel.TubeDynamic)
            .select_from(datamodel.Well)
        )
        # tubes = pd.read_sql(stmt, con=engine)
        with self.engine.connect() as con:
            gdf = gpd.GeoDataFrame.from_postgis(stmt, con=con, geom_col="coordinates")
        # for duplicates only keep the last combination of bro_id and tube_number
        gdf = gdf[~gdf.duplicated(subset=["bro_id", "tube_number"], keep="last")]

        # make sure all locations are in EPSG:28992
        msg = "Other coordinate reference systems than RD not supported yet"
        assert (gdf["reference_system"].str.lower() == "rd").all, msg

        # calculate top filter and bottom filter
        gdf["screen_top"] = gdf["tube_top_position"] - gdf["plain_tube_part_length"]
        gdf["screen_bot"] = gdf["screen_top"] - gdf["screen_length"]

        gdf["name"] = gdf.loc[:, ["bro_id", "tube_number"]].apply(
            lambda p: f"{p.iloc[0]}-{p.iloc[1]:03g}", axis=1
        )

        # set bro_id and tube_number as index
        gdf = gdf.set_index("name")

        # add number of measurements
        gdf["metingen"] = 0
        hasobs = [x for x in self.list_locations() if x in gdf.index]
        gdf.loc[hasobs, "metingen"] = 1

        # add location data in RD and lat/lon in WGS84
        gdf["x"] = gdf.geometry.x
        gdf["y"] = gdf.geometry.y

        transformer = Transformer.from_proj(EPSG_28992, WGS84, always_xy=False)
        gdf.loc[:, ["lon", "lat"]] = np.vstack(
            transformer.transform(gdf["x"].values, gdf["y"].values)
        ).T

        # sort data:
        gdf.sort_values(
            ["metingen", "nitg_code", "tube_number"], ascending=False, inplace=True
        )
        gdf["id"] = range(gdf.index.size)

        return gdf

    @lru_cache
    def list_locations(self) -> List[str]:
        """Return a list of locations that contain groundwater level dossiers, where
        each location is defines by a tuple of length 2: bro-id and tube_id
        """
        # get all grundwater level dossiers
        stmt = (
            select(
                datamodel.Well.bro_id,
                datamodel.TubeStatic.tube_number,
                func.count(
                    datamodel.GroundwaterLevelDossier.groundwater_level_dossier_id
                ).label("Number of glds"),
            )
            .join(datamodel.TubeStatic)
            .join(datamodel.Well)
            .group_by(
                datamodel.Well.bro_id,
                datamodel.TubeStatic.tube_number,
            )
            .select_from(datamodel.GroundwaterLevelDossier)
        )
        with self.engine.connect() as con:
            count = pd.read_sql(stmt, con=con)
        loc_df = count.loc[count["Number of glds"] > 0][["bro_id", "tube_number"]]
        locations = [
            f"{t[0]}-{t[1]:03g}" for t in loc_df.itertuples(index=False, name=None)
        ]
        return locations

    def list_locations_sorted_by_distance(self, name) -> List[str]:
        gdf = self.gmw_gdf.copy()

        p = gdf.loc[name, "coordinates"]

        gdf.drop(name, inplace=True)
        dist = gdf.distance(p)
        dist.name = "distance"
        distsorted = gdf.join(dist, how="right").sort_values("distance", ascending=True)
        return distsorted

    def get_timeseries(
        self, gmw_id: str, tube_id: int, observation_type="reguliereMeting"
    ) -> pd.Series:
        """Return a Pandas Series for the measurements at the requested bro-id and
        tube-id, im m. Return None when there are no measurements.
        """
        stmt = (
            select(
                datamodel.MeasurementTvp.measurement_time,
                datamodel.MeasurementTvp.field_value,
                datamodel.MeasurementTvp.calculated_value,
                datamodel.MeasurementPointMetadata.status_quality_control,
                datamodel.MeasurementPointMetadata.censor_reason_artesia,
                datamodel.MeasurementPointMetadata.censor_reason,
                datamodel.MeasurementPointMetadata.value_limit,
                datamodel.MeasurementTvp.field_value_unit,
                datamodel.MeasurementTvp.measurement_tvp_id,
                datamodel.MeasurementTvp.measurement_point_metadata_id,
            )
            .join(datamodel.MeasurementPointMetadata)
            .join(datamodel.Observation)
            .join(datamodel.ObservationMetadata)
            .join(datamodel.GroundwaterLevelDossier)
            .join(datamodel.TubeStatic)
            .join(datamodel.Well)
            .filter(
                datamodel.Well.bro_id.in_([gmw_id]),
                datamodel.TubeStatic.tube_number.in_([tube_id]),
                datamodel.ObservationMetadata.observation_type == observation_type,
            )
            .order_by(datamodel.MeasurementTvp.measurement_time)
        )
        with self.engine.connect() as con:
            df = pd.read_sql(stmt, con=con, index_col="measurement_time")

        if (
            df.loc[:, self.value_column].isna().all()
            and observation_type != "controlemeting"
        ):
            logger.warning(
                f"Timeseries {gmw_id}-{tube_id} has no data " f"in {self.value_column}!"
            )

        if self.value_column == "field_value":
            # make sure all measurements are in m
            mask = df["field_value_unit"] == "cm"
            if mask.any():
                df.loc[mask, "field_value"] /= 100
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

        # drop dupes
        df = df.loc[~df.index.duplicated(keep="first")]

        return df

    def count_measurements_per_filter(self) -> pd.Series:
        stmt = (
            select(
                datamodel.Well.bro_id,
                datamodel.TubeStatic.tube_number,
                func.count(datamodel.MeasurementTvp.measurement_tvp_id).label(
                    "Metingen"
                ),
            )
            .join(datamodel.MeasurementPointMetadata)
            .join(datamodel.Observation)
            .join(datamodel.ObservationMetadata)
            .join(datamodel.GroundwaterLevelDossier)
            .join(datamodel.TubeStatic)
            .join(datamodel.Well)
            .group_by(
                datamodel.Well.bro_id,
                datamodel.TubeStatic.tube_number,
            )
            .filter(datamodel.ObservationMetadata.observation_type == "reguliereMeting")
        )
        with self.engine.connect() as con:
            count = pd.read_sql(stmt, con=con)
        return count

    def save_qualifier(self, df):
        df = self.set_qc_fields_for_database(df)

        param_columns = [
            "measurement_point_metadata_id",
            self.qualifier_column,
            "censor_reason_artesia",
            "censor_reason",
            "value_limit",
        ]
        params = df[param_columns].to_dict("records")
        with Session(self.engine) as session:
            session.execute(update(datamodel.MeasurementPointMetadata), params)
            session.commit()

    def set_qc_fields_for_database(self, df, mask=None):
        if mask is None:
            mask = np.ones(df.index.size, dtype=bool)
        # approved obs
        mask2 = df.loc[:, self.qualifier_column].isin(
            [
                i18n.t("general.reliable"),
                i18n.t("general.unknown"),
            ]
        )
        if mask.any():
            df.loc[mask & mask2, "censor_reason_artesia"] = None
            df.loc[mask & mask2, "censor_reason"] = None
            df.loc[mask & mask2, "value_limit"] = None

        # flagged obs: create censor_reason_artesia
        mask2 = df.loc[:, self.qualifier_column].isin(
            [
                i18n.t("general.unreliable"),
                i18n.t("general.undecided"),
            ]
        )
        if mask2.any():
            df.loc[mask & mask2, "censor_reason_artesia"] = df.loc[
                mask & mask2, ["comment", "category"]
            ].apply(lambda s: ",".join(s), axis=1)
        return df


class DataSourceHydropandas(DataSourceTemplate):
    def __init__(self, extent=None, oc=None, fname=None, source="dino", **kwargs):
        if oc is None:
            if fname is None:
                fname = "obs_collection.pickle"
            if os.path.isfile(fname):
                with open(fname, "rb") as file:
                    oc = pickle.load(file)
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

    @cached_property
    def gmw_gdf(self) -> gpd.GeoDataFrame:
        return self._gmw_to_gdf()

    def _gmw_to_gdf(self):
        """Return all groundwater monitoring wells (gmw) as a GeoDataFrame"""
        oc = self.oc
        gdf = gpd.GeoDataFrame(oc, geometry=gpd.points_from_xy(oc.x, oc.y))
        columns = {
            "monitoring_well": "bro_id",
            "screen_bottom": "screen_bot",
            "tube_nr": "tube_number",
        }
        gdf = gdf.rename(columns=columns)
        gdf["nitg_code"] = ""

        # add number of measurements
        gdf["metingen"] = self.oc.stats.n_observations
        gdf["bro_id"] = gdf.index.tolist()

        return gdf

    @lru_cache
    def list_locations(self) -> List[Tuple[str, int]]:
        """Return a list of locations that contain groundwater level dossiers, where
        each location is defines by a tuple of length 2: bro-id and tube_id
        """
        oc = self.oc
        locations = []
        mask = [not x.loc[:, self.value_column].dropna().empty for x in oc["obs"]]
        for index in oc[mask].index:
            locations.append(tuple(oc.loc[index, ["monitoring_well", "tube_nr"]]))
        return locations

    def list_locations_sorted_by_distance(self, name):
        gdf = self.gmw_gdf.copy()
        p = gdf.loc[name, "geometry"]
        gdf.drop(name, inplace=True)
        dist = gdf.distance(p)
        dist.name = "distance"
        distsorted = self.oc.join(dist, how="right").sort_values(
            "distance", ascending=True
        )
        return distsorted

    def get_timeseries(self, gmw_id: str, tube_nr: int) -> pd.Series:
        """Return a Pandas Series for the measurements at the requested gmw_id and
        tube_id, im m. Return None when there are no measurements.
        """
        if self.source == "bro":
            name = f"{gmw_id}_{tube_nr}"  # bro
        elif self.source == "dino":
            name = f"{gmw_id}-{tube_nr}"  # dino
        else:
            raise ValueError

        columns = [self.value_column, self.qualifier_column]
        df = pd.DataFrame(self.oc.loc[name, "obs"].loc[:, columns])
        return df

    def save_qualifier(self, df: pd.DataFrame) -> None:
        raise NotImplementedError("Not connected to a database. Use CSV export!")
