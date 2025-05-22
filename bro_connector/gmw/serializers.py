from rest_framework import serializers
from gmw import models as gmw_models
from gld import models as gld_models
from django.utils.html import format_html, format_html_join

class GMWSerializer(serializers.ModelSerializer):
    x = serializers.SerializerMethodField()
    y = serializers.SerializerMethodField()
    linked_gmns: list = serializers.SerializerMethodField()
    groundlevel_position = serializers.SerializerMethodField()
    well_head_protector = serializers.SerializerMethodField()
    picture = serializers.SerializerMethodField()
    nitg_code = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

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
        pictures = obj.picture.order_by("-recording_datetime","-picture_id")
        if pictures:
            # return picture.image_tag
            return format_html_join(
                "",
                '<div style="margin-bottom: 0.5em;"><img src="{}" style="max-width:100px; max-height:100px;"><br><small>{}</small></div>',
                [
                    (pic.picture.url, pic.recording_datetime.strftime("%Y-%m-%d %H:%M") if pic.recording_datetime else "No timestamp")
                    for pic in pictures if pic.picture
                ]
            )
        else:
            return "..."

    def get_nitg_code(self, obj):
        return obj.nitg_code
    
    def get_label(self, obj: gmw_models.GroundwaterMonitoringWellStatic):
        return obj.__str__()


class GLDSerializer(serializers.ModelSerializer):
    class Meta:
        model = gld_models.GroundwaterLevelDossier
        fields = "__all__"
