from urllib.parse import urljoin, urlsplit

from django.conf import settings
from django.urls import NoReverseMatch, reverse


def _extract_origin(url: str) -> str:
    """Return scheme://netloc from a URL-like value, or an empty string."""
    if not url:
        return ""
    parsed = urlsplit(url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def get_measurements_update_api_url(default_path: str) -> str:
    """Resolve the GLD measurement update endpoint for embedded GWDatalens.

    Resolution order:
    1. Named Django URL route
    2. Provided default path fallback
    3. Absolute host from BRO_CONNECTOR_BASE_URL setting
    4. Absolute host from first CSRF_TRUSTED_ORIGINS entry

    Returns an absolute URL when a host is available, otherwise a relative path.
    """
    try:
        path = reverse("gld_api:observation-measurements-update")
    except NoReverseMatch:
        path = default_path

    if not path.startswith("/"):
        path = f"/{path}"

    base_url = _extract_origin(getattr(settings, "BRO_CONNECTOR_BASE_URL", ""))
    if not base_url:
        trusted_origins = getattr(settings, "CSRF_TRUSTED_ORIGINS", []) or []
        if trusted_origins:
            base_url = _extract_origin(trusted_origins[0])

    if not base_url:
        return path

    return urljoin(f"{base_url}/", path.lstrip("/"))
