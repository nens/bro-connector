import logging

import requests
from django.conf import settings
from requests.adapters import HTTPAdapter, Retry
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

def setup_brostar_session(brostar_api_key: str | None) -> requests.Session:
    if not brostar_api_key:
        raise ValueError("No BROSTAR API key provided.")

    s = requests.Session()
    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "POST", "PATCH"],
        connect=5,  # Number of retries on connection errors like ConnectTimeout
        read=5,  # Number of retries on read timeouts
        raise_on_status=False,  # Optional, if you want to suppress exceptions on bad status
    )
    s.auth = HTTPBasicAuth(username="__key__", password=brostar_api_key)
    s.headers = {"Content-Type": "application/json"}
    adapter = HTTPAdapter(max_retries=retry_strategy)
    # Mount the adapter to the session for both http and https
    s.mount("http://", adapter)
    s.mount("https://", adapter)

    return s

def send_to_brostar(message) -> None:
    """
    Send a Message instance to the BROSTAR API as an upload task.

    Called from the post_save signal on creation. Updates the message's
    status, brostar_task_id, brostar_task_url, and bro_errors fields in-place
    using update_fields to avoid triggering the signal again.

    Args:
        message: A concrete Message subclass instance (GMWMessage, GLDMessage, …).
    """
    # Resolve the organisation from the linked BRO project.
    if message.bro_project is None:
        logger.error(
            "Cannot send message %s to BROSTAR: bro_project is not set.", message.pk
        )
        _mark_failed(message, {"error": "bro_project is not set on the message."})
        return

    organisation = message.bro_project.owner
    if organisation is None:
        logger.error(
            "Cannot send message %s to BROSTAR: bro_project has no owner.", message.pk
        )
        _mark_failed(message, {"error": "bro_project has no owner organisation."})
        return

    brostar_token = organisation.brostar_token
    if not brostar_token:
        logger.error(
            "Cannot send message %s to BROSTAR: organisation %s has no brostar_token.",
            message.pk,
            organisation.pk,
        )
        _mark_failed(
            message,
            {"error": f"Organisation {organisation} has no brostar_token configured."},
        )
        return

    session = setup_brostar_session(brostar_token)

    bro_domain = message.registration_type.split("_")[0]
    payload = {
        "bro_domain": bro_domain,
        "project_number": str(message.bro_project.project_number),
        "registration_type": message.registration_type,
        "request_type": message.request_type,
        "metadata": message.metadata or {},
        "sourcedocument_data": message.sourcedocument_data or {},
    }

    brostar_url = getattr(settings, "BROSTAR_URL", "https://staging.brostar.nl/api")
    url = f"{brostar_url}/uploadtasks/"

    headers = {"Authorization": f"Token {brostar_token}"}

    try:
        response = session.post(url, json=payload, headers=headers, timeout=60)
    except requests.RequestException as exc:
        logger.exception(
            "Network error while sending message %s to BROSTAR: %s", message.pk, exc
        )
        _mark_failed(message, {"error": str(exc)})
        return

    if response.status_code < 300:
        data = response.json()
        task_url = data.get("url", "")
        task_id = str(data.get("id", ""))
        message.__class__.objects.filter(pk=message.pk).update(
            status="processing",
            brostar_task_url=task_url,
            brostar_task_id=task_id,
        )
        logger.info(
            "Message %s sent to BROSTAR successfully. Task URL: %s", message.pk, task_url
        )
    else:
        try:
            error_body = response.json()
        except Exception:
            error_body = {"raw": response.text}
        logger.error(
            "BROSTAR returned %s for message %s: %s",
            response.status_code,
            message.pk,
            error_body,
        )
        _mark_failed(message, {"status_code": response.status_code, "detail": error_body})


def _mark_failed(message, errors: dict) -> None:
    message.__class__.objects.filter(pk=message.pk).update(
        status="failed",
        bro_errors=errors,
    )
