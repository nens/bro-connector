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
            # "url_open_comments_wells",
            # "url_open_comments_tubes",
            "has_open_comments",
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
        main_pictures = obj.picture.order_by("-recording_datetime", "-picture_id").filter(is_main=True).all()
        if main_pictures:
            picture = main_pictures.first()
        else:
            picture = obj.picture.order_by("-recording_datetime", "-picture_id").first()
            
        if picture:
            # return picture.image_tag
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
        else:
            return "..."

    def get_nitg_code(self, obj):
        return obj.nitg_code

    def get_label(self, obj: gmw_models.GroundwaterMonitoringWellStatic):
        return obj.__str__()
    
    # def get_url_open_comments_wells(self, obj: gmw_models.GroundwaterMonitoringWellStatic):
    #     well_ids = obj.open_comments_well_ids
    #     if not well_ids:
    #         return "-"
        
    #     url = (
    #         reverse('admin:gmw_groundwatermonitoringwelldynamic_changelist')
    #         + "?"
    #         + urlencode({"groundwater_monitoring_well_dynamic_id__in": ",".join(str(id) for id in well_ids)})
    #     )
    #     return format_html('<a href="{}" target="_blank">Openstaand commentaar</a>', url)

    # def get_url_open_comments_tubes(self, obj: gmw_models.GroundwaterMonitoringWellStatic):
    #     tube_ids = obj.open_comments_tube_ids
    #     if not tube_ids:
    #         return "-"
        
    #     url = (
    #         reverse('admin:gmw_groundwatermonitoringtubedynamic_changelist')
    #         + "?"
    #         + urlencode({"groundwater_monitoring_tube_dynamic_id__in": ",".join(str(id) for id in tube_ids)})
    #     )
    #     return format_html('<a href="{}" target="_blank">Openstaand commentaar</a>', url)

    def get_has_open_comments(self, obj: gmw_models.GroundwaterMonitoringWellStatic):
        return obj.has_open_comments


class GLDSerializer(serializers.ModelSerializer):
    class Meta:
        model = gld_models.GroundwaterLevelDossier
        fields = "__all__"
