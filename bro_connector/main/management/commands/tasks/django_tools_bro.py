from gmw_aanlevering import models

class GetDjangoObjects:
    def get_all_tubes(well_static_id):
        return models.GroundwaterMonitoringTubesStatic.objects.filter(
                groundwater_monitoring_well = well_static_id,
            )

    def get_all_geo_ohm_cables(tube_static_id):
        return models.GeoOhmCable.objects.filter(
                groundwater_monitoring_tube_static = tube_static_id,
            )
    
    def get_all_electrodes(geo_ohm_cable_id):
        return models.ElectrodeStatic.objects.filter(
                geo_ohm_cable = geo_ohm_cable_id
            )

    def get_geo_ohm_cable(geo_ohm_cable_id) -> models.GeoOhmCable:
        return models.GeoOhmCable.objects.get(
            geo_ohm_cable_id = geo_ohm_cable_id
        )

    def get_electrode_static(electrode_static_id) -> models.ElectrodeStatic:
        return models.ElectrodeStatic.objects.get(
            electrode_static_id = electrode_static_id
        )
    
    def get_tube_static(tube_static_id) -> models.GroundwaterMonitoringTubesStatic:
        return models.GroundwaterMonitoringTubesStatic.objects.get(
            groundwater_monitoring_tube_static_id = tube_static_id
        )

class DjangoTableToDict:
    def __init__(self):
        self.tubes = {}
        self.geo_ohm_cables = {}
        self.electrodes = {}

    def update_static_well(self, well):
        static_well_data = {
            "registrationObjectType": well.registration_object_type,
            "broId": well.bro_id,
            "requestReference": well.request_reference,
            "deliveryAccountableParty": well.delivery_accountable_party,
            "deliveryResponsibleParty": well.delivery_responsible_party,
            "qualityRegime": well.quality_regime,
            "underPrivilige": well.under_privilege,
            "deliveryContext": well.delivery_context,
            "constructionStandard": well.construction_standard,
            "initialFunction": well.initial_function,
            "nitgCode": well.nitg_code,
            "olgaCoda": well.olga_code,
            "wellCode": well.well_code,
            "monitoringPdokId": well.monitoring_pdok_id,
            "coordinates": well.coordinates,
            "referenceSystem": well.reference_system,
            "horizontalPositioningMethod": well.horizontal_positioning_method,
            "localVerticalReferencePoint": well.local_vertical_reference_point,
            "offset": well.well_offset,
            "verticalDatum": well.vertical_datum,
        }
        return static_well_data

    def update_static_tube(self, tube: models.GroundwaterMonitoringTubesStatic):
        
        static_tube_data = {
            "tubeNumber": tube.tube_number,
            "tubeType": tube.tube_type,
            "artesianWellCapPresent": tube.artesian_well_cap_present,
            "sedimentSumpPresent": tube.sediment_sump_present,
            "numberOfGeoOhmCables": tube.number_of_geo_ohm_cables,
            "tubeMaterial": tube.tube_material,
            "screenLength": tube.screen_length,
            "sockMaterial": tube.sock_material,
            "sedimentSumpLength": tube.sediment_sump_length,
        }

        self.tubes[tube.groundwater_monitoring_tube_static_id] = static_tube_data

        if tube.number_of_geo_ohm_cables > 0:

            geo_ohm_cables = GetDjangoObjects.get_all_geo_ohm_cables(tube.groundwater_monitoring_tube_static_id)

            for geo_ohm_cable in geo_ohm_cables:

                geo_ohm_cable_data = self.update_static_geo_ohm_cable(geo_ohm_cable)
                self.tubes[tube.groundwater_monitoring_tube_static_id]['geoOhmCables'] = geo_ohm_cable_data

                electrodes = GetDjangoObjects.get_all_electrodes(geo_ohm_cable.geo_ohm_cable_id)
                
                for electrode in electrodes:

                    electrodes_data = self.update_static_electrode(electrode)
                    self.tubes[tube.groundwater_monitoring_tube_static_id]['geoOhmCables'][geo_ohm_cable.geo_ohm_cable_id]['electrodes'] = electrodes_data
        
        
        
        return self.tubes

    def update_static_geo_ohm_cable(self, geo_ohm_cable: models.GeoOhmCable):
        geo_ohm_cable_data = {
            "cableNumber": geo_ohm_cable.cable_number
        }
        self.geo_ohm_cables[geo_ohm_cable.geo_ohm_cable_id] = geo_ohm_cable_data
        return self.geo_ohm_cables

    def update_static_electrode(self, electrode: models.ElectrodeStatic):
        electrode_static_data = {
            "electrodePackingMaterial": electrode.electrode_packing_material,
            "electrodePosition": electrode.electrode_position,
        }
        
        self.electrodes[electrode.electrode_static_id] = electrode_static_data
        return self.electrodes

    def update_dynamic_well(self, dynamic_well: models.GroundwaterMonitoringWellDynamic) -> None:
        dynamic_well_data = {
            'numberOfStandpipes': dynamic_well.number_of_standpipes,
            'groundLevelStable': dynamic_well.ground_level_stable,
            'wellStability': dynamic_well.well_stability,
            'owner': dynamic_well.owner,
            'maintenanceResponsibleParty': dynamic_well.maintenance_responsible_party,
            'wellHeadProtector': dynamic_well.well_head_protector,
            'deliverGldToBro': dynamic_well.deliver_gld_to_bro,
            'groundLevelPosition': dynamic_well.ground_level_position,
            'groundLevelPositioningMethod': dynamic_well.ground_level_positioning_method,
        }
        return dynamic_well_data

    def update_dynamic_tube(self, dynamic_tube: models.GroundwaterMonitoringTubesDynamic) -> None:
        dynamic_tube_data = {
            'tubeTopDiameter': dynamic_tube.tube_top_diameter,
            'variableDiameter': dynamic_tube.variable_diameter,
            'tubeStatus': dynamic_tube.tube_status,
            'tubeTopPosition': dynamic_tube.tube_top_position,
            'tubeTopPositioningMethod': dynamic_tube.tube_top_positioning_method,
            'tubePackingMaterial': dynamic_tube.tube_packing_material,
            'glue': dynamic_tube.glue,
            'plainTubePartLength': dynamic_tube.plain_tube_part_length,
            'insertedPartDiameter': dynamic_tube.inserted_part_diameter,
            'insertedPartLength': dynamic_tube.inserted_part_length,
            'insertedPartMaterial': dynamic_tube.inserted_part_material,
        }
        return dynamic_tube_data

    def update_dynamic_electrode(self, dynamic_electrode: models.ElectrodeDynamic) -> None:
        dynamic_electrode_data = {
            'electrodeNumber': dynamic_electrode.electrode_number,
            'electrodeStatus': dynamic_electrode.electrode_status,
        }
        
        return dynamic_electrode_data

    def update_workaround_data(self):
        workaround_data = {
        # Additions required for different generations in bro-exchange -> WORK-AROUND
            "numberOfMonitoringTubes": 1, # This is set static as we are only ever handling one monitoring tube per event.
            "numberOfTubesLengthened": 1,
            "numberOfTubesShortened": 1,
            'numberOfElectrodesChanged': 1,
        }
        return workaround_data