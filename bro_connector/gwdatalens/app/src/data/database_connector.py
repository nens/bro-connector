"""PostgreSQL database connection management.

Handles database engine creation, connection lifecycle,
and query execution for PostgreSQL backends.
"""

import logging
from typing import Any, Optional
from urllib.parse import quote

import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine

from gwdatalens.app.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class DatabaseConnector:
    """Manages PostgreSQL database connections.

    Responsible for:
    - Creating and managing SQLAlchemy engine
    - Handling connection configuration
    - Executing raw SQL queries

    Parameters
    ----------
    config : dict
        Configuration dictionary containing database connection parameters
        with keys: user, password, host, port, database
    """

    def __init__(self, config: dict):
        """Initialize database connector with lazy connection.

        Parameters
        ----------
        config : dict
            Database configuration dictionary

        Note
        ----
        Connection is created lazily on first database access.
        """
        self.config: dict = config
        self._engine: Optional[Engine] = None
        logger.info(
            "Database connector initialized (connection deferred until first use)"
        )

    @property
    def engine(self) -> Engine:
        """Get database engine, creating connection lazily on first access.

        Returns
        -------
        sqlalchemy.engine.Engine
            Database engine instance

        Raises
        ------
        ConnectionError
            If database connection cannot be established
        ValueError
            If configuration is incomplete
        """
        if self._engine is None:
            self._engine = self._create_engine()
            logger.info("Database connection established")
        return self._engine

    def _create_engine(self) -> Engine:
        """Create SQLAlchemy engine from configuration.

        Returns
        -------
        sqlalchemy.engine.Engine
            Database engine instance

        Raises
        ------
        ValueError
            If configuration is incomplete
        ConnectionError
            If connection fails
        """
        user = self.config.get("user")
        password = self.config.get("password")
        host = self.config.get("host")
        port = self.config.get("port")
        database = self.config.get("database")

        if not all([user, password, host, port, database]):
            raise ConfigurationError("Database configuration is incomplete")

        encoded_password = quote(password, safe="")
        connection_string = (
            f"postgresql+psycopg2://{user}:{encoded_password}@{host}:{port}/{database}"
        )

        try:
            engine = create_engine(
                connection_string,
                connect_args={"options": "-csearch_path=gmw,gld,public,django_admin"},
            )
            # Test connection
            with engine.connect() as conn:
                conn.execute(select(1))
            return engine
        except Exception as e:
            logger.error("Failed to create database connection: %s", e)
            raise ConnectionError(f"Database connection failed: {e}") from e

    def execute_query(self, stmt: Any, **kwargs: Any) -> pd.DataFrame:
        """Execute a SQL query and return results as DataFrame.

        Parameters
        ----------
        stmt : sqlalchemy.sql.expression.Selectable
            SQLAlchemy select statement
        **kwargs
            Additional arguments to pass to pd.read_sql

        Returns
        -------
        pd.DataFrame
            Query results
        """
        with self.engine.connect() as con:
            return pd.read_sql(stmt, con=con, **kwargs)

    def execute_geodataframe_query(
        self,
        stmt: Any,
        x_col: str = "x_coordinate",
        y_col: str = "y_coordinate",
        crs: str = "EPSG:4326",
    ) -> gpd.GeoDataFrame:
        """Execute a query and return results as GeoDataFrame with Point geometries.

        Creates Point geometries from separate x and y coordinate columns.

        Parameters
        ----------
        stmt : sqlalchemy.sql.expression.Selectable
            SQLAlchemy select statement
        x_col : str, optional
            Name of x-coordinate column, by default "x_coordinate"
        y_col : str, optional
            Name of y-coordinate column, by default "y_coordinate"
        crs : str, optional
            Coordinate reference system, by default "EPSG:4326"

        Returns
        -------
        gpd.GeoDataFrame
            Query results as GeoDataFrame with Point geometries

        Raises
        ------
        ValueError
            If specified coordinate columns are not found in query results
        """
        # First execute the query as a regular DataFrame
        df = self.execute_query(stmt)

        # Verify coordinate columns exist
        if x_col not in df.columns or y_col not in df.columns:
            raise ValueError(
                f"Coordinate columns '{x_col}' and/or '{y_col}' not found in query results. "
                f"Available columns: {list(df.columns)}"
            )

        # Create Point geometries from x and y coordinates
        geometry = gpd.points_from_xy(df[x_col], df[y_col])

        # Convert to GeoDataFrame
        gdf = gpd.GeoDataFrame(df, geometry=geometry, crs=crs)

        return gdf

    @property
    def is_connected(self) -> bool:
        """Check if database connection is active.

        Returns
        -------
        bool
            True if connection exists and is active, False otherwise
        """
        if self._engine is None:
            return False
        try:
            with self._engine.connect() as conn:
                conn.execute(select(1))
            return True
        except ConnectionError:
            return False

    def close(self) -> None:
        """Close database connection if active.

        This releases database resources. Connection will be
        recreated automatically on next database access.
        """
        if self._engine is not None:
            logger.info("Closing database connection")
            self._engine.dispose()
            self._engine = None
