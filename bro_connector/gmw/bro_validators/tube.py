from gmw.models import GroundwaterMonitoringTubeStatic, GroundwaterMonitoringTubeDynamic


def validate_tube_static(tube: GroundwaterMonitoringTubeStatic) -> tuple[bool, str]:
    valid = True
    report = ""

    if tube.groundwater_monitoring_well_static.quality_regime == "IMBRO":
        ...
    else:
        ...

    return valid, report


def validate_tube_dynamic(
    tube_state: GroundwaterMonitoringTubeDynamic,
) -> tuple[bool, str]:
    valid = True
    report = ""

    if (
        tube_state.groundwater_monitoring_tube_static.groundwater_monitoring_well_static.quality_regime
        == "IMBRO"
    ):
        ...
    else:
        ...

    return valid, report
