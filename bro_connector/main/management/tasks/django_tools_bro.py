from gmw import models


class GetDjangoObjects:
    def get_all_tubes(well_static_id):
        return models.GroundwaterMonitoringTubeStatic.objects.filter(
            groundwater_monitoring_well_static_id=well_static_id,
        )

    def get_all_geo_ohm_cables(tube_static_id):
        return models.GeoOhmCable.objects.filter(
            groundwater_monitoring_tube_static_id=tube_static_id,
        )

    def get_all_electrodes(geo_ohm_cable_id):
        return models.ElectrodeStatic.objects.filter(geo_ohm_cable=geo_ohm_cable_id)

    def get_geo_ohm_cable(geo_ohm_cable_id) -> models.GeoOhmCable:
        return models.GeoOhmCable.objects.get(geo_ohm_cable_id=geo_ohm_cable_id)

    def get_electrode_static(electrode_static_id) -> models.ElectrodeStatic:
        return models.ElectrodeStatic.objects.get(
            electrode_static_id=electrode_static_id
        )

    def get_tube_static(tube_static_id) -> models.GroundwaterMonitoringTubeStatic:
        return models.GroundwaterMonitoringTubeStatic.objects.get(
            groundwater_monitoring_tube_static_id=tube_static_id
        )


class DjangoTableToDict:
    def __init__(self):
        self.tubes = {}
        self.geo_ohm_cables = {}
        self.electrodes = {}

    def update_static_well(self, well) -> dict:
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

    def update_static_tube(self, tube: models.GroundwaterMonitoringTubeStatic) -> dict:
        cap_present = "onbekend"
        if tube.artesian_well_cap_present:
            if tube.artesian_well_cap_present == True:
                cap_present = "ja"
            elif tube.artesian_well_cap_present == False:
                cap_present = "nee"

        sump_present = "onbekend"

        if tube.sediment_sump_present:
            if tube.sediment_sump_present == True:
                cap_present = "ja"
            elif tube.sediment_sump_present == False:
                cap_present = "nee"

        static_tube_data = {
            "tubeNumber": tube.tube_number,
            "tubeType": tube.tube_type,
            "artesianWellCapPresent": cap_present,
            "sedimentSumpPresent": sump_present,
            "numberOfGeoOhmCables": tube.number_of_geo_ohm_cables,
            "tubeMaterial": tube.tube_material,
            "screen": {
                "screenLength": tube.screen_length,
                "sockMaterial": tube.sock_material,
            },
        }

        if static_tube_data["sedimentSumpPresent"] == "ja":
            static_tube_data.update(
                {"sedimentSump": {"sedimentSumpLength": tube.sediment_sump_length}}
            )

        static_tube_data["geoOhmCables"] = {}

        if tube.number_of_geo_ohm_cables > 0:
            geo_ohm_cables = GetDjangoObjects.get_all_geo_ohm_cables(
                tube.groundwater_monitoring_tube_static_id
            )
            geo_ohm_cable_number = 0
            for geo_ohm_cable in geo_ohm_cables:
                geo_ohm_cable_data = self.update_static_geo_ohm_cable(geo_ohm_cable)

                static_tube_data["geoOhmCables"][
                    geo_ohm_cable_number
                ] = geo_ohm_cable_data

                electrodes = GetDjangoObjects.get_all_electrodes(
                    geo_ohm_cable.geo_ohm_cable_id
                )

                electrodes_number = 0
                static_tube_data["geoOhmCables"][geo_ohm_cable_number][
                    "electrodes"
                ] = {}

                for electrode in electrodes:
                    electrodes_data = self.update_static_electrode(electrode)
                    static_tube_data["geoOhmCables"][geo_ohm_cable_number][
                        "electrodes"
                    ][electrodes_number] = electrodes_data

                    electrodes_number += 1

                geo_ohm_cable_number += 1

        return static_tube_data

    def update_static_geo_ohm_cable(self, geo_ohm_cable: models.GeoOhmCable) -> dict:
        geo_ohm_cable_data = {"cableNumber": geo_ohm_cable.cable_number}
        return geo_ohm_cable_data

    def update_static_electrode(self, electrode: models.ElectrodeStatic) -> dict:
        electrode_static_data = {
            "electrodePackingMaterial": electrode.electrode_packing_material,
            "electrodePosition": float(electrode.electrode_position.replace(",", ".")),
            "electrodeNumber": electrode.electrode_number,
        }

        return electrode_static_data

    def update_dynamic_well(
        self, dynamic_well: models.GroundwaterMonitoringWellDynamic
    ) -> dict:
        dynamic_well_data = {
            "numberOfStandpipes": dynamic_well.number_of_standpipes,
            "groundLevelStable": dynamic_well.ground_level_stable,
            "owner": dynamic_well.owner,
            "wellHeadProtector": dynamic_well.well_head_protector,
            "deliverGldToBro": dynamic_well.deliver_gld_to_bro,
            "groundLevelPosition": dynamic_well.ground_level_position,
            "groundLevelPositioningMethod": dynamic_well.ground_level_positioning_method,
        }
        if dynamic_well_data["groundLevelStable"] != "ja":
            dynamic_well_data.update({"wellStability": dynamic_well.well_stability})

        if dynamic_well.maintenance_responsible_party != None:
            dynamic_well_data.update(
                {
                    "maintenanceResponsibleParty": dynamic_well.maintenance_responsible_party
                }
            )

        return dynamic_well_data

    def update_dynamic_tube(
        self, dynamic_tube: models.GroundwaterMonitoringTubeDynamic, sourcedoctype
    ) -> dict:
        if sourcedoctype == "construction" or "construction_with_history":
            dynamic_tube_data = {
                "tubeTopDiameter": dynamic_tube.tube_top_diameter,
                "variableDiameter": dynamic_tube.variable_diameter,
                "tubeStatus": dynamic_tube.tube_status,
                "tubeTopPosition": dynamic_tube.tube_top_position,
                "tubeTopPositioningMethod": dynamic_tube.tube_top_positioning_method,
                "tubePackingMaterial": dynamic_tube.tube_packing_material,
                "glue": dynamic_tube.glue,
                "plainTubePart": {
                    "plainTubePartLength": dynamic_tube.plain_tube_part_length
                },
                "insertedPartDiameter": dynamic_tube.inserted_part_diameter,
                "insertedPartLength": dynamic_tube.inserted_part_length,
                "insertedPartMaterial": dynamic_tube.inserted_part_material,
            }

        elif sourcedoctype == "positions" or "positions_measuring":
            dynamic_tube_data = {
                "tubeTopPosition": dynamic_tube.tube_top_position,
                "tubeTopPositioningMethod": dynamic_tube.tube_top_positioning_method,
            }

        elif sourcedoctype == "shortening" or "lengthening":
            dynamic_tube_data = {
                "tubeTopPosition": dynamic_tube.tube_top_position,
                "tubeTopPositioningMethod": dynamic_tube.tube_top_positioning_method,
                "plainTubePart": {
                    "plainTubePartLength": dynamic_tube.plain_tube_part_length
                },
            }

        elif sourcedoctype == "tube_status":
            dynamic_tube_data = {
                "tubeStatus": dynamic_tube.tube_status,
            }

        return dynamic_tube_data

    def update_dynamic_electrode(
        self, dynamic_electrode: models.ElectrodeDynamic
    ) -> dict:
        dynamic_electrode_data = {
            "electrodeStatus": dynamic_electrode.electrode_status,
        }

        return dynamic_electrode_data


class GetEvents:
    """
    A Class that helps retrieving different types of events.
    The events will have information linking to the data that changed.
    """

    def construction():
        return models.Event.objects.filter(
            event_name="constructie",
            delivered_to_bro=False,
        )

    def wellHeadProtector():
        return models.Event.objects.filter(
            event_name="beschermconstructieVeranderd",
            delivered_to_bro=False,
        )

    def lengthening():
        return models.Event.objects.filter(
            event_name="buisOpgelengd",
            delivered_to_bro=False,
        )

    def shortening():
        return models.Event.objects.filter(
            event_name="buisIngekort",
            delivered_to_bro=False,
        )

    def groundLevelMeasuring():
        return models.Event.objects.filter(
            event_name="nieuweInmetingMaaiveld",
            delivered_to_bro=False,
        )

    def positionsMeasuring():
        return models.Event.objects.filter(
            event_name="nieuweInmetingPosities",
            delivered_to_bro=False,
        )

    def groundLevel():
        return models.Event.objects.filter(
            event_name="nieuweBepalingMaaiveld",
            delivered_to_bro=False,
        )

    def owner():
        return models.Event.objects.filter(
            event_name="eigenaarVeranderd",
            delivered_to_bro=False,
        )

    def positions():
        return models.Event.objects.filter(
            event_name="inmeting",
            delivered_to_bro=False,
        )

    def electrodeStatus():
        return models.Event.objects.filter(
            event_name="electrodeStatus",
            delivered_to_bro=False,
        )

    def maintainer():
        return models.Event.objects.filter(
            event_name="onderhouderVeranderd",
            delivered_to_bro=False,
        )

    def tubeStatus():
        return models.Event.objects.filter(
            event_name="buisstatusVeranderd",
            delivered_to_bro=False,
        )

    def insertion():
        return models.Event.objects.filter(
            event_name="buisdeelIngeplaatst",
            delivered_to_bro=False,
        )

    def shift():
        return models.Event.objects.filter(
            event_name="maaiveldVerlegd",
            delivered_to_bro=False,
        )
