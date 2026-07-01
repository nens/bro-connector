from rest_framework import serializers

from gld.choices import OBSERVATIONTYPE, STATUSCODE


class MeasurementUpdateItemSerializer(serializers.Serializer):
    measurement_time = serializers.DateTimeField()
    calculated_value = serializers.FloatField(required=False, allow_null=True)
    status_quality_control_reason_datalens = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, max_length=200
    )
    status_quality_control = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, max_length=200
    )
    value_limit = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, max_length=50
    )
    comment = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, max_length=255
    )


class MeasurementUpdateRequestSerializer(serializers.Serializer):
    gld_id = serializers.IntegerField()
    observation_type = serializers.ChoiceField(choices=OBSERVATIONTYPE)
    validatie_status = serializers.ChoiceField(
        choices=STATUSCODE, required=False, allow_null=True
    )
    measurements = MeasurementUpdateItemSerializer(many=True)
