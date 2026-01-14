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
        self, stmt: Any, geom_col: str = "coordinates"
    ) -> gpd.GeoDataFrame:
        """Execute a spatial query and return results as GeoDataFrame.

        Parameters
        ----------
        stmt : sqlalchemy.sql.expression.Selectable
            SQLAlchemy select statement
        geom_col : str, optional
            Name of geometry column, by default "coordinates"

        Returns
        -------
        gpd.GeoDataFrame
            Query results as GeoDataFrame
        """
        with self.engine.connect() as con:
            return gpd.GeoDataFrame.from_postgis(stmt, con=con, geom_col=geom_col)

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
