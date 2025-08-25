from django.utils.cache import _generate_cache_key
from django.utils.hashable import make_hashable

from django.utils.encoding import iri_to_uri

def ignore_query_params_key_func(key, key_prefix, version):
    """
    Return a cache key that ignores query parameters.
    This assumes `key` is the full request path + query string.
    """
    print(key)
    base_path = key.split("?", 1)[0]  # Remove query string
    print("base_path: ", base_path)
    return "%s:%s:%s" % (key_prefix, version, iri_to_uri(base_path))

def unified_map_key_func(key, key_prefix, version):
    """
    Cache key function that:
    - Ignores query parameters
    - Treats /map/ and /map/validation/ the same
    """
    base_path = key.split("?", 1)[0]  # Strip query string

    # Normalize paths
    if base_path.startswith("/map/validation/") or base_path.rstrip("/") == "/map":
        normalized = "/map"
    else:
        normalized = base_path.rstrip("/")
    print("normalized: ", normalized)

    return "%s:%s:%s" % (key_prefix, version, iri_to_uri(normalized))