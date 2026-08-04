import logging
from typing import Any
from urllib.parse import urlsplit

import pandas as pd
from gwdatalens.app.config import config
from gwdatalens.app.constants import (
    TimeRangeDefaults,
)

logger = logging.getLogger(__name__)


def is_absolute_http_url(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlsplit(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def resolve_bro_connector_api_url() -> str:
    """Resolve API target for qualifier export.

    Priority:
    1. Explicit BRO_CONNECTOR_API_URL
    2. Django-aware dynamic URL resolution (when embedded)
    3. Fallback to BRO_CONNECTOR_API_ENDPOINT
    """
    configured_url = config.get("BRO_CONNECTOR_API_URL")
    if is_absolute_http_url(configured_url):
        return configured_url

    endpoint_path = config.get(
        "BRO_CONNECTOR_API_ENDPOINT", "/api/gld/observation/measurements/"
    )

    if config.get("DJANGO_APP"):
        try:
            from main.utils.gwdatalens_api import get_measurements_update_api_url

            resolved = get_measurements_update_api_url(default_path=endpoint_path)
            if is_absolute_http_url(resolved):
                return resolved
        except Exception as e:
            logger.warning("Failed to resolve Django API URL dynamically: %s", e)

    if is_absolute_http_url(endpoint_path):
        return endpoint_path

    raise ValueError(
        "BRO connector API URL is not absolute. Configure one of: "
        "BRO_CONNECTOR_API_URL, GWDATALENS_BRO_CONNECTOR_API_URL, "
        "or set Django BRO_CONNECTOR_BASE_URL for dynamic resolution."
        ""
    )


def build_django_session_forwarding_context() -> dict[str, Any]:
    """Build request kwargs to forward Django session auth when available.

    Returns a dict that can be merged into ``requests.post`` kwargs. The
    result may contain ``cookies`` and ``headers`` with session and CSRF
    context from the active Django request.
    """
    if not config.get("DJANGO_APP"):
        return {}

    try:
        from main.settings.user import get_current_request
    except Exception as e:
        logger.debug("Unable to import Django request helper: %s", e)
        return {}

    request = get_current_request()
    if request is None:
        logger.debug("No active Django request found for session forwarding.")
        return {}

    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        logger.debug("Active request has no authenticated user.")
        return {}

    session_cookie_name = "sessionid"
    csrf_cookie_name = "csrftoken"
    try:
        from django.conf import settings

        session_cookie_name = getattr(
            settings, "SESSION_COOKIE_NAME", session_cookie_name
        )
        csrf_cookie_name = getattr(settings, "CSRF_COOKIE_NAME", csrf_cookie_name)
    except Exception as e:
        logger.debug("Unable to load Django cookie settings: %s", e)

    cookies: dict[str, str] = {}
    headers: dict[str, str] = {}

    session_cookie = request.COOKIES.get(session_cookie_name)
    if not session_cookie:
        session_cookie = getattr(getattr(request, "session", None), "session_key", None)
    if session_cookie:
        cookies[session_cookie_name] = session_cookie

    csrf_token = request.COOKIES.get(csrf_cookie_name) or request.META.get(
        "CSRF_COOKIE"
    )
    if csrf_token:
        cookies[csrf_cookie_name] = csrf_token
        headers["X-CSRFToken"] = csrf_token

    # Provide same-origin headers so Django CSRF checks can validate HTTPS
    # requests that rely on SessionAuthentication.
    try:
        origin = request.build_absolute_uri("/").rstrip("/")
    except Exception:
        origin = ""
    if origin:
        headers.setdefault("Referer", f"{origin}/")
        headers.setdefault("Origin", origin)

    if not cookies:
        logger.debug("No session cookies available to forward.")
        return {}

    return {
        "cookies": cookies,
        "headers": headers,
    }


def build_api_auth_kwargs() -> dict[str, Any]:
    """Build auth-related kwargs for BRO connector API requests.

    Supported auth modes:
    - ``auto`` (default): try Django session forwarding first, then Basic Auth
    - ``session``: use only Django session forwarding
    - ``basic``: use only configured Basic Auth credentials
    """
    raw_mode = config.get("BRO_CONNECTOR_AUTH_MODE", "auto")
    auth_mode = str(raw_mode).strip().lower() if raw_mode is not None else "auto"
    if auth_mode not in {"auto", "session", "basic"}:
        logger.warning(
            "Invalid BRO_CONNECTOR_AUTH_MODE='%s'; defaulting to 'auto'.",
            raw_mode,
        )
        auth_mode = "auto"

    def basic_auth_kwargs() -> dict[str, Any]:
        username = config.get("BRO_CONNECTOR_USERNAME")
        password = config.get("BRO_CONNECTOR_PASSWORD")
        if username and password:
            return {"auth": (username, password)}
        return {}

    if auth_mode in {"auto", "session"}:
        session_context = build_django_session_forwarding_context()
        if session_context:
            logger.debug("Using forwarded Django session authentication context.")
            return session_context
        if auth_mode == "session":
            logger.warning(
                "BRO_CONNECTOR_AUTH_MODE='session' but no Django session "
                "context is available for forwarding."
            )
            return {}

    basic_context = basic_auth_kwargs()
    if basic_context:
        if auth_mode == "basic":
            logger.debug("Using BRO connector Basic Authentication (forced mode).")
        else:
            logger.debug("Using BRO connector Basic Authentication (fallback).")
        return basic_context

    logger.warning(
        "No BRO connector authentication context available (mode='%s').",
        auth_mode,
    )
    return {}


def resolve_bro_connector_api_timeout_seconds() -> float:
    """Resolve request timeout for BRO connector API calls in seconds."""
    raw_timeout = config.get("BRO_CONNECTOR_API_TIMEOUT_SECONDS", 30)
    try:
        timeout_seconds = float(raw_timeout)
    except (TypeError, ValueError):
        logger.warning(
            "Invalid BRO_CONNECTOR_API_TIMEOUT_SECONDS='%s'; using 30s.",
            raw_timeout,
        )
        return 30.0

    if timeout_seconds <= 0:
        logger.warning(
            "BRO_CONNECTOR_API_TIMEOUT_SECONDS must be > 0 (got %s); using 30s.",
            timeout_seconds,
        )
        return 30.0

    return timeout_seconds


def serialize_measurement_time_for_api(value: Any) -> str:
    """Serialize measurement timestamp as an explicit UTC instant.

    Export rows currently use timezone-naive local clock timestamps. Sending
    naive datetime strings allows the API server to reinterpret them in its own
    timezone context, which can shift instants around DST boundaries.
    """
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize(TimeRangeDefaults.LOCAL_TIMEZONE)
    return ts.tz_convert("UTC").isoformat()
