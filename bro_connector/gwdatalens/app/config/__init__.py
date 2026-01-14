"""Configuration management for GW DataLens.

Provides a hierarchical configuration system with the following priority order
(lowest to highest):

1. Hard-coded defaults (ConfigDefaults in constants.py)
2. config.toml (user-editable application settings)
3. database.toml (user-editable database credentials - .gitignored)
4. Environment variables (for containerized deployments)
5. CLI arguments (highest priority, runtime overrides)

Usage
-----
    from gwdatalens.app.config import config

    # Access configuration values
    debug_mode = config.get("DEBUG")
    db_config = config.get_database_config()

    # Update configuration at runtime (e.g., from CLI)
    config.update_from_cli(debug=True, port=8080)
"""

from gwdatalens.app.config.manager import ConfigManager

# Global configuration instance
config = ConfigManager()

__all__ = ["config", "ConfigManager"]
