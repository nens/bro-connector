from gmw.bro_validators import well, tube, electrode
from gmw.models import Electrode, GeoOhmCable, GroundwaterMonitoringWellStatic, GroundwaterMonitoringTubeStatic

class WellValidation:
    def __init__(self):
        self.com_bro = True
        self.bro_act = ""

    def add_to_report(self, com_bro_obj, bro_act_obj):
        if not com_bro_obj:
            self.bro_act += bro_act_obj
            self.com_bro = False

    def electrode(self, geo_ohm_cable: GeoOhmCable):
        # electrode static query
        electorde_static_query = geo_ohm_cable.electrode.all()
        for electrode_static in electorde_static_query:
            # electrode static validation
            com_bro_el_stat, bro_act_el_stat = electrode.validate_electrode(
                electrode_static
            )
            if not com_bro_el_stat:
                self.bro_act += (
                    "------------------------------------------------------------------------------------------------\n"
                    + "Electrode - Statisch: "
                    + str(electrode_static)
                    + "\n"
                )
            self.add_to_report(com_bro_el_stat, bro_act_el_stat)

    def geo_ohm_cable(self, tube_static: GroundwaterMonitoringTubeStatic):
        # geo ohm cable query
        geo_ohm_cable_query = tube_static.geo_ohm_cable.all()
        for geo_ohm_cable in geo_ohm_cable_query:
            # geo ohm cable validation
            com_bro_geo_ohm, bro_act_geo_ohm = electrode.validate_geo_ohm_cable(
                geo_ohm_cable
            )
            if not com_bro_geo_ohm:
                self.bro_act += (
                    "------------------------------------------------------------------------------------------------\n"
                    + "Geo Ohm Kabel: "
                    + str(geo_ohm_cable)
                    + "\n"
                )
            self.add_to_report(com_bro_geo_ohm, bro_act_geo_ohm)

            # electrode static check
            self.electrode(geo_ohm_cable)

    def tube_dynamic(self, tube_static: GroundwaterMonitoringTubeStatic):
        # tube dynamic query
        tube_dynamic_query = tube_static.state.all()
        for tube_dynamic in tube_dynamic_query:
            # tube dynamic validation
            com_bro_tube_dyn, bro_act_tube_dyn = tube.validate_tube_dynamic(
                tube_dynamic
            )
            if not com_bro_tube_dyn:
                self.bro_act += (
                    "------------------------------------------------------------------------------------------------\n"
                    + "Grondwatermonitoring Filter - Dynamisch: "
                    + str(tube_dynamic)
                    + "\n"
                )
            self.add_to_report(com_bro_tube_dyn, bro_act_tube_dyn)

    def tube_static(self, well_static: GroundwaterMonitoringWellStatic):
        # tube static query
        tube_static_query = well_static.tube.all()
        for tube_static in tube_static_query:
            # tube static validation
            com_bro_tube_stat, bro_act_tube_stat = tube.validate_tube_static(
                tube_static
            )
            if not com_bro_tube_stat:
                self.bro_act += (
                    "------------------------------------------------------------------------------------------------\n"
                    + "Grondwatermonitoring Filter - Statisch: "
                    + str(tube_static)
                    + "\n"
                )
            self.add_to_report(com_bro_tube_stat, bro_act_tube_stat)

            # check tube dynamic
            self.tube_dynamic(tube_static)
            # geo ohm cable check
            self.geo_ohm_cable(tube_static)

    def well_dynamic(self, well_static: GroundwaterMonitoringWellStatic):
        # well dynamic query
        well_dynamic_query = well_static.state.all()
        for well_dynamic in well_dynamic_query:
            # well dynamic validation
            com_bro_well_dyn, bro_act_well_dyn = well.validate_well_dynamic(
                well_dynamic
            )
            if not com_bro_well_dyn:
                self.bro_act += (
                    "------------------------------------------------------------------------------------------------\n"
                    + "Grondwatermonitoring Put - Dynamisch: "
                    + str(well_dynamic)
                    + "\n"
                )
            self.add_to_report(com_bro_well_dyn, bro_act_well_dyn)

    def well_complete(self, well_static: GroundwaterMonitoringWellStatic):
        # well static validation
        com_bro_well_stat, bro_act_well_stat = well.validate_well_static(well_static)

        if not com_bro_well_stat:
            self.bro_act += (
                "Grondwatermonitoring Put - Statisch: " + str(well_static) + "\n"
            )
        self.add_to_report(com_bro_well_stat, bro_act_well_stat)

        # check well dynamic
        self.well_dynamic(well_static)
        # check tube static
        self.tube_static(well_static)

        return self.com_bro, self.bro_act
