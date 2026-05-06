import logging
import datetime
import requests
import xmltodict
from django.conf import settings
from gar.models import (
    FieldObservations,
    FieldSamples,
    GroundwaterCompositionResearches,
)
from gmw.models import GroundwaterMonitoringTubeStatic, GroundwaterMonitoringWellStatic

from ..tasks.import_checker import get_last_import_date, should_import
from ..tasks.kvk_handler import DataRetrieverKVK
from ..tasks.progressor import Progress

logger = logging.getLogger(__name__)


def _parse_date(value) -> str | None:
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


def _bool_or_none(value) -> bool | None:
    """Convert 'ja'/'nee' strings to bool, or pass through booleans."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    mapping = {"ja": True, "nee": False, "true": True, "false": False}
    return mapping.get(str(value).lower())


def handle_individual_bro_id(gar_id: str, last_import_date=None) -> dict | None:
    logger.info(f"Processing GAR: {gar_id}")

    if not should_import(gar_id, "gar", last_import_date):
        logger.info(f"Skipping {gar_id} – already up to date.")
        return None

    bro_url = getattr(
        settings, "BRO_UITGIFTE_SERVICE_URL", "https://publiek.broservices.nl"
    )
    url = f"{bro_url}/gm/gar/v1/objects/{gar_id}?fullHistory=nee"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
    except Exception as e:
        logger.error(f"Could not download GAR XML for {gar_id}: {e}")
        return None

    try:
        json_data = xmltodict.parse(r.content)
    except Exception as e:
        logger.error(f"Could not parse GAR XML for {gar_id}: {e}")
        return None

    dispatch = json_data.get("dispatchDataResponse", {}).get("dispatchDocument", {})

    if "GAR_O" not in dispatch:
        logger.info(f"GAR_O not found for {gar_id}, skipping.")
        return None

    gar_data = dispatch["GAR_O"]

    monitoring_point_data = (
        gar_data.get("monitoringPoint", {}).get(
            "garcommon:GroundwaterMonitoringTube", {}
        )
        or {}
    )
    gmw_bro_id = monitoring_point_data.get("garcommon:broId")
    tube_number = monitoring_point_data.get("garcommon:tubeNumber")

    monitoring_tube_id = None
    if gmw_bro_id and tube_number is not None:
        try:
            gmws = GroundwaterMonitoringWellStatic.objects.get(bro_id=gmw_bro_id)
            tube = GroundwaterMonitoringTubeStatic.objects.get(
                groundwater_monitoring_well_static=gmws,
                tube_number=tube_number,
            )
            monitoring_tube_id = tube.pk
        except (
            GroundwaterMonitoringWellStatic.DoesNotExist,
            GroundwaterMonitoringTubeStatic.DoesNotExist,
            GroundwaterMonitoringTubeStatic.MultipleObjectsReturned,
        ):
            logger.warning(
                f"Tube not found for GMW {gmw_bro_id}, tube {tube_number}."
            )

    # GroundwaterCompositionResearches – main GAR record (local_id stores BRO ID)
    try:
        gcr, _ = GroundwaterCompositionResearches.objects.update_or_create(
            local_id=gar_id,
            bro_id=gar_data.get("brocom:broId"),
            defaults={
                "groundwater_monitoring_tube_id": monitoring_tube_id,
                "assessment_procedure_id": _text_or_none(
                    gar_data.get("qualityControlMethod")
                ),
            },
        )
    except Exception as e:
        logger.error(
            f"Could not save GroundwaterCompositionResearches for {gar_id}: {e}"
        )
        return None

    field_research_data = gar_data.get("fieldResearch") or {}
    _save_field_sample(gcr, gar_data, field_research_data)

    return {"ids_found": 1, "imported": 1}


def _save_field_sample(
    gcr: GroundwaterCompositionResearches,
    gar_data: dict,
    field_research_data: dict,
) -> None:
    delivery_accountable_party = gar_data.get("brocom:deliveryAccountableParty")
    dap_int = None
    if delivery_accountable_party:
        try:
            dap_int = int(str(delivery_accountable_party).strip())
        except (ValueError, TypeError):
            pass

    sampling_device = field_research_data.get("garcommon:samplingDevice") or {}
    pump_type = _text_or_none(sampling_device.get("garcommon:pumpType"))
    sampling_date_time_str = field_research_data.get(
        "garcommon:samplingDateTime"
    )
    sampling_date_time = datetime.datetime.fromisoformat(sampling_date_time_str) if sampling_date_time_str else None
    try:
        field_sample, _ = FieldSamples.objects.update_or_create(
            groundwater_composition_research_id=gcr.pk,
            defaults={
                "delivery_accountable_party": dap_int,
                "quality_control_method": _text_or_none(
                    gar_data.get("qualityControlMethod")
                ),
                "sampling_datetime": sampling_date_time,
                "sampling_standard": _text_or_none(
                    field_research_data.get("garcommon:samplingStandard")
                ),
                "pump_type": pump_type,
            },
        )
    except Exception as e:
        logger.error(
            f"Could not save FieldSamples for GAR {gcr.local_id}: {e}"
        )
        return

    field_observation_data = field_research_data.get("garcommon:fieldObservation") or {}
    _save_field_observation(field_sample, field_observation_data)


def _save_field_observation(
    field_sample: FieldSamples, field_observation_data: dict
) -> None:
    if not field_observation_data:
        return

    try:
        FieldObservations.objects.update_or_create(
            field_sample_id=field_sample.pk,
            defaults={
                "abnormality_in_cooling": _bool_or_none(
                    field_observation_data.get("garcommon:abnormalityInCooling")
                ),
                "abnormality_in_device": _bool_or_none(
                    field_observation_data.get("garcommon:abnormalityInDevice")
                ),
                "polluted_by_engine": _bool_or_none(
                    field_observation_data.get("garcommon:pollutedByEngine")
                ),
                "filter_aerated": _bool_or_none(
                    field_observation_data.get("garcommon:filterAerated")
                ),
                "groundwater_level_dropped_too_much": _bool_or_none(
                    field_observation_data.get(
                        "garcommon:groundWaterLevelDroppedTooMuch"
                    )
                ),
                "abnormal_filter": _bool_or_none(
                    field_observation_data.get("garcommon:abnormalFilter")
                ),
                "sample_aerated": _bool_or_none(
                    field_observation_data.get("garcommon:sampleAerated")
                ),
                "hose_reused": _bool_or_none(
                    field_observation_data.get("garcommon:hoseReused")
                ),
                "temperature_difficult_to_measure": _bool_or_none(
                    field_observation_data.get(
                        "garcommon:temperatureDifficultToMeasure"
                    )
                ),
            },
        )
    except Exception as e:
        logger.error(
            f"Could not save FieldObservations for FieldSample {field_sample.pk}: {e}"
        )


def run(kvk_number: str = None, bro_type: str = "gar", **kwargs) -> dict:
    progressor = Progress()

    if kvk_number is None:
        logger.warning("No kvk_number provided for GAR import.")
        return {"ids_found": 0, "imported": 0}

    DR = DataRetrieverKVK(kvk_number)
    DR.request_bro_ids("gar")
    DR.get_ids_kvk()
    ids = DR.gar_ids
    ids_ini_count = len(ids)

    print(f"{ids_ini_count} GAR BRO IDs found for organisation {kvk_number}.")

    last_import_date = get_last_import_date("gar")
    progressor.calibrate(ids, 25)

    imported = 0
    for gar_id in ids:
        result = handle_individual_bro_id(gar_id, last_import_date=last_import_date)
        if result:
            imported += 1
        progressor.next()
        progressor.progress()

    return {"ids_found": ids_ini_count, "imported": imported}
