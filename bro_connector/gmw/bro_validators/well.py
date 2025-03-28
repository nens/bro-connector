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


def tuple_to_list(tuples: list[tuple]) -> list:
    result = []
    for first, _ in tuples:
        result.append(first)
    return result


def report_missing_IMBRO(field: str) -> str:
    return f"{field} moet aangevuld worden om het IMBRO te maken\n"


def report_invalid_IMBRO(field: str, valid_values: list) -> str:
    return f"{field} moet een IMBRO waarde hebben: {valid_values}.\n"


def report_missing_IMBRO_A(field: str) -> str:
    return f"{field} moet aangevuld worden om het IMBRO/A te maken\n"


def report_invalid_IMBRO_A(field: str, valid_values: list) -> str:
    return f"{field} moet een IMBRO/A waarde hebben: {valid_values}.\n"


def validate_well_static(well: GroundwaterMonitoringWellStatic) -> tuple[bool, str]:
    valid = True
    report = ""

    if well.quality_regime == "IMBRO":
        # delivery_accountable_party
        if well.delivery_accountable_party is None:
            valid = False
            report += report_missing_IMBRO(
                well._meta.get_field("delivery_accountable_party").verbose_name
            )
        # delivery_responsible_party
        if well.delivery_responsible_party is None:
            valid = False
            report += report_missing_IMBRO(
                well._meta.get_field("delivery_responsible_party").verbose_name
            )

        # delivery_context
        if well.delivery_context is None:
            valid = False
            report += report_missing_IMBRO(
                well._meta.get_field("delivery_context").verbose_name
            )
        elif well.delivery_context not in tuple_to_list(DELIVERYCONTEXT_IMBRO):
            valid = False
            report += report_invalid_IMBRO(
                well._meta.get_field("delivery_context").verbose_name,
                DELIVERYCONTEXT_IMBRO,
            )

        # construction_standard
        if well.construction_standard is None:
            valid = False
            report += report_missing_IMBRO(
                well._meta.get_field("construction_standard").verbose_name
            )
        elif well.construction_standard not in tuple_to_list(
            CONSTRUCTIONSTANDARD_IMBRO
        ):
            valid = False
            report += report_invalid_IMBRO(
                well._meta.get_field("construction_standard").verbose_name,
                tuple_to_list(CONSTRUCTIONSTANDARD_IMBRO),
            )

        # construction_standard
        if well.initial_function is None:
            valid = False
            report += report_missing_IMBRO(
                well._meta.get_field("initial_function").verbose_name
            )
        elif well.initial_function not in tuple_to_list(INITIALFUNCTION_IMBRO):
            valid = False
            report += report_invalid_IMBRO(
                well._meta.get_field("initial_function").verbose_name,
                tuple_to_list(INITIALFUNCTION_IMBRO),
            )

        # coordinates
        if well.coordinates is None:
            valid = False
            report += report_missing_IMBRO(
                well._meta.get_field("coordinates").verbose_name
            )

        # horizontal_positioning_method
        if well.horizontal_positioning_method is None:
            valid = False
            report += report_missing_IMBRO(
                well._meta.get_field("horizontal_positioning_method").verbose_name
            )
        elif well.horizontal_positioning_method not in tuple_to_list(
            HORIZONTALPOSITIONINGMETHOD_IMBRO
        ):
            valid = False
            report += report_invalid_IMBRO(
                well._meta.get_field("horizontal_positioning_method").verbose_name,
                tuple_to_list(HORIZONTALPOSITIONINGMETHOD_IMBRO),
            )

        # local_vertical_reference_point
        if well.local_vertical_reference_point is None:
            valid = False
            report += report_missing_IMBRO(
                well._meta.get_field("local_vertical_reference_point").verbose_name
            )
        elif well.local_vertical_reference_point not in tuple_to_list(
            LOCALVERTICALREFERENCEPOINT
        ):
            valid = False
            report += report_invalid_IMBRO(
                well._meta.get_field("local_vertical_reference_point").verbose_name,
                tuple_to_list(LOCALVERTICALREFERENCEPOINT),
            )

        # well_offset
        if well.well_offset is None:
            valid = False
            report += report_missing_IMBRO(
                well._meta.get_field("well_offset").verbose_name
            )

        # vertical_datum
        if well.vertical_datum is None:
            valid = False
            report += report_missing_IMBRO(
                well._meta.get_field("vertical_datum").verbose_name
            )
        elif well.vertical_datum not in tuple_to_list(VERTICALDATUM):
            valid = False
            report += report_invalid_IMBRO(
                well._meta.get_field("vertical_datum").verbose_name,
                tuple_to_list(VERTICALDATUM),
            )

    else:  # "IMBRO/A"
        # delivery_accountable_party
        if well.delivery_accountable_party is None:
            valid = False
            report += report_missing_IMBRO_A(
                well._meta.get_field("delivery_accountable_party").verbose_name
            )

        # delivery_responsible_party
        if well.delivery_responsible_party is None:
            valid = False
            report += report_missing_IMBRO_A(
                well._meta.get_field("delivery_responsible_party").verbose_name
            )

        # delivery_context
        if well.delivery_context is None:
            valid = False
            report += report_missing_IMBRO_A(
                well._meta.get_field("delivery_context").verbose_name
            )
        elif well.delivery_context not in tuple_to_list(DELIVERYCONTEXT):
            valid = False
            report += report_invalid_IMBRO_A(
                well._meta.get_field("delivery_context").verbose_name,
                tuple_to_list(DELIVERYCONTEXT),
            )

        # construction_standard
        if well.construction_standard is None:
            valid = False
            report += report_missing_IMBRO_A(
                well._meta.get_field("construction_standard").verbose_name
            )
        elif well.construction_standard not in tuple_to_list(CONSTRUCTIONSTANDARD):
            valid = False
            report += report_invalid_IMBRO_A(
                well._meta.get_field("construction_standard").verbose_name,
                tuple_to_list(CONSTRUCTIONSTANDARD),
            )

        # initial_function
        if well.initial_function is None:
            valid = False
            report += report_missing_IMBRO_A(
                well._meta.get_field("initial_function").verbose_name
            )
        elif well.initial_function not in tuple_to_list(INITIALFUNCTION):
            valid = False
            report += report_invalid_IMBRO_A(
                well._meta.get_field("initial_function").verbose_name,
                tuple_to_list(INITIALFUNCTION),
            )

        # coordinates
        if well.coordinates is None:
            valid = False
            report += report_missing_IMBRO_A(
                well._meta.get_field("coordinates").verbose_name
            )

        # horizontal_positioning_method
        if well.horizontal_positioning_method is None:
            valid = False
            report += report_missing_IMBRO_A(
                well._meta.get_field("horizontal_positioning_method").verbose_name
            )
        elif well.horizontal_positioning_method not in tuple_to_list(
            HORIZONTALPOSITIONINGMETHOD
        ):
            valid = False
            report += report_invalid_IMBRO_A(
                well._meta.get_field("horizontal_positioning_method").verbose_name,
                tuple_to_list(HORIZONTALPOSITIONINGMETHOD),
            )

        # local_vertical_reference_point
        if well.local_vertical_reference_point is None:
            valid = False
            report += report_missing_IMBRO_A(
                well._meta.get_field("local_vertical_reference_point").verbose_name
            )
        elif well.local_vertical_reference_point not in tuple_to_list(
            LOCALVERTICALREFERENCEPOINT
        ):
            valid = False
            report += report_invalid_IMBRO_A(
                well._meta.get_field("local_vertical_reference_point").verbose_name,
                tuple_to_list(LOCALVERTICALREFERENCEPOINT),
            )

        # well_offset
        if well.well_offset is None:
            valid = False
            report += report_missing_IMBRO_A(
                well._meta.get_field("well_offset").verbose_name
            )
        # vertical_datum
        if well.vertical_datum is None:
            valid = False
            report += report_missing_IMBRO_A(
                well._meta.get_field("vertical_datum").verbose_name
            )

        elif well.vertical_datum not in tuple_to_list(VERTICALDATUM):
            valid = False
            report += report_invalid_IMBRO_A(
                well._meta.get_field("vertical_datum").verbose_name,
                tuple_to_list(VERTICALDATUM),
            )

    return valid, report


def validate_well_dynamic(
    well_state: GroundwaterMonitoringWellDynamic,
) -> tuple[bool, str]:
    valid = True
    report = ""

    is_imbro = well_state.groundwater_monitoring_well_static.quality_regime == "IMBRO"

    boolean_choices = BOOLEAN_CHOICES_IMBRO if is_imbro else BOOLEAN_CHOICES
    wellhead_protector_choices = (
        WELLHEADPROTECTOR_IMBRO if is_imbro else WELLHEADPROTECTOR
    )
    ground_level_method_choices = (
        GROUNDLEVELPOSITIONINGMETHOD_IMBRO if is_imbro else GROUNDLEVELPOSITIONINGMETHOD
    )

    required_fields = {
        "groundwater_monitoring_well_static": well_state.groundwater_monitoring_well_static,
        "ground_level_position": well_state.ground_level_position,
        "owner": well_state.owner,
    }

    choice_fields = {
        "ground_level_stable": (
            well_state.ground_level_stable,
            tuple_to_list(boolean_choices),
        ),
        "well_head_protector": (
            well_state.well_head_protector,
            tuple_to_list(wellhead_protector_choices),
        ),
        "ground_level_positioning_method": (
            well_state.ground_level_positioning_method,
            tuple_to_list(ground_level_method_choices),
        ),
    }

    for field, value in required_fields.items():
        if value is None:
            valid = False
            if is_imbro:
                report += report_missing_IMBRO(
                    well_state._meta.get_field(field).verbose_name
                )
            else:
                report += report_missing_IMBRO_A(
                    well_state._meta.get_field(field).verbose_name
                )

    for field, (value, valid_values) in choice_fields.items():
        if value not in valid_values:
            valid = False
            if is_imbro:
                report += report_invalid_IMBRO(
                    well_state._meta.get_field(field).verbose_name, valid_values
                )
            else:
                report += report_invalid_IMBRO_A(
                    well_state._meta.get_field(field).verbose_name, valid_values
                )

    return valid, report
