from rest_framework import serializers
from . import models as gmw_models
from gld import models as gld_models

class GMWSerializer(serializers.ModelSerializer):
    lon = serializers.SerializerMethodField()
    lat = serializers.SerializerMethodField()

    class Meta:
        model = gmw_models.GroundwaterMonitoringWellStatic
        fields = '__all__'

    def get_lon(self, obj):
        return obj.lon
    
    def get_lat(self, obj):
        return obj.lat
        
    
class InstantieSerializer(serializers.ModelSerializer):

    class Meta:
        model = gmw_models.Instantie
        fields = '__all__'

class GLDSerializer(serializers.ModelSerializer):
    class Meta:
        model = gld_models.GroundwaterLevelDossier
        fields = '__all__'
