import pytest
from django.urls import reverse
from django.utils import timezone
from gld.models import MeasurementTvp, Observation, ObservationMetadata
from rest_framework.test import APIClient


def _url():
    return reverse("gld_api:observation-measurements-update")


def _payload(gld, measurement_time, **item_overrides):
    item = {
        "measurement_time": measurement_time.isoformat(),
        "calculated_value": 9.99,
        "status_quality_control_reason_datalens": "handmatige controle",
        "status_quality_control": "goedgekeurd",
        "value_limit": "0.05",
        "comment": "gecorrigeerd door bronhouder",
    }
    item.update(item_overrides)
    return {
        "gld_id": gld.pk,
        "observation_type": "reguliereMeting",
        "validatie_status": "voorlopig",
        "measurements": [item],
    }


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_post_without_credentials_is_rejected(
    anonymous_api_client, default_groundwater_level_dossier, default_measurement_tvp
):
    payload = _payload(
        default_groundwater_level_dossier, default_measurement_tvp.measurement_time
    )
    response = anonymous_api_client.post(_url(), payload, format="json")
    assert response.status_code == 401


@pytest.mark.django_db
def test_post_with_wrong_credentials_is_rejected(
    api_user, default_groundwater_level_dossier, default_measurement_tvp
):
    import base64

    client = APIClient()
    wrong_credentials = base64.b64encode(
        b"external-partner:totally-wrong-password"
    ).decode()
    client.credentials(HTTP_AUTHORIZATION=f"Basic {wrong_credentials}")
    payload = _payload(
        default_groundwater_level_dossier, default_measurement_tvp.measurement_time
    )
    response = client.post(_url(), payload, format="json")
    assert response.status_code == 401


@pytest.mark.django_db
def test_post_with_valid_credentials_is_authenticated(
    api_client, default_groundwater_level_dossier, default_measurement_tvp
):
    payload = _payload(
        default_groundwater_level_dossier, default_measurement_tvp.measurement_time
    )
    response = api_client.post(_url(), payload, format="json")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Validation / lookups
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_post_with_invalid_payload_returns_400(
    api_client, default_groundwater_level_dossier
):
    payload = {
        "gld_id": default_groundwater_level_dossier.pk,
        "observation_type": "niet-bestaand-type",
        "measurements": [],
    }
    response = api_client.post(_url(), payload, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_post_with_unknown_gld_id_returns_400(api_client, default_observation):
    payload = _payload(
        default_observation.groundwater_level_dossier, timezone.now()
    )
    payload["gld_id"] = 999_999
    response = api_client.post(_url(), payload, format="json")
    assert response.status_code == 400
    assert "bestaat niet" in response.data["detail"]


@pytest.mark.django_db
def test_post_with_no_matching_observation_returns_400(
    api_client, default_groundwater_level_dossier, default_observation_metadata
):
    # default_observation_metadata exists (reguliereMeting/voorlopig) but no
    # Observation links it to this dossier, since default_observation was
    # never requested.
    payload = _payload(
        default_groundwater_level_dossier,
        timezone.now(),
        observation_type="controlemeting",
    )
    payload["observation_type"] = "controlemeting"
    response = api_client.post(_url(), payload, format="json")
    assert response.status_code == 400
    assert "Geen observatie gevonden" in response.data["detail"]


# ---------------------------------------------------------------------------
# Update behaviour
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_post_updates_existing_measurement_and_metadata(
    api_client, default_groundwater_level_dossier, default_measurement_tvp
):
    payload = _payload(
        default_groundwater_level_dossier, default_measurement_tvp.measurement_time
    )
    response = api_client.post(_url(), payload, format="json")

    assert response.status_code == 200
    assert response.data["not_found"] == []
    assert len(response.data["updated"]) == 1

    default_measurement_tvp.refresh_from_db()
    assert float(default_measurement_tvp.calculated_value) == 9.99
    assert default_measurement_tvp.comment == "gecorrigeerd door bronhouder"

    metadata = default_measurement_tvp.measurement_point_metadata
    metadata.refresh_from_db()
    assert metadata.status_quality_control == "goedgekeurd"
    assert metadata.status_quality_control_reason_datalens == "handmatige controle"
    assert metadata.value_limit == "0.05"


@pytest.mark.django_db
def test_post_reports_measurement_times_not_found(
    api_client, default_groundwater_level_dossier, default_observation
):
    payload = _payload(default_groundwater_level_dossier, timezone.now())
    response = api_client.post(_url(), payload, format="json")

    assert response.status_code == 200
    assert response.data["updated"] == []
    assert len(response.data["not_found"]) == 1


@pytest.mark.django_db
def test_post_matches_null_validatie_status_to_null_metadata_status(
    api_client, default_groundwater_level_dossier, default_organisation
):
    metadata = ObservationMetadata.objects.create(
        observation_type="reguliereMeting",
        status=None,
        responsible_party=default_organisation,
    )
    observation = Observation.objects.create(
        groundwater_level_dossier=default_groundwater_level_dossier,
        observation_metadata=metadata,
    )
    tvp = MeasurementTvp.objects.create(
        observation=observation,
        measurement_time=timezone.now(),
        calculated_value=1.0,
        field_value_unit="m",
    )

    payload = _payload(
        default_groundwater_level_dossier,
        tvp.measurement_time,
        calculated_value=5.5,
    )
    payload["validatie_status"] = None

    response = api_client.post(_url(), payload, format="json")
    assert response.status_code == 200
    assert len(response.data["updated"]) == 1


@pytest.mark.django_db
def test_post_flags_observation_for_correction_when_up_to_date_in_bro(
    api_client,
    default_groundwater_level_dossier,
    default_observation,
    default_measurement_tvp,
):
    Observation.objects.filter(pk=default_observation.pk).update(
        up_to_date_in_bro=True
    )

    payload = _payload(
        default_groundwater_level_dossier, default_measurement_tvp.measurement_time
    )
    response = api_client.post(_url(), payload, format="json")
    assert response.status_code == 200

    default_observation.refresh_from_db()
    assert default_observation.up_to_date_in_bro is False
    assert default_observation.correction_reason == "eigenCorrectie"


@pytest.mark.django_db
def test_post_flags_observation_for_correction_when_already_delivered_to_bro(
    api_client,
    default_groundwater_level_dossier,
    default_observation,
    default_measurement_tvp,
):
    Observation.objects.filter(pk=default_observation.pk).update(
        up_to_date_in_bro=False, observation_id_bro="GLD000000001_O1"
    )

    payload = _payload(
        default_groundwater_level_dossier, default_measurement_tvp.measurement_time
    )
    response = api_client.post(_url(), payload, format="json")
    assert response.status_code == 200

    default_observation.refresh_from_db()
    assert default_observation.up_to_date_in_bro is False
    assert default_observation.correction_reason == "eigenCorrectie"


@pytest.mark.django_db
def test_post_does_not_flag_observation_when_not_yet_delivered(
    api_client,
    default_groundwater_level_dossier,
    default_observation,
    default_measurement_tvp,
):
    Observation.objects.filter(pk=default_observation.pk).update(
        up_to_date_in_bro=False, observation_id_bro=None, correction_reason=None
    )

    payload = _payload(
        default_groundwater_level_dossier, default_measurement_tvp.measurement_time
    )
    response = api_client.post(_url(), payload, format="json")
    assert response.status_code == 200

    default_observation.refresh_from_db()
    assert default_observation.correction_reason is None
