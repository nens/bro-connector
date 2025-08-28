from rest_framework import serializers
from gmw import models as gmw_models
from gld import models as gld_models
from django.utils.html import format_html_join
from django.urls import reverse
from django.utils.html import format_html
from urllib.parse import urlencode

class GMWSerializer(serializers.ModelSerializer):
    x = serializers.SerializerMethodField()
    y = serializers.SerializerMethodField()
    linked_gmns: list = serializers.SerializerMethodField()
    groundlevel_position = serializers.SerializerMethodField()
    well_head_protector = serializers.SerializerMethodField()
    picture = serializers.SerializerMethodField()
    nitg_code = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()
    # url_open_comments_wells = serializers.SerializerMethodField()
    # url_open_comments_tubes = serializers.SerializerMethodField()
    has_open_comments = serializers.SerializerMethodField()
    # tubes = serializers.SerializerMethodField()
    glds = serializers.SerializerMethodField()

    class Meta:
        model = gmw_models.GroundwaterMonitoringWellStatic
        fields = [
            "groundwater_monitoring_well_static_id",
            "bro_id",
            "label",
            "well_code",
            "deliver_gmw_to_bro",
            "complete_bro",
            "in_management",
            "picture",
            "x",
            "y",
            "delivery_accountable_party",
            "linked_gmns",
            "nitg_code",
            "label",
            "groundlevel_position",
            "well_head_protector",
            "has_open_comments",
            # "tubes",
            "glds",
        ]

    def get_label(self, obj):
        return obj.__str__()

    def get_x(self, obj):
        return obj.lat

    def get_y(self, obj):
        return obj.lon

    def get_linked_gmns(self, obj: gmw_models.GroundwaterMonitoringWellStatic) -> list:
        measuring_points = [
            mp.gmn.name for tube in obj.tube.all() for mp in tube.measuring_point.all()
        ]
        return list(set(measuring_points))

    def get_groundlevel_position(self, obj: gmw_models.GroundwaterMonitoringWellStatic):
        last_state = obj.state.last()
        if not last_state:
            return None
        return last_state.ground_level_position

    def get_well_head_protector(self, obj: gmw_models.GroundwaterMonitoringWellStatic):
        last_state = obj.state.last()
        if not last_state:
            return None
        return last_state.well_head_protector

    def get_picture(self, obj: gmw_models.GroundwaterMonitoringWellStatic):
        pictures = list(obj.picture.all())
        if not pictures:
            return "..."

        picture = pictures[0]  # ordering is done during prefetching to minimize traffic

        if picture.picture:
            return format_html_join(
                "",
                '<div style="margin-bottom: 0.5em;"><img src="{}" style="max-width:100px; max-height:100px;"><br><small>{}</small></div>',
                [
                    (
                        picture.picture.url,
                        picture.recording_datetime.strftime("%Y-%m-%d %H:%M")
                        if picture.recording_datetime
                        else "No timestamp",
                    )
                ],
            )
        return "..."
        # main_pictures = obj.picture.order_by("-recording_datetime", "-picture_id").filter(is_main=True).all()
        # if main_pictures:
        #     picture = main_pictures.first()
        # else:
        #     picture = obj.picture.order_by("-recording_datetime", "-picture_id").first()
            
        # if picture and picture.picture:
        #     # return picture.image_tag
        #     return format_html_join(
        #         "",
        #         '<div style="margin-bottom: 0.5em;"><img src="{}" style="max-width:100px; max-height:100px;"><br><small>{}</small></div>',
        #         [
        #             (
        #                 picture.picture.url,
        #                 picture.recording_datetime.strftime("%Y-%m-%d %H:%M")
        #                 if picture.recording_datetime
        #                 else "No timestamp",
        #             )
        #         ],
        #     )
        # else:
        #     return "..."

    def get_nitg_code(self, obj):
        return obj.nitg_code

    def get_label(self, obj: gmw_models.GroundwaterMonitoringWellStatic):
        return obj.__str__()
    
    def get_has_open_comments(self, obj: gmw_models.GroundwaterMonitoringWellStatic):
        return obj.has_open_comments
    
    # def get_tubes(self, obj: gmw_models.GroundwaterMonitoringWellStatic):
    #     tubes = gmw_models.GroundwaterMonitoringTubeStatic.objects.filter(
    #         groundwater_monitoring_well_static=obj
    #     )
    #     if tubes:
    #         return list(set([tube.groundwater_monitoring_tube_static_id for tube in tubes]))
        
    #     return []
    
    def get_glds(self, obj: gmw_models.GroundwaterMonitoringWellStatic):
        tubes = gmw_models.GroundwaterMonitoringTubeStatic.objects.filter(
            groundwater_monitoring_well_static=obj
        )
        if tubes:
            gld_ids = []
            for tube in tubes:
                glds = gld_models.GroundwaterLevelDossier.objects.filter(
                    groundwater_monitoring_tube=tube
                )
                if glds:
                    gld_ids.extend([gld.groundwater_level_dossier_id for gld in glds])

            return list(set(gld_ids))
        
        return []
    
    def get_obs(self, obj: gmw_models.GroundwaterMonitoringWellStatic):
        tubes = gmw_models.GroundwaterMonitoringTubeStatic.objects.filter(
            groundwater_monitoring_well_static=obj
        )
        if tubes:
            obs_ids = [] 
            for tube in tubes:
                glds = gld_models.GroundwaterLevelDossier.objects.filter(
                    groundwater_monitoring_tube=tube
                )
                if glds:
                    for gld in glds:
                        obs = gld_models.Observation.objects.filter(
                            groundwater_level_dossier=gld
                        ).order_by("-observation_starttime").first()

                        # mtvp = (
                        #     gld_models.MeasurementTvp.objects.filter(observation=obs)
                        #     .order_by("-measurement_time")
                        #     .first()
                        # )
                        # if mtvp:
                        #     return mtvp.measurement_time
                        
                        if obs:
                            obs_ids.append(obs.observation_id)

            return list(set(obs_ids))
        
        return []

class GLDSerializer(serializers.ModelSerializer):
    groundwater_monitoring_well_static_id = serializers.SerializerMethodField()
    groundwater_monitoring_tube_static_id = serializers.SerializerMethodField()
    tube_number = serializers.SerializerMethodField()
    latest_observation_id_regular = serializers.SerializerMethodField()
    latest_measurement_date_regular = serializers.SerializerMethodField()
    observation_type_regular = serializers.SerializerMethodField()
    status_regular = serializers.SerializerMethodField()
    latest_observation_id_controle = serializers.SerializerMethodField()
    latest_measurement_date_controle = serializers.SerializerMethodField()
    observation_type_controle = serializers.SerializerMethodField()
    status_controle = serializers.SerializerMethodField()
    latest_observation_id = serializers.SerializerMethodField()
    latest_measurement_date = serializers.SerializerMethodField()
    observation_type = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = gld_models.GroundwaterLevelDossier
        fields = [
            "groundwater_level_dossier_id",
            "groundwater_monitoring_well_static_id",
            "groundwater_monitoring_tube_static_id",
            "gld_bro_id",
            "tube_number",
            "latest_observation_id_regular",
            "latest_measurement_date_regular",
            "observation_type_regular",
            "status_regular",
            "latest_observation_id_controle",
            "latest_measurement_date_controle",
            "observation_type_controle",
            "status_controle",
            "latest_observation_id",
            "latest_measurement_date",
            "observation_type",
            "status"
        ]

    def get_groundwater_monitoring_tube_static_id(self, obj: gld_models.GroundwaterLevelDossier):
        tube = obj.groundwater_monitoring_tube
        if tube:
            return tube.groundwater_monitoring_tube_static_id
        return None

    def get_groundwater_monitoring_well_static_id(self, obj: gld_models.GroundwaterLevelDossier):
        tube = obj.groundwater_monitoring_tube
        if tube:
            well = gmw_models.GroundwaterMonitoringTubeStatic.objects.get(
                groundwater_monitoring_tube_static_id=tube.groundwater_monitoring_tube_static_id
            ).groundwater_monitoring_well_static
            return well.groundwater_monitoring_well_static_id
        return None
    
    def get_tube_number(self, obj: gld_models.GroundwaterLevelDossier):
        return obj.tube_number

    def get_latest_observation_id_regular(self, obj: gld_models.GroundwaterLevelDossier):
        obs: gld_models.Observation = obj.latest_observation_regular
        if obs:
            return obs.observation_id
        return None
    
    def get_latest_observation_id_controle(self, obj: gld_models.GroundwaterLevelDossier):
        obs: gld_models.Observation = obj.latest_observation_controle
        if obs:
            return obs.observation_id
        return None
    
    def get_latest_measurement_date_regular(self, obj: gld_models.GroundwaterLevelDossier):
        meas: gld_models.MeasurementTvp = obj.latest_measurement_regular
        if meas:
            return meas.measurement_time
        return None
    
    def get_latest_measurement_date_controle(self, obj: gld_models.GroundwaterLevelDossier):
        meas: gld_models.MeasurementTvp = obj.latest_measurement_controle
        if meas:
            return meas.measurement_time
        return None

    def get_observation_type_regular(self, obj: gld_models.GroundwaterLevelDossier):
        latest_observation_regular: gld_models.Observation = obj.latest_observation_regular

        if latest_observation_regular and obj.latest_measurement_regular:
            metadata: gld_models.ObservationMetadata = latest_observation_regular.observation_metadata
            observation_type_regular = metadata.observation_type

            return observation_type_regular
        
        return None
    
    def get_observation_type_controle(self, obj: gld_models.GroundwaterLevelDossier):
        latest_observation_controle: gld_models.Observation = obj.latest_observation_controle

        if latest_observation_controle and obj.latest_measurement_controle:
            metadata: gld_models.ObservationMetadata = latest_observation_controle.observation_metadata
            observation_type_controle = metadata.observation_type

            return observation_type_controle
        
        return None

    def get_status_regular(self, obj: gld_models.GroundwaterLevelDossier):
        latest_observation_regular: gld_models.Observation = obj.latest_observation_regular

        if latest_observation_regular and obj.latest_measurement_regular:
            metadata: gld_models.ObservationMetadata = latest_observation_regular.observation_metadata
            status = metadata.status

            return status
        
        return None
    
    def get_status_controle(self, obj: gld_models.GroundwaterLevelDossier):
        ## Status of a controle measurement should always be None
        return None
    
    def get_latest_observation_id(self, obj: gld_models.GroundwaterLevelDossier):
        return None
    
    def get_latest_measurement_date(self, obj: gld_models.GroundwaterLevelDossier):
        return None

    def get_observation_type(self, obj: gld_models.GroundwaterLevelDossier):
        return None
    
    def get_status(self, obj: gld_models.GroundwaterLevelDossier):
        return None
    
class ObservationSerializer(serializers.ModelSerializer):
    timestamp_last_measurement = serializers.SerializerMethodField()
    # observation_type = serializers.SerializerMethodField()
    # status = serializers.SerializerMethodField()

    class Meta:
        model = gld_models.GroundwaterLevelDossier
        fields = [
            "timestamp_last_measurement",
            # "observation_type",
            # "status",
        ]

    def get_timestamp_last_measurement(self, obj: gld_models.Observation):
        return obj.timestamp_last_measurement

    # def get_latest_measurement_date(self, obj: gld_models.GroundwaterLevelDossier):
    #     for obs in obj.observation.all():
    #         for measurement in obs.measurement.all():
    #             return measurement.measurement_time
    #     return None
