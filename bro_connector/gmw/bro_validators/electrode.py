from gmw.choices import (
    ELECTRODEPACKINGMATERIAL,
    ELECTRODEPACKINGMATERIAL_IMBRO,
    ELECTRODESTATUS,
    ELECTRODESTATUS_IMBRO,
)
from gmw.models import Electrode, GeoOhmCable


def validate_geo_ohm_cable(cable: GeoOhmCable) -> tuple[bool, str]:
    valid = True
    report = ""

    if (
        cable.groundwater_monitoring_tube_static.groundwater_monitoring_well_static.quality_regime
        == "IMBRO"
    ):
        # groundwater_monitoring_tube_static
        if cable.groundwater_monitoring_tube_static is None:
            valid = False
            report += f"{cable._meta.get_field('groundwater_monitoring_tube_static').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # cable_number
        if cable.cable_number is None:
            valid = False
            report += f"{cable._meta.get_field('cable_number').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

    else:
        # groundwater_monitoring_tube_static
        if cable.groundwater_monitoring_tube_static is None:
            valid = False
            report += f"{cable._meta.get_field('groundwater_monitoring_tube_static').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # cable_number
        if cable.cable_number is None:
            valid = False
            report += f"{cable._meta.get_field('cable_number').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

    return valid, report


def validate_electrode(
    electrode: Electrode,
) -> tuple[bool, str]:
    valid = True
    report = ""

    if (
        electrode.geo_ohm_cable.groundwater_monitoring_tube_static.groundwater_monitoring_well_static.quality_regime
        == "IMBRO"
    ):
        # electrode_packing_material
        if electrode.electrode_packing_material not in [
            item for subtuple in ELECTRODEPACKINGMATERIAL_IMBRO for item in subtuple
        ]:
            valid = False
            report += f"{electrode._meta.get_field('electrode_packing_material').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # electrode_position
        if electrode.electrode_position is None:
            valid = False
            report += f"{electrode._meta.get_field('electrode_position').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # electrode_number
        if electrode.electrode_number is None:
            valid = False
            report += f"{electrode._meta.get_field('electrode_number').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

    else:
        # electrode_packing_material
        if electrode.electrode_packing_material not in [
            item for subtuple in ELECTRODEPACKINGMATERIAL for item in subtuple
        ]:
            valid = False
            report += f"{electrode._meta.get_field('electrode_packing_material').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # electrode_position
        if electrode.electrode_position is None:
            valid = False
            report += f"{electrode._meta.get_field('electrode_position').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # electrode_number
        if electrode.electrode_number is None:
            valid = False
            report += f"{electrode._meta.get_field('electrode_number').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

    if (
        electrode.geo_ohm_cable.groundwater_monitoring_tube_static.groundwater_monitoring_well_static.quality_regime
        == "IMBRO"
    ):
        # electrode_status
        if electrode.electrode_status not in [
            item for subtuple in ELECTRODESTATUS_IMBRO for item in subtuple
        ]:
            valid = False
            report += f"{electrode._meta.get_field('electrode_status').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

    else:
        # electrode_status
        if electrode.electrode_status not in [
            item for subtuple in ELECTRODESTATUS for item in subtuple
        ]:
            valid = False
            report += f"{electrode._meta.get_field('electrode_status').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

    return valid, report
