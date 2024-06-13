from rest_framework import serializers
import bro.models as bro_models

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = bro_models.Company
        fields = '__all__'