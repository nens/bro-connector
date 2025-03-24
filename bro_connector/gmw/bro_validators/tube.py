from gmw.models import GroundwaterMonitoringTubeStatic, GroundwaterMonitoringTubeDynamic
from gmw.choices import (
    TUBETYPE,
    BOOLEAN_CHOICES,
    TUBEMATERIAL,
    SOCKMATERIAL,
    TUBETYPE_IMBRO,
    TUBEMATERIAL_IMBRO,
    SOCKMATERIAL_IMBRO,
    TUBESTATUS,
    TUBETOPPOSITIONINGMETHOD,
    TUBEPACKINGMATERIAL,
    GLUE,
    TUBESTATUS_IMBRO,
    TUBETOPPOSITIONINGMETHOD_IMBRO,
    TUBEPACKINGMATERIAL_IMBRO,
    GLUE_IMBRO,
)


def validate_tube_static(tube: GroundwaterMonitoringTubeStatic) -> tuple[bool, str]:
    valid = True
    report = ""

    if tube.groundwater_monitoring_well_static.quality_regime == "IMBRO":
        # groundwater_monitoring_well_static
        if tube.groundwater_monitoring_well_static is None:
            valid = False
            report += f"{tube._meta.get_field('groundwater_monitoring_well_static').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # tube_number
        if tube.tube_number is None:
            valid = False
            report += f"{tube._meta.get_field('tube_number').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # tube_type
        if tube.tube_type not in [
            item for subtuple in TUBETYPE_IMBRO for item in subtuple
        ]:
            valid = False
            report += f"{tube._meta.get_field('tube_type').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # artesian_well_cap_present
        if tube.artesian_well_cap_present not in [
            item for subtuple in BOOLEAN_CHOICES for item in subtuple
        ]:
            valid = False
            report += f"{tube._meta.get_field('artesian_well_cap_present').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # sediment_sump_present
        if tube.sediment_sump_present not in [
            item for subtuple in BOOLEAN_CHOICES for item in subtuple
        ]:
            valid = False
            report += f"{tube._meta.get_field('sediment_sump_present').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # tube_material
        if tube.tube_material not in [
            item for subtuple in TUBEMATERIAL_IMBRO for item in subtuple
        ]:
            valid = False
            report += f"{tube._meta.get_field('tube_material').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # screen_length
        if tube.screen_length is None:
            valid = False
            report += f"{tube._meta.get_field('screen_length').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # sock_material
        if tube.sock_material not in [
            item for subtuple in SOCKMATERIAL_IMBRO for item in subtuple
        ]:
            valid = False
            report += f"{tube._meta.get_field('sock_material').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # sediment_sump_length
        if tube.sediment_sump_length is None:
            valid = False
            report += f"{tube._meta.get_field('sediment_sump_length').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

    else:
        # groundwater_monitoring_well_static
        if tube.groundwater_monitoring_well_static is None:
            valid = False
            report += f"{tube._meta.get_field('groundwater_monitoring_well_static').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # tube_number
        if tube.tube_number is None:
            valid = False
            report += f"{tube._meta.get_field('tube_number').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # tube_type
        if tube.tube_type not in [item for subtuple in TUBETYPE for item in subtuple]:
            valid = False
            report += f"{tube._meta.get_field('tube_type').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # artesian_well_cap_present
        if tube.artesian_well_cap_present not in [
            item for subtuple in BOOLEAN_CHOICES for item in subtuple
        ]:
            valid = False
            report += f"{tube._meta.get_field('artesian_well_cap_present').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # sediment_sump_present
        if tube.sediment_sump_present not in [
            item for subtuple in BOOLEAN_CHOICES for item in subtuple
        ]:
            valid = False
            report += f"{tube._meta.get_field('sediment_sump_present').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # tube_material
        if tube.tube_material not in [
            item for subtuple in TUBEMATERIAL for item in subtuple
        ]:
            valid = False
            report += f"{tube._meta.get_field('tube_material').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # screen_length
        if tube.screen_length is None:
            valid = False
            report += f"{tube._meta.get_field('screen_length').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # sock_material
        if tube.sock_material not in [
            item for subtuple in SOCKMATERIAL for item in subtuple
        ]:
            valid = False
            report += f"{tube._meta.get_field('sock_material').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # sediment_sump_length
        if tube.sediment_sump_length is None:
            valid = False
            report += f"{tube._meta.get_field('sediment_sump_length').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

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
        # tube_top_diameter
        if tube_state.tube_top_diameter is None:
            valid = False
            report += f"{tube_state._meta.get_field('tube_top_diameter').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # variable_diameter
        if tube_state.variable_diameter not in [
            item for subtuple in BOOLEAN_CHOICES for item in subtuple
        ]:
            valid = False
            report += f"{tube_state._meta.get_field('variable_diameter').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # tube_status
        if tube_state.tube_status not in [
            item for subtuple in TUBESTATUS_IMBRO for item in subtuple
        ]:
            valid = False
            report += f"{tube_state._meta.get_field('tube_status').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # tube_top_position
        if tube_state.tube_top_position is None:
            valid = False
            report += f"{tube_state._meta.get_field('tube_top_position').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # tube_top_positioning_method
        if tube_state.tube_top_positioning_method not in [
            item for subtuple in TUBETOPPOSITIONINGMETHOD_IMBRO for item in subtuple
        ]:
            valid = False
            report += f"{tube_state._meta.get_field('tube_top_positioning_method').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # tube_packing_material
        if tube_state.tube_packing_material not in [
            item for subtuple in TUBEPACKINGMATERIAL_IMBRO for item in subtuple
        ]:
            valid = False
            report += f"{tube_state._meta.get_field('tube_packing_material').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # glue
        if tube_state.glue not in [
            item for subtuple in GLUE_IMBRO for item in subtuple
        ]:
            valid = False
            report += f"{tube_state._meta.get_field('glue').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # plain_tube_part_length
        if tube_state.plain_tube_part_length is None:
            valid = False
            report += f"{tube_state._meta.get_field('plain_tube_part_length').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # inserted_part_diameter
        if tube_state.inserted_part_diameter is None:
            valid = False
            report += f"{tube_state._meta.get_field('inserted_part_diameter').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # inserted_part_length
        if tube_state.inserted_part_length is None:
            valid = False
            report += f"{tube_state._meta.get_field('inserted_part_length').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # inserted_part_material
        if tube_state.inserted_part_material is None:
            valid = False
            report += f"{tube_state._meta.get_field('inserted_part_material').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

    else:
        # tube_top_diameter
        if tube_state.tube_top_diameter is None:
            valid = False
            report += f"{tube_state._meta.get_field('tube_top_diameter').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # variable_diameter
        if tube_state.variable_diameter not in [
            item for subtuple in BOOLEAN_CHOICES for item in subtuple
        ]:
            valid = False
            report += f"{tube_state._meta.get_field('variable_diameter').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # tube_status
        if tube_state.tube_status not in [
            item for subtuple in TUBESTATUS for item in subtuple
        ]:
            valid = False
            report += f"{tube_state._meta.get_field('tube_status').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # tube_top_position
        if tube_state.tube_top_position is None:
            valid = False
            report += f"{tube_state._meta.get_field('tube_top_position').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # tube_top_positioning_method
        if tube_state.tube_top_positioning_method not in [
            item for subtuple in TUBETOPPOSITIONINGMETHOD for item in subtuple
        ]:
            valid = False
            report += f"{tube_state._meta.get_field('tube_top_positioning_method').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # tube_packing_material
        if tube_state.tube_packing_material not in [
            item for subtuple in TUBEPACKINGMATERIAL for item in subtuple
        ]:
            valid = False
            report += f"{tube_state._meta.get_field('tube_packing_material').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # glue
        if tube_state.glue not in [item for subtuple in GLUE for item in subtuple]:
            valid = False
            report += f"{tube_state._meta.get_field('glue').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # plain_tube_part_length
        if tube_state.plain_tube_part_length is None:
            valid = False
            report += f"{tube_state._meta.get_field('plain_tube_part_length').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # inserted_part_diameter
        if tube_state.inserted_part_diameter is None:
            valid = False
            report += f"{tube_state._meta.get_field('inserted_part_diameter').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # inserted_part_length
        if tube_state.inserted_part_length is None:
            valid = False
            report += f"{tube_state._meta.get_field('inserted_part_length').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # inserted_part_material
        if tube_state.inserted_part_material is None:
            valid = False
            report += f"{tube_state._meta.get_field('inserted_part_material').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

    return valid, report
