import electrode
import well
import tube


def add_to_report(com_bro, bro_act, com_bro_obj, bro_act_obj):
    if not com_bro_obj:
        bro_act += bro_act_obj
        com_bro = False
    return com_bro, bro_act


def electrode_dyn_check(com_bro, bro_act, electrode_static):
    # electrode dynamic query
    electrode_dynamic_query = electrode_static.electrodedynamic_set.all()
    for electrode_dynamic in electrode_dynamic_query:
        # electrode dynamic validation
        com_bro_el_dyn, bro_act_el_dyn = electrode.validate_electrode_dynamic(
            electrode_dynamic
        )
        if not com_bro_el_dyn:
            bro_act += "\n" + "Electrode - Dynamisch: " + str(electrode_dynamic) + "\n"
        com_bro, bro_act = add_to_report(
            com_bro, bro_act, com_bro_el_dyn, bro_act_el_dyn
        )

    return com_bro, bro_act


def electrode_stat_check(com_bro, bro_act, geo_ohm_cable):
    # electrode static query
    electorde_static_query = geo_ohm_cable.electrodestatic_set.all()
    for electrode_static in electorde_static_query:
        # electrode static validation
        com_bro_el_stat, bro_act_el_stat = electrode.validate_electrode_static(
            electrode_static
        )
        if not com_bro_el_stat:
            bro_act += "\n" + "Electrode - Statisch: " + str(electrode_static) + "\n"
        com_bro, bro_act = add_to_report(
            com_bro, bro_act, com_bro_el_stat, bro_act_el_stat
        )

        # electrode dynamic check
        com_bro, bro_act = electrode_dyn_check(com_bro, bro_act, electrode_static)

    return com_bro, bro_act


def geo_ohm_check(com_bro, bro_act, tube_static):
    # geo ohm cable query
    geo_ohm_cable_query = tube_static.geoohmcable_set.all()
    for geo_ohm_cable in geo_ohm_cable_query:
        # geo ohm cable validation
        com_bro_geo_ohm, bro_act_geo_ohm = electrode.validate_geo_ohm_cable(
            geo_ohm_cable
        )
        if not com_bro_geo_ohm:
            bro_act += "\n" + "Geo Ohm Kabel: " + str(geo_ohm_cable) + "\n"
        com_bro, bro_act = add_to_report(
            com_bro, bro_act, com_bro_geo_ohm, bro_act_geo_ohm
        )

        # electrode static check
        com_bro, bro_act = electrode_stat_check(com_bro, bro_act, geo_ohm_cable)

    return com_bro, bro_act


def tube_dyn_check(com_bro, bro_act, tube_static):
    # tube dynamic query
    tube_dynamic_query = tube_static.state.all()
    for tube_dynamic in tube_dynamic_query:
        # tube dynamic validation
        com_bro_tube_dyn, bro_act_tube_dyn = tube.validate_tube_dynamic(tube_dynamic)
        if not com_bro_tube_dyn:
            bro_act += (
                "\n"
                + "Grondwatermonitoring Filter - Dynamisch: "
                + str(tube_dynamic)
                + "\n"
            )
        com_bro, bro_act = add_to_report(
            com_bro, bro_act, com_bro_tube_dyn, bro_act_tube_dyn
        )

    return com_bro, bro_act


def tube_stat_check(com_bro, bro_act, well_static):
    # tube static query
    tube_static_query = well_static.tube.all()
    for tube_static in tube_static_query:
        # tube static validation
        com_bro_tube_stat, bro_act_tube_stat = tube.validate_tube_static(tube_static)
        if not com_bro_tube_stat:
            bro_act += (
                "\n"
                + "Grondwatermonitoring Filter - Statisch: "
                + str(tube_static)
                + "\n"
            )
        com_bro, bro_act = add_to_report(
            com_bro, bro_act, com_bro_tube_stat, bro_act_tube_stat
        )

        # check tube dynamic
        com_bro, bro_act = tube_dyn_check(com_bro, bro_act, tube_static)
        # geo ohm cable check
        com_bro, bro_act = geo_ohm_check(com_bro, bro_act, tube_static)

    return com_bro, bro_act


def well_dyn_check(com_bro, bro_act, well_static):
    # well dynamic query
    well_dynamic_query = well_static.state.all()
    for well_dynamic in well_dynamic_query:
        # well dynamic validation
        com_bro_well_dyn, bro_act_well_dyn = well.validate_well_dynamic(well_dynamic)
        if not com_bro_well_dyn:
            bro_act += (
                "\n"
                + "Grondwatermonitoring Put - Dynamisch: "
                + str(well_dynamic)
                + "\n"
            )
        com_bro, bro_act = add_to_report(
            com_bro, bro_act, com_bro_well_dyn, bro_act_well_dyn
        )

    return com_bro, bro_act


def well_stat_check(com_bro, bro_act, well_static):
    # well static validation
    com_bro_well_stat, bro_act_well_stat = well.validate_well_static(well_static)
    if not com_bro_well_stat:
        bro_act += "Grondwatermonitoring Put - Statisch: " + str(well_static) + "\n"
    com_bro, bro_act = add_to_report(
        com_bro, bro_act, com_bro_well_stat, bro_act_well_stat
    )

    # check well dynamic
    com_bro, bro_act = well_dyn_check(com_bro, bro_act, well_static)
    # check tube static
    com_bro, bro_act = tube_stat_check(com_bro, bro_act, well_static)

    return com_bro, bro_act
