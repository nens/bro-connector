import pytest
from gld.serializers import (
    MeasurementUpdateItemSerializer,
    MeasurementUpdateRequestSerializer,
)


def _valid_item(**overrides):
    item = {
        "measurement_time": "2024-01-01T10:00:00Z",
        "calculated_value": 1.23,
        "status_quality_control_reason_datalens": "handmatige controle",
        "status_quality_control": "goedgekeurd",
        "value_limit": "0.05",
        "comment": "gecorrigeerd",
    }
    item.update(overrides)
    return item


def _valid_payload(**overrides):
    payload = {
        "gld_id": 1,
        "observation_type": "reguliereMeting",
        "validatie_status": "voorlopig",
        "measurements": [_valid_item()],
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# MeasurementUpdateItemSerializer
# ---------------------------------------------------------------------------


def test_item_serializer_accepts_full_payload():
    serializer = MeasurementUpdateItemSerializer(data=_valid_item())
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["calculated_value"] == 1.23
    assert serializer.validated_data["comment"] == "gecorrigeerd"


def test_item_serializer_requires_measurement_time():
    data = _valid_item()
    del data["measurement_time"]
    serializer = MeasurementUpdateItemSerializer(data=data)
    assert not serializer.is_valid()
    assert "measurement_time" in serializer.errors


@pytest.mark.parametrize(
    "field",
    [
        "calculated_value",
        "status_quality_control_reason_datalens",
        "status_quality_control",
        "value_limit",
        "comment",
    ],
)
def test_item_serializer_optional_fields_can_be_omitted(field):
    data = _valid_item()
    del data[field]
    serializer = MeasurementUpdateItemSerializer(data=data)
    assert serializer.is_valid(), serializer.errors
    assert field not in serializer.validated_data


def test_item_serializer_allows_null_calculated_value():
    serializer = MeasurementUpdateItemSerializer(
        data=_valid_item(calculated_value=None)
    )
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["calculated_value"] is None


def test_item_serializer_rejects_invalid_measurement_time():
    serializer = MeasurementUpdateItemSerializer(
        data=_valid_item(measurement_time="not-a-date")
    )
    assert not serializer.is_valid()
    assert "measurement_time" in serializer.errors


# ---------------------------------------------------------------------------
# MeasurementUpdateRequestSerializer
# ---------------------------------------------------------------------------


def test_request_serializer_accepts_valid_payload():
    serializer = MeasurementUpdateRequestSerializer(data=_valid_payload())
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["gld_id"] == 1
    assert len(serializer.validated_data["measurements"]) == 1


def test_request_serializer_allows_null_validatie_status():
    serializer = MeasurementUpdateRequestSerializer(
        data=_valid_payload(validatie_status=None)
    )
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["validatie_status"] is None


def test_request_serializer_requires_gld_id():
    data = _valid_payload()
    del data["gld_id"]
    serializer = MeasurementUpdateRequestSerializer(data=data)
    assert not serializer.is_valid()
    assert "gld_id" in serializer.errors


def test_request_serializer_rejects_invalid_observation_type():
    serializer = MeasurementUpdateRequestSerializer(
        data=_valid_payload(observation_type="onzin")
    )
    assert not serializer.is_valid()
    assert "observation_type" in serializer.errors


def test_request_serializer_rejects_invalid_validatie_status():
    serializer = MeasurementUpdateRequestSerializer(
        data=_valid_payload(validatie_status="onzin")
    )
    assert not serializer.is_valid()
    assert "validatie_status" in serializer.errors


def test_request_serializer_requires_at_least_parseable_measurements_list():
    serializer = MeasurementUpdateRequestSerializer(
        data=_valid_payload(measurements=[{"calculated_value": 1.0}])
    )
    assert not serializer.is_valid()
    assert "measurements" in serializer.errors


def test_request_serializer_accepts_multiple_measurements():
    serializer = MeasurementUpdateRequestSerializer(
        data=_valid_payload(
            measurements=[
                _valid_item(measurement_time="2024-01-01T10:00:00Z"),
                _valid_item(measurement_time="2024-01-01T11:00:00Z"),
            ]
        )
    )
    assert serializer.is_valid(), serializer.errors
    assert len(serializer.validated_data["measurements"]) == 2
