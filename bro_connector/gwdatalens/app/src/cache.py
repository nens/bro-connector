"""Caching utilities for standalone and Django modes.

Cache is only active in standalone Dash mode to avoid conflicts with Django's
caching implementation.
"""

from flask_caching import Cache

from gwdatalens.app.config import config
from gwdatalens.app.constants import ConfigDefaults

# Flask-Caching instance (only used in standalone mode)
cache = Cache()


def conditional_cache(timeout=ConfigDefaults.CACHE_TIMEOUT):
    """Decorator that conditionally caches based on application mode.

    In Django mode: returns the original function (no caching).
    In standalone mode: uses Flask-Caching's memoize for robust caching.
    """

    def decorator(func):
        if config.get("DJANGO_APP", False):
            # Django mode: no caching
            return func

        # Standalone mode: apply cache.memoize
        return cache.memoize(timeout=timeout)(func)

    return decorator
