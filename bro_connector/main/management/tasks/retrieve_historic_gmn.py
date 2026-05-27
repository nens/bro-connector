import logging

import requests
import xmltodict
from django.conf import settings
from gmn.models import GroundwaterMonitoringNet, MeasuringPoint
from gmw.models import GroundwaterMonitoringTubeStatic, GroundwaterMonitoringWellStatic

from ..tasks.import_checker import get_last_import_date, should_import
from ..tasks.kvk_handler import DataRetrieverKVK
from ..tasks.progressor import Progress

logger = logging.getLogger(__name__)


def _parse_date(value) -> str | None:
    """Extract date string from a brocom:date dict or plain string."""
    if value is None:
        return None
    if isinstance(value, dict):
        return value.get("brocom:date") or value.get("brocom:year")
    return value


def _text_or_none(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return value.get("#text")
    return value


def handle_individual_bro_id(gmn_id: str, last_import_date=None) -> dict | None:
    logger.info(f"Processing GMN: {gmn_id}")

    if not should_import(gmn_id, "gmn", last_import_date):
        logger.info(f"Skipping {gmn_id} – already up to date.")
        return None

    bro_url = getattr(
        settings, "BRO_UITGIFTE_SERVICE_URL", "https://publiek.broservices.nl"
    )
    url = f"{bro_url}/gm/gmn/v1/objects/{gmn_id}?fullHistory=nee"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
    except Exception as e:
        logger.error(f"Could not download GMN XML for {gmn_id}: {e}")
        return None

    try:
        json_data = xmltodict.parse(r.content)
    except Exception as e:
        logger.error(f"Could not parse GMN XML for {gmn_id}: {e}")
        return None

    dispatch = json_data.get("dispatchDataResponse", {}).get("dispatchDocument", {})

    if "GMN_PPO" not in dispatch:
        logger.info(f"GMN_PPO not found for {gmn_id}, skipping.")
        return None

    gmn_ppo = dispatch["GMN_PPO"]

    measuringpoint_data = gmn_ppo.get("measuringPoint", [])
    if isinstance(measuringpoint_data, dict):
        measuringpoint_data = [measuringpoint_data]

    gmn_obj = _save_gmn_data(gmn_ppo)
    if gmn_obj is None:
        return None

    _save_measuringpoints(gmn_obj, measuringpoint_data)
    return {"ids_found": 1, "imported": 1}


def _save_gmn_data(gmn_ppo: dict) -> GroundwaterMonitoringNet | None:
    bro_id = gmn_ppo.get("brocom:broId")
    if not bro_id:
        return None

    history = gmn_ppo.get("monitoringNetHistory", {})
    start_date = _parse_date(history.get("startDateMonitoring"))

    try:
        gmn_obj, _ = GroundwaterMonitoringNet.objects.update_or_create(
            gmn_bro_id=bro_id,
            defaults={
                "quality_regime": gmn_ppo.get("brocom:qualityRegime") or "",
                "name": gmn_ppo.get("name") or bro_id,
                "delivery_context": (
                    _text_or_none(gmn_ppo.get("deliveryContext")) or ""
                ),
                "monitoring_purpose": (
                    _text_or_none(gmn_ppo.get("monitoringPurpose")) or ""
                ),
                "groundwater_aspect": (
                    _text_or_none(gmn_ppo.get("groundwaterAspect")) or ""
                ),
                "start_date_monitoring": start_date,
                "province_name": "",
                "bro_domain": "GMN",
                "deliver_to_bro": True,
                "object_id_accountable_party": bro_id,
            },
        )
        return gmn_obj
    except Exception as e:
        logger.error(f"Could not save GroundwaterMonitoringNet for {bro_id}: {e}")
        return None


def _save_measuringpoints(
    gmn_obj: GroundwaterMonitoringNet, measuringpoint_data: list
) -> None:
    for mp_item in measuringpoint_data:
        mp_data = mp_item.get("MeasuringPoint") if isinstance(mp_item, dict) else None
        if not mp_data or not isinstance(mp_data, dict):
            mp_data = mp_item

        mp_start_date = _parse_date(mp_data.get("startDate"))
        mp_end_date = _parse_date(mp_data.get("endDate"))

        monitoring_tubes = mp_data.get("monitoringTube", {})
        if isinstance(monitoring_tubes, dict):
            monitoring_tubes = [monitoring_tubes]

        # Use the last (most recent) tube reference
        tube_ref = monitoring_tubes[-1] if monitoring_tubes else {}
        tube_data = tube_ref.get("GroundwaterMonitoringTube") or tube_ref

        gmw_bro_id = tube_data.get("broId")
        tube_number = tube_data.get("tubeNumber")

        if not gmw_bro_id or tube_number is None:
            continue

        try:
            gmws = GroundwaterMonitoringWellStatic.objects.get(bro_id=gmw_bro_id)
            tube = GroundwaterMonitoringTubeStatic.objects.get(
                groundwater_monitoring_well_static=gmws,
                tube_number=tube_number,
            )
        except (
            GroundwaterMonitoringWellStatic.DoesNotExist,
            GroundwaterMonitoringTubeStatic.DoesNotExist,
            GroundwaterMonitoringTubeStatic.MultipleObjectsReturned,
        ):
            logger.warning(
                f"Tube not found for GMW {gmw_bro_id}, tube {tube_number} – "
                "skipping measuring point."
            )
            continue

        try:
            MeasuringPoint.objects.update_or_create(
                gmn=gmn_obj,
                groundwater_monitoring_tube=tube,
                defaults={
                    "added_to_gmn_date": mp_start_date,
                    "deleted_from_gmn_date": mp_end_date,
                },
            )
        except Exception as e:
            logger.error(
                f"Could not save MeasuringPoint for GMN {gmn_obj.gmn_bro_id}, "
                f"tube {gmw_bro_id}_{tube_number}: {e}"
            )


def run(kvk_number: str = None, bro_type: str = "gmn", **kwargs) -> dict:
    progressor = Progress()

    if kvk_number is None:
        logger.warning("No kvk_number provided for GMN import.")
        return {"ids_found": 0, "imported": 0}

    DR = DataRetrieverKVK(kvk_number)
    DR.request_bro_ids("gmn")
    DR.get_ids_kvk()
    ids = DR.gmn_ids
    ids_ini_count = len(ids)

    print(f"{ids_ini_count} GMN BRO IDs found for organisation {kvk_number}.")

    last_import_date = get_last_import_date("gmn")
    progressor.calibrate(ids, 25)

    imported = 0
    for gmn_id in ids:
        result = handle_individual_bro_id(gmn_id, last_import_date=last_import_date)
        if result:
            imported += 1
        progressor.next()
        progressor.progress()

    return {"ids_found": ids_ini_count, "imported": imported}
