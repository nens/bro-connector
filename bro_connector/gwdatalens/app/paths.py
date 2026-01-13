"""Application paths and directory constants.

This module defines all path constants used throughout the application,
including paths to assets, locales, CSS, and other resources.
"""

from pathlib import Path

from gwdatalens.app.config import config

# Base application paths
GWDATALENS_APP_ROOT = Path(__file__).parent.parent
GWDATALENS_APP_PATH = Path(__file__).parent

# Asset paths depend on whether running as Django app or standalone
if config.get("DJANGO_APP"):
    ASSETS_PATH = GWDATALENS_APP_ROOT.parent / "static" / "dash"
else:
    ASSETS_PATH = GWDATALENS_APP_PATH.parent / "assets"

# Resource paths
LOCALE_PATH = ASSETS_PATH / "locale"
CUSTOM_CSS_PATH = str(ASSETS_PATH / "custom.css")
MAPBOX_ACCESS_TOKEN = str(ASSETS_PATH / ".mapbox_access_token")

__all__ = [
    "GWDATALENS_APP_ROOT",
    "GWDATALENS_APP_PATH",
    "ASSETS_PATH",
    "LOCALE_PATH",
    "CUSTOM_CSS_PATH",
    "MAPBOX_ACCESS_TOKEN",
]
