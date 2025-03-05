from rest_framework import serializers
import bro.models as bro_models


class OrganisationSerializer(serializers.ModelSerializer):
    class Meta:
        model = bro_models.Organisation
        fields = "__all__"
