from rest_framework import serializers
from gmw import models as gmw_models
from gld import models as gld_models
from gmn import models as gmn_models

class GMWSerializer(serializers.ModelSerializer):
    x = serializers.SerializerMethodField()
    y = serializers.SerializerMethodField()

    linked_gmns: list = serializers.SerializerMethodField()

    class Meta:
        model = gmw_models.GroundwaterMonitoringWellStatic
        fields = '__all__'

    def get_x(self, obj):
        return obj.lat
    
    def get_y(self, obj):
        return obj.lon
    
    def get_linked_gmns(self, obj) -> list:
        linked_measuringpoints = [
            measuringpoint.gmn.name for measuringpoint in gmn_models.MeasuringPoint.objects.filter(
                groundwater_monitoring_tube__groundwater_monitoring_well_static = obj
            )
        ]

        linked_measuringpoints = list(set(linked_measuringpoints)) # remove duplicates
        
        return linked_measuringpoints

class InstantieSerializer(serializers.ModelSerializer):

    class Meta:
        model = gmw_models.Instantie
        fields = '__all__'

class GLDSerializer(serializers.ModelSerializer):
    class Meta:
        model = gld_models.GroundwaterLevelDossier
        fields = '__all__'
