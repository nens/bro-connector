import logging

import requests
import xmltodict
from bro.models import Organisation
from django.conf import settings
from frd.models import (
    FormationResistanceDossier,
    GeoOhmMeasurementMethod,
    ElectromagneticMeasurementMethod,
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


def _get_or_create_organisation(kvk_number) -> Organisation | None:
    if kvk_number is None:
        return None
    try:
        number = int(str(kvk_number).strip())
        org, _ = Organisation.objects.get_or_create(company_number=number)
        return org
    except (ValueError, TypeError):
        return None


def handle_individual_bro_id(frd_id: str, last_import_date=None) -> dict | None:
    logger.info(f"Processing FRD: {frd_id}")

    if not should_import(frd_id, "frd", last_import_date):
        logger.info(f"Skipping {frd_id} – already up to date.")
        return None

    bro_url = getattr(
        settings, "BRO_UITGIFTE_SERVICE_URL", "https://publiek.broservices.nl"
    )
    url = f"{bro_url}/gm/frd/v1/objects/{frd_id}?fullHistory=nee"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
    except Exception as e:
        logger.error(f"Could not download FRD XML for {frd_id}: {e}")
        return None

    try:
        json_data = xmltodict.parse(r.content)
    except Exception as e:
        logger.error(f"Could not parse FRD XML for {frd_id}: {e}")
        return None

    dispatch = json_data.get("dispatchDataResponse", {}).get("dispatchDocument", {})

    if "FRD_O" not in dispatch:
        logger.info(f"FRD_O not found for {frd_id}, skipping.")
        return None

    frd_data = dispatch["FRD_O"]

    tube_data = (
        frd_data.get("groundwaterMonitoringTube", {})
        .get("frdcommon:MonitoringTube", {})
    )
    gmw_bro_id = tube_data.get("frdcommon:broId")
    tube_number = tube_data.get("frdcommon:tubeNumber")

    monitoring_tube = None
    if gmw_bro_id and tube_number is not None:
        try:
            gmws = GroundwaterMonitoringWellStatic.objects.get(bro_id=gmw_bro_id)
            monitoring_tube = GroundwaterMonitoringTubeStatic.objects.get(
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
                "saving FRD without tube reference."
            )

    delivery_accountable_party = _get_or_create_organisation(
        frd_data.get("brocom:deliveryAccountableParty")
    )

    try:
        frd_obj, _ = FormationResistanceDossier.objects.update_or_create(
            frd_bro_id=frd_data.get("brocom:broId"),
            defaults={
                "delivery_accountable_party": delivery_accountable_party,
                "quality_regime": frd_data.get("brocom:qualityRegime"),
                "assessment_type": _text_or_none(frd_data.get("determinationType")),
                "groundwater_monitoring_tube": monitoring_tube,
                "deliver_to_bro": True,
            },
        )
    except Exception as e:
        logger.error(f"Could not save FormationResistanceDossier for {frd_id}: {e}")
        return None

    _save_geo_ohm_measurements(frd_obj, frd_data, delivery_accountable_party)
    _save_electromagnetic_measurements(frd_obj, frd_data, delivery_accountable_party)

    return {"ids_found": 1, "imported": 1}


def _save_geo_ohm_measurements(
    frd_obj: FormationResistanceDossier,
    frd_data: dict,
    responsible_party: Organisation | None,
) -> None:
    raw = frd_data.get("relatedGeoElectricMeasurement")
    if not raw:
        return
    measurements = raw if isinstance(raw, list) else [raw]

    GeoOhmMeasurementMethod.objects.filter(
        formation_resistance_dossier=frd_obj
    ).delete()

    for item in measurements:
        gem_data = item.get("frdcommon:GeoElectricMeasurement", {})
        measurement_date = _parse_date(gem_data.get("frdcommon:measurementDate"))
        measuring_procedure = (
            _text_or_none(gem_data.get("frdcommon:determinationProcedure"))
            or "onbekend"
        )
        assessment_procedure = (
            _text_or_none(gem_data.get("frdcommon:evaluationProcedure")) or "onbekend"
        )

        if responsible_party is None:
            logger.warning(
                "No responsible party available for GeoOhmMeasurementMethod – skipping."
            )
            continue

        if measurement_date is None:
            continue

        try:
            GeoOhmMeasurementMethod.objects.create(
                formation_resistance_dossier=frd_obj,
                measurement_date=measurement_date,
                measuring_responsible_party=responsible_party,
                measuring_procedure=measuring_procedure,
                assessment_procedure=assessment_procedure,
            )
        except Exception as e:
            logger.error(
                f"Could not save GeoOhmMeasurementMethod for FRD "
                f"{frd_obj.frd_bro_id}: {e}"
            )


def _save_electromagnetic_measurements(
    frd_obj: FormationResistanceDossier,
    frd_data: dict,
    responsible_party: Organisation | None,
) -> None:
    raw = frd_data.get("relatedElectromagneticMeasurement")
    if not raw:
        return
    measurements = raw if isinstance(raw, list) else [raw]

    ElectromagneticMeasurementMethod.objects.filter(
        formation_resistance_dossier=frd_obj
    ).delete()

    for item in measurements:
        em_data = item.get("frdcommon:ElectromagneticMeasurement", {})
        measurement_date = _parse_date(em_data.get("frdcommon:measurementDate"))
        measuring_procedure = (
            _text_or_none(em_data.get("frdcommon:determinationProcedure")) or "onbekend"
        )
        assessment_procedure = (
            _text_or_none(em_data.get("frdcommon:evaluationProcedure")) or "onbekend"
        )

        if responsible_party is None:
            continue

        if measurement_date is None:
            continue

        try:
            ElectromagneticMeasurementMethod.objects.create(
                formation_resistance_dossier=frd_obj,
                measurement_date=measurement_date,
                measuring_responsible_party=responsible_party,
                measuring_procedure=measuring_procedure,
                assessment_procedure=assessment_procedure,
            )
        except Exception as e:
            logger.error(
                f"Could not save ElectromagneticMeasurementMethod for FRD "
                f"{frd_obj.frd_bro_id}: {e}"
            )


def run(kvk_number: str = None, bro_type: str = "frd", **kwargs) -> dict:
    progressor = Progress()

    if kvk_number is None:
        logger.warning("No kvk_number provided for FRD import.")
        return {"ids_found": 0, "imported": 0}

    DR = DataRetrieverKVK(kvk_number)
    DR.request_bro_ids("frd")
    DR.get_ids_kvk()
    ids = DR.frd_ids
    ids_ini_count = len(ids)

    print(f"{ids_ini_count} FRD BRO IDs found for organisation {kvk_number}.")

    last_import_date = get_last_import_date("frd")
    progressor.calibrate(ids, 25)

    imported = 0
    for frd_id in ids:
        result = handle_individual_bro_id(frd_id, last_import_date=last_import_date)
        if result:
            imported += 1
        progressor.next()
        progressor.progress()

    return {"ids_found": ids_ini_count, "imported": imported}
