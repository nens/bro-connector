from gmw import models

EVENTNAME2TYPE = {
    "constructie": "Construction",
    "beschermconstructieVeranderd": "WellHeadProtector",
    "buisOpgelengd": "Lengthening",
    "buisIngekort": "Shortening",
    "nieuweInmetingMaaiveld": "GroundLevelMeasuring",
    "nieuweInmetingPosities": "PositionsMeasuring",
    "nieuweBepalingMaaiveld": "GroundLevel",
    "eigenaarVeranderd": "Owner",
    "inmeting": "Positions",
    "electrodeStatus": "ElectrodeStatus",
    "onderhouderVeranderd": "Maintainer",
    "buisstatusVeranderd": "TubeStatus",
    "buisdeelIngeplaatst": "Insertion",
    "maaiveldVerlegd": "Shift",
    "opruimen": "Removal",
}


class DjangoTableToDict:
    def __init__(self):
        self.tubes = {}
        self.geo_ohm_cables = {}
        self.electrodes = {}

    def update_static_well(self, well) -> dict:
        static_well_data = {
            "deliveryAccountableParty": well.delivery_accountable_party,
            "deliveryResponsibleParty": well.delivery_responsible_party,
            "qualityRegime": well.quality_regime,
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
        if well.bro_id is not None:
            static_well_data.update({"broId": well.bro_id})

        return static_well_data

    def update_static_tube(self, tube: models.GroundwaterMonitoringTubeStatic) -> dict:
        cap_present = "onbekend"
        if tube.artesian_well_cap_present:
            if tube.artesian_well_cap_present:
                cap_present = "ja"
            elif tube.artesian_well_cap_present is False:
                cap_present = "nee"

        sump_present = "onbekend"

        if tube.sediment_sump_present:
            if tube.sediment_sump_present:
                cap_present = "ja"
            elif tube.sediment_sump_present is False:
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
            geo_ohm_cable_number = 0
            for geo_ohm_cable in tube.geo_ohm_cable.all():
                geo_ohm_cable_data = self.update_static_geo_ohm_cable(geo_ohm_cable)

                static_tube_data["geoOhmCables"][geo_ohm_cable_number] = (
                    geo_ohm_cable_data
                )
                electrodes_number = 0
                static_tube_data["geoOhmCables"][geo_ohm_cable_number][
                    "electrodes"
                ] = {}

                for electrode in geo_ohm_cable.electrode.all():
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

    def update_static_electrode(self, electrode: models.Electrode) -> dict:
        electrode_static_data = {
            "electrodePackingMaterial": electrode.electrode_packing_material,
            "electrodePosition": float(electrode.electrode_position.replace(",", ".")),
            "electrodeNumber": electrode.electrode_number,
            "electrodeStatus": electrode.electrode_status,
        }

        return electrode_static_data

    def update_dynamic_well(
        self, dynamic_well: models.GroundwaterMonitoringWellDynamic
    ) -> dict:
        dynamic_well_data = {
            "groundLevelStable": dynamic_well.ground_level_stable,
            "owner": dynamic_well.owner,
            "wellHeadProtector": dynamic_well.well_head_protector,
            "deliverGldToBro": dynamic_well.deliver_gld_to_bro,
            "groundLevelPosition": dynamic_well.ground_level_position,
            "groundLevelPositioningMethod": dynamic_well.ground_level_positioning_method,
        }
        if dynamic_well_data["groundLevelStable"] != "ja":
            dynamic_well_data.update({"wellStability": dynamic_well.well_stability})

        if dynamic_well.maintenance_responsible_party is not None:
            dynamic_well_data.update(
                {
                    "maintenanceResponsibleParty": dynamic_well.maintenance_responsible_party
                }
            )

        return dynamic_well_data

    def update_dynamic_tube(
        self, dynamic_tube: models.GroundwaterMonitoringTubeDynamic, sourcedoctype: str
    ) -> dict:
        """
        Update dynamic tube data based on document type.

        Args:
            dynamic_tube: GroundwaterMonitoringTubeDynamic model instance
            sourcedoctype: Type of source document

        Returns:
            Dictionary containing relevant dynamic tube data for the given document type
        """
        if sourcedoctype in ["construction", "construction_with_history"]:
            return self._get_construction_tube_data(dynamic_tube)
        elif sourcedoctype in ["positions", "positions_measuring"]:
            return self._get_positions_tube_data(dynamic_tube)
        elif sourcedoctype in ["shortening", "lengthening"]:
            return self._get_length_change_tube_data(dynamic_tube)
        elif sourcedoctype == "tube_status":
            return self._get_tube_status_data(dynamic_tube)
        else:
            return {}  # Return empty dict for unknown document types

    def _get_construction_tube_data(
        self, dynamic_tube: models.GroundwaterMonitoringTubeDynamic
    ) -> dict:
        """Get dynamic tube data for construction document types."""
        return {
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

    def _get_positions_tube_data(
        self, dynamic_tube: models.GroundwaterMonitoringTubeDynamic
    ) -> dict:
        """Get dynamic tube data for positions document types."""
        return {
            "tubeTopPosition": dynamic_tube.tube_top_position,
            "tubeTopPositioningMethod": dynamic_tube.tube_top_positioning_method,
        }

    def _get_length_change_tube_data(
        self, dynamic_tube: models.GroundwaterMonitoringTubeDynamic
    ) -> dict:
        """Get dynamic tube data for shortening or lengthening document types."""
        return {
            "tubeTopPosition": dynamic_tube.tube_top_position,
            "tubeTopPositioningMethod": dynamic_tube.tube_top_positioning_method,
            "plainTubePart": {
                "plainTubePartLength": dynamic_tube.plain_tube_part_length
            },
        }

    def _get_tube_status_data(
        self, dynamic_tube: models.GroundwaterMonitoringTubeDynamic
    ) -> dict:
        """Get dynamic tube data for tube status document type."""
        return {
            "tubeStatus": dynamic_tube.tube_status,
        }


def getConstruction():
    return models.Event.objects.filter(
        event_name="constructie",
        delivered_to_bro=False,
    )


def getAllIntermediateEvents():
    return models.Event.objects.filter(delivered_to_bro=False).exclude(
        event_name="constructie"
    )


def getWellHeadProtector():
    return models.Event.objects.filter(
        event_name="beschermconstructieVeranderd",
        delivered_to_bro=False,
    )


def getLengthening():
    return models.Event.objects.filter(
        event_name="buisOpgelengd",
        delivered_to_bro=False,
    )


def getShortening():
    return models.Event.objects.filter(
        event_name="buisIngekort",
        delivered_to_bro=False,
    )


def getGroundLevelMeasuring():
    return models.Event.objects.filter(
        event_name="nieuweInmetingMaaiveld",
        delivered_to_bro=False,
    )


def getPositionsMeasuring():
    return models.Event.objects.filter(
        event_name="nieuweInmetingPosities",
        delivered_to_bro=False,
    )


def getGroundLevel():
    return models.Event.objects.filter(
        event_name="nieuweBepalingMaaiveld",
        delivered_to_bro=False,
    )


def getOwner():
    return models.Event.objects.filter(
        event_name="eigenaarVeranderd",
        delivered_to_bro=False,
    )


def getPositions():
    return models.Event.objects.filter(
        event_name="inmeting",
        delivered_to_bro=False,
    )


def getElectrodeStatus():
    return models.Event.objects.filter(
        event_name="electrodeStatus",
        delivered_to_bro=False,
    )


def getMaintainer():
    return models.Event.objects.filter(
        event_name="onderhouderVeranderd",
        delivered_to_bro=False,
    )


def getTubeStatus():
    return models.Event.objects.filter(
        event_name="buisstatusVeranderd",
        delivered_to_bro=False,
    )


def getInsertion():
    return models.Event.objects.filter(
        event_name="buisdeelIngeplaatst",
        delivered_to_bro=False,
    )


def getShift():
    return models.Event.objects.filter(
        event_name="maaiveldVerlegd",
        delivered_to_bro=False,
    )
