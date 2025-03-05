from gmw.models import GroundwaterMonitoringWellStatic, GroundwaterMonitoringWellDynamic
from gmw.choices import (
    GROUNDLEVELPOSITIONINGMETHOD,
    GROUNDLEVELPOSITIONINGMETHOD_IMBRO,
    WELLHEADPROTECTOR,
    WELLHEADPROTECTOR_IMBRO,
    INITIALFUNCTION,
    DELIVERYCONTEXT,
    DELIVERYCONTEXT_IMBRO,
    CONSTRUCTIONSTANDARD_IMBRO,
    INITIALFUNCTION_IMBRO,
    HORIZONTALPOSITIONINGMETHOD_IMBRO,
    LOCALVERTICALREFERENCEPOINT,
    VERTICALDATUM,
    HORIZONTALPOSITIONINGMETHOD,
    CONSTRUCTIONSTANDARD,
    BOOLEAN_CHOICES,
    BOOLEAN_CHOICES_IMBRO,
)


def validate_well_static(well: GroundwaterMonitoringWellStatic) -> tuple[bool, str]:
    valid = True
    report = ""

    if well.quality_regime == "IMBRO":
        # delivery_accountable_party
        if well.delivery_accountable_party is None:
            valid = False
            report += f"{well._meta.get_field('delivery_accountable_party').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # delivery_responsible_party
        if well.delivery_responsible_party is None:
            valid = False
            report += f"{well._meta.get_field('delivery_responsible_party').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # delivery_context
        if well.delivery_context not in [
            item for subtuple in DELIVERYCONTEXT_IMBRO for item in subtuple
        ]:
            valid = False
            report += f"{well._meta.get_field('delivery_context').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # construction_standard
        if well.construction_standard not in [
            item for subtuple in CONSTRUCTIONSTANDARD_IMBRO for item in subtuple
        ]:
            valid = False
            report += f"{well._meta.get_field('construction_standard').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # construction_standard
        if well.initial_function not in [
            item for subtuple in INITIALFUNCTION_IMBRO for item in subtuple
        ]:
            valid = False
            report += f"{well._meta.get_field('initial_function').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # coordinates
        if well.coordinates is None:
            valid = False
            report += f"{well._meta.get_field('coordinates').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # horizontal_positioning_method
        if well.horizontal_positioning_method not in [
            item for subtuple in HORIZONTALPOSITIONINGMETHOD_IMBRO for item in subtuple
        ]:
            valid = False
            report += f"{well._meta.get_field('horizontal_positioning_method').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # local_vertical_reference_point
        if well.local_vertical_reference_point not in [
            item for subtuple in LOCALVERTICALREFERENCEPOINT for item in subtuple
        ]:
            valid = False
            report += f"{well._meta.get_field('local_vertical_reference_point').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # well_offset
        if well.well_offset is None:
            valid = False
            report += f"{well._meta.get_field('well_offset').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # vertical_datum
        if well.vertical_datum not in [
            item for subtuple in VERTICALDATUM for item in subtuple
        ]:
            valid = False
            report += f"{well._meta.get_field('vertical_datum').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

    else:  # "IMBRO/A"
        # delivery_accountable_party
        if well.delivery_accountable_party is None:
            valid = False
            report += f"{well._meta.get_field('delivery_accountable_party').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # delivery_responsible_party
        if well.delivery_responsible_party is None:
            valid = False
            report += f"{well._meta.get_field('delivery_responsible_party').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # delivery_context
        if well.delivery_context not in [
            item for subtuple in DELIVERYCONTEXT for item in subtuple
        ]:
            valid = False
            report += f"{well._meta.get_field('delivery_context').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # construction_standard
        if well.construction_standard not in [
            item for subtuple in CONSTRUCTIONSTANDARD for item in subtuple
        ]:
            valid = False
            report += f"{well._meta.get_field('construction_standard').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"
        # construction_standard
        if well.initial_function not in [
            item for subtuple in INITIALFUNCTION for item in subtuple
        ]:
            valid = False
            report += f"{well._meta.get_field('initial_function').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # coordinates
        if well.coordinates is None:
            valid = False
            report += f"{well._meta.get_field('coordinates').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # horizontal_positioning_method
        if well.horizontal_positioning_method not in [
            item for subtuple in HORIZONTALPOSITIONINGMETHOD for item in subtuple
        ]:
            valid = False
            report += f"{well._meta.get_field('horizontal_positioning_method').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # local_vertical_reference_point
        if well.local_vertical_reference_point not in [
            item for subtuple in LOCALVERTICALREFERENCEPOINT for item in subtuple
        ]:
            valid = False
            report += f"{well._meta.get_field('local_vertical_reference_point').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # well_offset
        if well.well_offset is None:
            valid = False
            report += f"{well._meta.get_field('well_offset').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # vertical_datum
        if well.vertical_datum not in [
            item for subtuple in VERTICALDATUM for item in subtuple
        ]:
            valid = False
            report += f"{well._meta.get_field('vertical_datum').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

    return valid, report


def validate_well_dynamic(
    well_state: GroundwaterMonitoringWellDynamic,
) -> tuple[bool, str]:
    valid = True
    report = ""

    if well_state.groundwater_monitoring_well_static.quality_regime == "IMBRO":
        # groundwater_monitoring_well_static
        if well_state.groundwater_monitoring_well_static is None:
            valid = False
            report += f"{well_state._meta.get_field('groundwater_monitoring_well_static').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # vertical_datum
        if well_state.ground_level_stable not in [
            item for subtuple in BOOLEAN_CHOICES_IMBRO for item in subtuple
        ]:
            valid = False
            report += f"{well_state._meta.get_field('ground_level_stable').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # owner
        if well_state.owner is None:
            valid = False
            report += f"{well_state._meta.get_field('owner').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # well_head_protector
        if well_state.well_head_protector not in [
            item for subtuple in WELLHEADPROTECTOR_IMBRO for item in subtuple
        ]:
            valid = False
            report += f"{well_state._meta.get_field('well_head_protector').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # ground_level_position
        if well_state.ground_level_position is None:
            valid = False
            report += f"{well_state._meta.get_field('ground_level_position').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

        # ground_level_positioning_method
        if well_state.ground_level_positioning_method not in [
            item for subtuple in GROUNDLEVELPOSITIONINGMETHOD_IMBRO for item in subtuple
        ]:
            valid = False
            report += f"{well_state._meta.get_field('ground_level_positioning_method').verbose_name} moet aangevuld worden om het IMBRO te maken\n"

    else:
        # groundwater_monitoring_well_static
        if well_state.groundwater_monitoring_well_static is None:
            valid = False
            report += f"{well_state._meta.get_field('groundwater_monitoring_well_static').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # vertical_datum
        if well_state.ground_level_stable not in [
            item for subtuple in BOOLEAN_CHOICES for item in subtuple
        ]:
            valid = False
            report += f"{well_state._meta.get_field('ground_level_stable').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # owner
        if well_state.owner is None:
            valid = False
            report += f"{well_state._meta.get_field('owner').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # well_head_protector
        if well_state.well_head_protector not in [
            item for subtuple in WELLHEADPROTECTOR for item in subtuple
        ]:
            valid = False
            report += f"{well_state._meta.get_field('well_head_protector').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # ground_level_position
        if well_state.ground_level_position is None:
            valid = False
            report += f"{well_state._meta.get_field('ground_level_position').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

        # ground_level_positioning_method
        if well_state.ground_level_positioning_method not in [
            item for subtuple in GROUNDLEVELPOSITIONINGMETHOD for item in subtuple
        ]:
            valid = False
            report += f"{well_state._meta.get_field('ground_level_positioning_method').verbose_name} moet aangevuld worden om het IMBRO/A te maken\n"

    return valid, report
