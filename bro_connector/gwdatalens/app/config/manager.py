"""Configuration manager for GW DataLens application."""

import logging
import os
from pathlib import Path
from typing import Any

import tomli

from gwdatalens.app.constants import ConfigDefaults

logging.basicConfig(level=ConfigDefaults.STARTUP_LOG_LEVEL)
logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration is invalid or incomplete."""


class ConfigManager:
    """Manages application configuration with hierarchical precedence.

    Configuration priority (lowest to highest):
    1. Hard-coded defaults (ConfigDefaults)
    2. config.toml file
    3. database.toml file
    4. Environment variables
    5. CLI arguments

    Parameters
    ----------
    config_dir : Path, optional
        Directory containing configuration files. Defaults to app directory.
    """

    def __init__(self, config_dir: Path | None = None):
        """Initialize configuration manager."""
        if config_dir is None:
            config_dir = Path(__file__).parent.parent

        self.config_dir = Path(config_dir)
        self._config: dict[str, Any] = {}
        self._database_config: dict[str, Any] = {}

        # Load configuration in order of precedence
        self._load_defaults()
        self._load_config_file()
        self._load_database_file()
        self._load_environment_variables()

    def _load_defaults(self) -> None:
        """Load hard-coded default configuration."""
        self._config = {
            "DEBUG": False,
            "LOCALE": "nl",
            "DJANGO_APP": False,
            "CACHING": False,
            "SERIES_LOAD_LIMIT": ConfigDefaults.MAX_WELLS_SELECTION,
            "PORT": 8050,
            "BACKGROUND_CALLBACKS": False,
            "USE_MAPBOX": False,
            "LOG_LEVEL": "INFO",
            "CALLBACK_LOGGING": ConfigDefaults.CALLBACK_LOGGING,
            "CALLBACK_LOG_TIME": ConfigDefaults.CALLBACK_LOG_TIME,
            "CALLBACK_LOG_INPUTS": ConfigDefaults.CALLBACK_LOG_INPUTS,
            "CALLBACK_LOG_OUTPUTS": ConfigDefaults.CALLBACK_LOG_OUTPUTS,
            "CALLBACK_LOG_TRIGGER": ConfigDefaults.CALLBACK_LOG_TRIGGER,
            "pastastore": {
                "name": "pastastore",
                "path": "./gwdatalens/pastasdb/",
                "connector": "pas",
                "update_knmi": False,
            },
        }
        logger.debug("Loaded default configuration")

    def _load_config_file(self) -> None:
        """Load configuration from config.toml file."""
        config_file = self.config_dir / "config.toml"

        if not config_file.exists():
            logger.warning("Configuration file not found: %s", config_file)
            return

        try:
            with open(config_file, "rb") as f:
                file_config = tomli.load(f)

            # Merge settings into config
            if "settings" in file_config:
                self._config.update(file_config["settings"])

            # Merge pastastore config
            if "pastastore" in file_config:
                self._config["pastastore"].update(file_config["pastastore"])

            logger.info("Loaded configuration from %s", config_file)
        except Exception as e:
            logger.error("Failed to load config.toml: %s", e)
            raise ConfigurationError(f"Invalid config.toml: {e}") from e

    def _load_database_file(self) -> None:
        """Load database configuration from database.toml file."""
        db_file = self.config_dir / "database.toml"

        if not db_file.exists():
            logger.debug(
                "No database.toml found at %s. "
                "This is OK if using HydropandasDataSource or Django.",
                db_file,
            )
            return

        try:
            with open(db_file, "rb") as f:
                db_config = tomli.load(f)

            if "database" in db_config:
                self._database_config = db_config["database"]
                logger.info(f"Loaded database configuration from {db_file}")
            else:
                logger.warning("database.toml exists but missing [database] section")

        except Exception as e:
            logger.error(f"Failed to load database.toml: {e}")
            raise ConfigurationError(f"Invalid database.toml: {e}") from e

    def _load_environment_variables(self) -> None:
        """Load configuration from environment variables.

        Environment variables override config file settings.
        Format: GWDATALENS_<SETTING_NAME>=<value>
        """
        env_prefix = "GWDATALENS_"

        # Map of env var names to config keys and types
        env_mappings = {
            f"{env_prefix}DEBUG": (
                "DEBUG",
                lambda x: x.lower() in ("true", "1", "yes"),
            ),
            f"{env_prefix}PORT": ("PORT", int),
            f"{env_prefix}LOCALE": ("LOCALE", str),
            f"{env_prefix}CACHING": (
                "CACHING",
                lambda x: x.lower() in ("true", "1", "yes"),
            ),
            f"{env_prefix}SERIES_LOAD_LIMIT": ("SERIES_LOAD_LIMIT", int),
            f"{env_prefix}LOG_LEVEL": ("LOG_LEVEL", str),
            f"{env_prefix}USE_MAPBOX": (
                "USE_MAPBOX",
                lambda x: x.lower() in ("true", "1", "yes"),
            ),
            f"{env_prefix}CALLBACK_LOGGING": (
                "CALLBACK_LOGGING",
                lambda x: x.lower() in ("true", "1", "yes"),
            ),
            f"{env_prefix}CALLBACK_LOG_TIME": (
                "CALLBACK_LOG_TIME",
                lambda x: x.lower() in ("true", "1", "yes"),
            ),
            f"{env_prefix}CALLBACK_LOG_INPUTS": (
                "CALLBACK_LOG_INPUTS",
                lambda x: x.lower() in ("true", "1", "yes"),
            ),
            f"{env_prefix}CALLBACK_LOG_OUTPUTS": (
                "CALLBACK_LOG_OUTPUTS",
                lambda x: x.lower() in ("true", "1", "yes"),
            ),
            f"{env_prefix}CALLBACK_LOG_TRIGGER": (
                "CALLBACK_LOG_TRIGGER",
                lambda x: x.lower() in ("true", "1", "yes"),
            ),
            # Database environment variables
            f"{env_prefix}DB_HOST": ("database.host", str),
            f"{env_prefix}DB_PORT": ("database.port", int),
            f"{env_prefix}DB_NAME": ("database.database", str),
            f"{env_prefix}DB_USER": ("database.user", str),
            f"{env_prefix}DB_PASSWORD": ("database.password", str),
        }

        for env_var, (config_key, converter) in env_mappings.items():
            if env_var in os.environ:
                try:
                    value = converter(os.environ[env_var])

                    # Handle nested keys (e.g., "database.host")
                    if "." in config_key:
                        section, key = config_key.split(".", 1)
                        if section == "database":
                            self._database_config[key] = value
                    else:
                        self._config[config_key] = value

                    logger.debug(f"Loaded {config_key} from environment variable")
                except ValueError as e:
                    logger.warning(f"Invalid value for {env_var}: {e}")

    def update_from_cli(self, **kwargs: Any) -> None:
        """Update configuration from CLI arguments.

        CLI arguments have highest priority and override all other sources.

        Parameters
        ----------
        **kwargs
            Configuration key-value pairs from CLI
        """
        for key, value in kwargs.items():
            if value is not None:  # Only override if explicitly provided
                upper_key = key.upper()
                if upper_key in self._config:
                    self._config[upper_key] = value
                    logger.info(f"Updated {upper_key} from CLI: {value}")

    def update_database_from_django(self, localsecret: Any) -> None:
        """Update database configuration from Django localsecret.

        Parameters
        ----------
        localsecret
            Django localsecret module with database credentials
        """
        self._database_config = {
            "database": localsecret.database,
            "user": localsecret.user,
            "password": localsecret.password,
            "host": localsecret.host,
            "port": localsecret.port,
        }
        logger.info("Loaded database configuration from Django localsecret")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value.

        Parameters
        ----------
        key : str
            Configuration key
        default : Any, optional
            Default value if key not found

        Returns
        -------
        Any
            Configuration value
        """
        return self._config.get(key, default)

    def get_database_config(self) -> dict[str, Any]:
        """Get database configuration.

        Returns
        -------
        dict
            Database configuration dictionary

        Raises
        ------
        ConfigurationError
            If database configuration is incomplete
        """
        if not self._database_config:
            return {}

        required_keys = ["host", "port", "database", "user", "password"]
        missing_keys = [k for k in required_keys if k not in self._database_config]

        if missing_keys:
            raise ConfigurationError(
                f"Database configuration incomplete. Missing: {', '.join(missing_keys)}"
            )

        return self._database_config

    def has_database_config(self) -> bool:
        """Check if database configuration is available and complete.

        Returns
        -------
        bool
            True if complete database configuration exists
        """
        if not self._database_config:
            return False

        required_keys = ["host", "port", "database", "user", "password"]
        return all(k in self._database_config for k in required_keys)

    def to_dict(self) -> dict[str, Any]:
        """Export configuration as dictionary.

        Returns
        -------
        dict
            Complete configuration including database settings
        """
        result = self._config.copy()
        if self._database_config:
            result["database"] = self._database_config
        return result

    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access to configuration."""
        return self.get(key)

    def __repr__(self) -> str:
        """String representation of configuration."""
        # Don't expose password in repr
        safe_config = self.settings.copy()
        if "database" in safe_config and "password" in safe_config["database"]:
            safe_config["database"]["password"] = "***"
        return f"ConfigManager({safe_config})"
