from rest_framework import serializers
from . import models as gmw_models
from gld import models as gld_models

class GMWSerializer(serializers.ModelSerializer):
    x = serializers.SerializerMethodField()
    y = serializers.SerializerMethodField()

    class Meta:
        model = gmw_models.GroundwaterMonitoringWellStatic
        fields = '__all__'

    def get_x(self, obj):
        return obj.lat
    
    def get_y(self, obj):
        return obj.lon
        
    
class InstantieSerializer(serializers.ModelSerializer):

    class Meta:
        model = gmw_models.Instantie
        fields = '__all__'

class GLDSerializer(serializers.ModelSerializer):
    class Meta:
        model = gld_models.GroundwaterLevelDossier
        fields = '__all__'
