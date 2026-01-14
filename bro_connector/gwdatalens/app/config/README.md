# GW DataLens Configuration Guide

This document describes the configuration system for GW DataLens.

## Overview

GW DataLens uses a hierarchical configuration system with the following priority order (lowest to highest):

1. **Hard-coded defaults** - Sensible defaults in `ConfigDefaults` class
2. **config.toml** - User-editable application settings
3. **database.toml** - User-editable database credentials (gitignored)
4. **Environment variables** - For containerized deployments
5. **CLI arguments** - Highest priority, runtime overrides

## Configuration Files

### config.toml

Main application configuration file located at `gwdatalens/app/config.toml`.

**Example:**

```toml
[settings]
DEBUG = true               # enable debug mode, only for standalone mode
LOCALE = "nl"              # application language, options: "nl", "en"
DJANGO_APP = false         # Set to true when running under Django
CACHING = false            # Enable caching (doesn't work with DJANGO_APP=true)
SERIES_LOAD_LIMIT = 50     # Max number of series to load simultaneously
PORT = 8050                # Default port for the Dash app
BACKGROUND_CALLBACKS = false
USE_MAPBOX = false         # Requires Mapbox access token
LOG_LEVEL = "INFO"         # DEBUG, INFO, WARNING, ERROR, CRITICAL

[pastastore]
name = "zeeland_bro"            # name of the pastas database
path = "./gwdatalens/pastasdb/" # path to pastas model database
connector = "pas"               # database connector
update_knmi = false             # update knmi data in pastas database on startup
```

### database.toml

Database credentials file located at `gwdatalens/app/database.toml`.

**Setup:**

1. Copy `database_template.toml` to `database.toml`
2. Fill in your database credentials
3. Ensure `database.toml` is in `.gitignore` (should already be the case, but good to check.)

**Example:**

```toml
[database]
host = "localhost"
port = 5432
database = "gwdatalens_db"
user = "gwdatalens_user"
password = "your_secure_password"
```

## Environment Variables

Environment variables override `config.toml` but are overridden by CLI arguments.

All environment variables use the `GWDATALENS_` prefix:

### Application Settings

- `GWDATALENS_DEBUG=true` - Enable debug mode
- `GWDATALENS_PORT=8050` - Set application port
- `GWDATALENS_LOCALE=nl` - Set language (nl/en)
- `GWDATALENS_CACHING=true` - Enable caching
- `GWDATALENS_SERIES_LOAD_LIMIT=50` - Max series to load at once
- `GWDATALENS_LOG_LEVEL=INFO` - Set logging level
- `GWDATALENS_USE_MAPBOX=true` - Enable Mapbox

### Database Settings

- `GWDATALENS_DB_HOST=localhost` - Database host
- `GWDATALENS_DB_PORT=5432` - Database port
- `GWDATALENS_DB_NAME=database_name` - Database name
- `GWDATALENS_DB_USER=username` - Database user
- `GWDATALENS_DB_PASSWORD=password` - Database password

**Example (bash):**

```bash
export GWDATALENS_DEBUG=true
export GWDATALENS_PORT=8080
export GWDATALENS_DB_HOST=postgres.example.com
gwdatalens
```

## CLI Arguments

Command-line arguments have the highest priority and override all other configuration sources.

```bash
gwdatalens --help

# Run with custom port
gwdatalens --port 8080

# Run in debug mode
gwdatalens --debug

# Set locale to English
gwdatalens --locale en

# Set log level
gwdatalens --log-level DEBUG

# Combine multiple options
gwdatalens --debug --port 9000 --locale en --log-level DEBUG
```

## Programmatic Access

### Using the Configuration Manager

```python
from gwdatalens.app.config import config

# Get configuration values
debug = config.get("DEBUG")
port = config.get("PORT")
locale = config.get("LOCALE")

# Get database configuration
db_config = config.get_database_config()
# Returns: {"host": "...", "port": ..., "database": "...", "user": "...", "password": "..."}

# Check if database configuration exists
if config.has_database_config():
    print("Database configuration available")

# Update configuration at runtime (e.g., from CLI)
config.update_from_cli(debug=True, port=8080)

# Get all settings as dictionary
config.to_dict()
```

## Troubleshooting

### Configuration not loading

Check the logs for configuration loading messages:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Database connection fails

1. Verify `database.toml` exists and has correct credentials
2. Check environment variables: `echo $GWDATALENS_DB_HOST`
3. Test database connection manually:

```bash
psql -h localhost -p 5432 -U username -d database_name
```

### Environment variables not working

Ensure proper prefix: `GWDATALENS_` (not `GW_DATALENS_` or `GWDATALENS`)

### CLI arguments ignored

CLI arguments only override if explicitly provided:

```bash
gwdatalens --port 8080  # Works
gwdatalens port=8080    # Doesn't work
```
