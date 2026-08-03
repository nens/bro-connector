import datetime
import logging
import time
import xml.etree.ElementTree as ET
from typing import Any

import requests

logger = logging.getLogger(__name__)


OBSERVATION_NAMESPACE = {
    "gco": "http://www.isotc211.org/2005/gco",
    "swe": "http://www.opengis.net/swe/2.0",
    "xlink": "http://www.w3.org/1999/xlink",
    "gldcommon": "http://www.broservices.nl/xsd/gldcommon/1.0",
    "brocom": "http://www.broservices.nl/xsd/brocommon/3.0",
    "gmd": "http://www.isotc211.org/2005/gmd",
    "gml": "http://www.opengis.net/gml/3.2",
    "om": "http://www.opengis.net/om/2.0",
    "waterml": "http://www.opengis.net/waterml/2.0",
    "": "http://www.broservices.nl/xsd/dsgld/1.0",  # Default namespace (empty prefix)
}


def datetime_or_none(
    string: str | None, max_val: bool = False
) -> datetime.datetime | None:
    """DD-MM-YYYY to Datetime.Date"""
    addition = "T23:59:59" if max_val else "T00:00:00"
    if string:
        datetime_val = datetime.datetime.strptime(
            f"{string}{addition}", "%d-%m-%YT%H:%M:%S"
        )
        datetime_val = datetime_val.replace(tzinfo=datetime.UTC)
        return datetime_val


def date_or_none(string: str | None) -> datetime.date | None:
    """DD-MM-YYYY to Datetime.Date"""
    if string:
        return datetime.datetime.strptime(string, "%d-%m-%Y").date()


def observation_summary(bro_url: str, bro_id: str) -> list[dict[str, Any]]:
    url = f"{bro_url}/gm/gld/v1/objects/{bro_id}/observationsSummary"
    attempt = 0
    max_retries = 3
    while attempt < max_retries:
        try:
            r = requests.get(url, timeout=30)

            if r.status_code == 429:
                # Rate limit hit
                retry_after = r.headers.get("Retry-After")
                wait_time = float(retry_after) if retry_after else 5.0  # default 5s
                logger.warning(
                    f"Rate limited. Waiting {wait_time} seconds before retrying..."
                )
                time.sleep(wait_time)
                attempt += 1
                continue  # retry

            r.raise_for_status()
            data = r.json()

            if not data:
                logger.info(f"No observations found for {bro_id}.")
                return []

            return data

        except Exception as e:
            logger.error(f"Error fetching observations: {e}")
            return []

    logger.error(f"Max retries exceeded for {bro_id}.")
    return []


def procedure_information(bro_url: str, bro_id: str, observation_id: str):
    url = f"{bro_url}/gm/gld/v1/objects/{bro_id}/observations/{observation_id}?startTVPTime=1900-01-01T00%3A00%3A00&endTVPTime=1900-01-01T00%3A00%3A00"
    r = requests.get(url=url)
    r.raise_for_status()
    observation_tree = ET.fromstring(r.content)
    observation_element = observation_tree.find(
        ".//observation", namespaces=OBSERVATION_NAMESPACE
    )
    return observation_element


def format_procedure(observation: ET.Element) -> dict:
    procedure = {}

    named_values = observation.findall(".//om:NamedValue", OBSERVATION_NAMESPACE)
    for named_value in named_values:
        name = (
            getattr(named_value.find(".//om:name", OBSERVATION_NAMESPACE), "attrib", {})
            .get("{http://www.w3.org/1999/xlink}href", "None:None")
            .split(":")[-1]
        )
        if name == "principalInvestigator":
            value = named_value.find(".//om:value", OBSERVATION_NAMESPACE)
            if value:
                procedure.update(
                    {
                        "InvestigatorKvk": getattr(
                            value.find(
                                ".//gldcommon:chamberOfCommerceNumber",
                                OBSERVATION_NAMESPACE,
                            ),
                            "text",
                            None,
                        ),
                    }
                )
        else:
            value = getattr(
                named_value.find(".//om:value", OBSERVATION_NAMESPACE), "text", None
            )
            procedure.update({name: value})

    process_reference_element = observation.find(
        ".//waterml:processReference", OBSERVATION_NAMESPACE
    )
    if process_reference_element is not None:
        process_reference = process_reference_element.attrib.get(
            "{http://www.w3.org/1999/xlink}href", "None:None"
        ).split(":")[-1]
    else:
        process_reference = None

    procedure.update(
        {
            "ProcessReference": process_reference,
            "ResultTime": getattr(
                observation.find(".//om:resultTime", OBSERVATION_NAMESPACE).find(
                    ".//gml:timePosition", OBSERVATION_NAMESPACE
                ),
                "text",
                None,
            ),
        }
    )
    try:
        procedure.update(
            {
                "InvestigatorKvk": getattr(
                    observation.find(
                        ".//gldcommon:chamberOfCommerceNumber", OBSERVATION_NAMESPACE
                    ),
                    "text",
                    None,
                )
            }
        )
    except AttributeError:
        logger.info("No chamberOfCommerceNumber found.")

    return procedure
