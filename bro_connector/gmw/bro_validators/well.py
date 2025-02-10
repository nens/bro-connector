from gmw.models import GroundwaterMonitoringWellStatic, GroundwaterMonitoringWellDynamic
from gmw.choices import (
    GROUNDLEVELPOSITIONINGMETHOD,
    WELLSTATUS,
    WELLHEADPROTECTOR,
    WELLSTABILITY,
    INITIALFUNCTION,
    QUALITYREGIME,
    DELIVERYCONTEXT,
)


def validate_well_static(well: GroundwaterMonitoringWellStatic) -> tuple[bool, str]:
    valid = True
    report = ""

    if well.quality_regime == "IMBRO":
        ...
    else:
        ...

    return valid, report


def validate_well_dynamic(
    well_state: GroundwaterMonitoringWellDynamic,
) -> tuple[bool, str]:
    valid = True
    report = ""

    if well_state.groundwater_monitoring_well_static.quality_regime == "IMBRO":
        ...
    else:
        ...

    return valid, report
