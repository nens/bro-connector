import bro.models as bro_models
from rest_framework import serializers


class OrganisationSerializer(serializers.ModelSerializer):
    class Meta:
        model = bro_models.Organisation
        fields = "__all__"
