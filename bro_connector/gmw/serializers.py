from rest_framework import serializers
from gmw import models as gmw_models
from gld import models as gld_models
from gmn import models as gmn_models

class GMWSerializer(serializers.ModelSerializer):
    x = serializers.SerializerMethodField()
    y = serializers.SerializerMethodField()
    linked_gmns: list = serializers.SerializerMethodField()
    groundlevel_position = serializers.SerializerMethodField()
    well_head_protector = serializers.SerializerMethodField()
    picture = serializers.SerializerMethodField()

    class Meta:
        model = gmw_models.GroundwaterMonitoringWellStatic
        fields = '__all__'

    def get_x(self, obj):
        return obj.lat
    
    def get_y(self, obj):
        return obj.lon
    
    def get_linked_gmns(self, obj: gmw_models.GroundwaterMonitoringWellStatic) -> list:
        measuring_points = [
            mp.gmn.name for tube in obj.tube.all()
            for mp in tube.measuringpoint_set.all()
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
        picture: gmw_models.Picture = obj.picture.last()
        if picture:
            return picture.image_tag
        else:
            return "..."

class GLDSerializer(serializers.ModelSerializer):
    class Meta:
        model = gld_models.GroundwaterLevelDossier
        fields = '__all__'
