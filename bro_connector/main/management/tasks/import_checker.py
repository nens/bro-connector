import datetime
import logging

import requests
from django.utils import timezone

logger = logging.getLogger(__name__)


def get_last_import_date(bro_type: str, default_days: int = 3650) -> datetime.datetime:
    """
    Returns the created_date of the last successfully executed BroImport for the given
    bro_type, or now() - default_days if no such import exists.
    """
    try:
        from tools.models import BroImport

        imports = (
            BroImport.objects.filter(bro_type=bro_type.upper(), executed=True)
            .order_by("-created_date")
        )
        if len(imports) > 1:
            last = imports[1]
            if last and last.created_date:
                return last.created_date
    except Exception as e:
        logger.warning(f"Could not query BroImport for last import date: {e}")

    return timezone.now() - datetime.timedelta(days=default_days)


def should_import(
    bro_id: str, bro_type: str, last_import_date: datetime.datetime | None
) -> bool:
    """
    Checks whether the BRO object should be (re-)imported.

    Queries the BRO public API for the object's registrationHistory dates and
    returns True if any of those is more recent than last_import_date, or if the
    check cannot be performed (fail-open).
    """
    if last_import_date is None:
        return True

    try:
        import xmltodict

        url = (
            f"https://publiek.broservices.nl/gm/{bro_type.lower()}/v1/objects/"
            f"{bro_id}?fullHistory=nee"
        )
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return True  # fail-open

        data = xmltodict.parse(r.content)
        dispatch = data.get("dispatchDataResponse", {}).get("dispatchDocument", {})

        for key, obj in dispatch.items():
            if not isinstance(obj, dict):
                continue
            reg_history = obj.get("registrationHistory", {})
            date_candidates = [
                reg_history.get("brocom:latestCorrectionTime"),
                reg_history.get("brocom:latestAdditionTime"),
                reg_history.get("brocom:objectRegistrationTime"),
            ]
            dates = []
            for d in date_candidates:
                if d:
                    try:
                        dt = datetime.datetime.fromisoformat(d)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=datetime.timezone.utc)
                        dates.append(dt)
                    except (ValueError, TypeError):
                        pass

            if not dates:
                return True  # no dates → always import

            if last_import_date.tzinfo is None:
                last_import_date = last_import_date.replace(
                    tzinfo=datetime.timezone.utc
                )

            logger.info(
                f"Found registration history dates for {bro_type}/{bro_id}: "
                f"{', '.join(d.isoformat() for d in dates)}; "
                f"last import date: {last_import_date.isoformat()}"
            )
            return max(dates) > last_import_date

        return True  # no recognised dispatch document key

    except Exception as e:
        logger.warning(f"should_import check failed for {bro_type}/{bro_id}: {e}")
        return True  # fail-open
