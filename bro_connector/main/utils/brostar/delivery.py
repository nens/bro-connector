import time
from typing import Literal

import requests

from config import REGISTRATION_TYPES, Config, UniqueRegistrationTypes


def _validate_registration_type(registration_type: str) -> bool:
    return registration_type in REGISTRATION_TYPES


def check_status(brostar_s: requests.Session, url: str) -> requests.Response:
    brostar_s.post(f"{url}check_status/")
    res = brostar_s.get(url, timeout=15)
    res.raise_for_status()
    return res


def create_brostar_metadata(
    object_id: str,
    request_reference: str,
    quality_regime: Literal["IMBRO", "IMBRO/A"],
    kvk: str,
) -> dict:
    data = {}
    bro_id = None
    if object_id.startswith(("GMW", "GMN", "GLD", "FRD")):
        bro_id = object_id

    if bro_id:
        data = {
            "broId": bro_id,
            "correctionReason": "eigenCorrectie",
        }

    data.update(
        {
            "requestReference": request_reference,
            "deliveryAccountableParty": kvk,
            "qualityRegime": quality_regime,
        }
    )

    if quality_regime == "IMBRO/A" and not object_id.startswith("GMN"):
        data.update({"underPrivilege": "ja"})

    return data


def create_brostar_task(
    brostar_s: requests.Session,
    data: dict,
    registration_type: UniqueRegistrationTypes,
    config: Config,
) -> requests.Response:
    """
    well_information: \n dict = {\n
        'bericht_type': registrate, replace, delete.
        'metadata': BROSTAR Metadata (use function).
        'sourcedoc_data: All information in a dictionary required to generate the sourcedocument of choice.\n
    }
    """
    if not _validate_registration_type(registration_type):
        raise ValueError(
            f"Registration type: {registration_type} unknown. Pick one of: {REGISTRATION_TYPES}."
        )

    bro_type = registration_type.split(sep="_")[0]

    payload = {
        "bro_domain": f"{bro_type}",
        "project_number": config.project_number,
        "registration_type": registration_type,
        "request_type": data["request_type"],
        "metadata": data["metadata"],
        "sourcedocument_data": data["sourcedocument_data"],
    }
    r = brostar_s.post(
        f"{config.brostar_base_url}/uploadtasks/", json=payload, timeout=60
    )
    print(
        f"Created BROSTAR task for {registration_type}, status code: {r.status_code}."
    )
    if r.status_code < 250:
        time.sleep(3)
        res = brostar_s.get(r.json()["url"], timeout=30)
        res.raise_for_status()
    else:
        res = r
    return res
