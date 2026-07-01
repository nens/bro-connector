from gld.models import GroundwaterLevelDossier, MeasurementTvp, Observation
from gld.serializers import MeasurementUpdateRequestSerializer
from rest_framework import status
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class ObservationMeasurementsUpdateView(APIView):
    """
    Update `MeasurementTvp` values and quality metadata for one or more measurements
    belonging to a `GroundwaterLevelDossier`.

    Requires **HTTP Basic Authentication** (username + password).

    ---

    ## Access

    Send a `POST` request with a JSON body.
    Example using the Python `requests` library:

        import requests

        response = requests.post(
            "https://<host>/gld/observation/measurements/",
            auth=("username", "password"),
            json={
                "gld_id": 1,
                "observation_type": "reguliereMeting",
                "validatie_status": "goedgekeurd",
                "measurements": [
                    {
                        "measurement_time": "2024-01-15T08:00:00+00:00",
                        "calculated_value": -1.234,
                        "status_quality_control": "goedgekeurd",
                        "status_quality_control_reason_datalens": "manual review",
                        "value_limit": "none",
                        "comment": "corrected after inspection"
                    }
                ]
            }
        )
        print(response.json())

    ---

    ## Input

    | Field | Type | Required | Description |
    |---|---|---|---|
    | `gld_id` | integer | yes | Primary key of the `GroundwaterLevelDossier` to update. |
    | `observation_type` | string | yes | Target observation type (e.g. `reguliereMeting`, `controlemeting`). |
    | `validatie_status` | string | no | Narrows observation selection by status (e.g. `goedgekeurd`, `voorlopig`). Omit to include all statuses. |
    | `measurements` | list | yes | List of measurement update items (see below). |

    ### measurements item fields

    | Field | Type | Required | Max length | Description |
    |---|---|---|---|---|
    | `measurement_time` | datetime (ISO 8601) | yes | — | Identifies the `MeasurementTvp` record to update. |
    | `calculated_value` | float | no | — | New calculated value. The original is backed up in `initial_calculated_value` if not yet set. |
    | `comment` | string | no | 255 | Free-text comment stored on the `MeasurementTvp`. |
    | `status_quality_control` | string | no | 200 | Quality-control status written to `MeasurementPointMetadata`. |
    | `status_quality_control_reason_datalens` | string | no | 200 | Reason string written to `MeasurementPointMetadata`. |
    | `value_limit` | string | no | 50 | Limit indicator written to `MeasurementPointMetadata`. |

    ---

    ## Process

    1. The request body is validated against the input schema above.
    2. The `GroundwaterLevelDossier` with `pk=gld_id` is fetched — returns **400** if not found.
    3. `Observation` records are filtered by dossier, `observation_type`, and `validatie_status` — returns **400** if none match.
    4. For each item in `measurements`, the matching `MeasurementTvp` is looked up by `measurement_time`:
        - **Found** → `calculated_value`, `comment`, and linked `MeasurementPointMetadata` fields are updated.
        - **Not found** → the timestamp is recorded in `not_found`.
    5. If any records were updated, observations already registered in the BRO
       (`up_to_date_in_bro=True` or `observation_id_bro` is set) are flagged:
       `correction_reason` → `eigenCorrectie`, `up_to_date_in_bro` → `False`.

    ---

    ## Output — HTTP 200

    **`updated`** — list of successfully updated records:

        [{"observation_pk": 42, "measurement_time": "2024-01-15T08:00:00+00:00"}, ...]

    **`not_found`** — list of timestamps for which no `MeasurementTvp` was found:

        [{"observation_pk": null, "measurement_time": "2024-01-16T08:00:00+00:00"}, ...]

    ---

    ## Errors

    | Status | Cause |
    |---|---|
    | 410 | `gld_id` does not match any `GroundwaterLevelDossier`. |
    | 411 | No `Observation` matches the supplied `observation_type` / `validatie_status`. |
    | 400 | Request body fails validation — field-level error details are included. |
    | 401 | Missing or invalid Basic Authentication credentials. |
    """

    authentication_classes = [BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MeasurementUpdateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        gld_id = data["gld_id"]
        observation_type = data["observation_type"]
        validatie_status = data.get("validatie_status")

        try:
            gld = GroundwaterLevelDossier.objects.get(pk=gld_id)
        except GroundwaterLevelDossier.DoesNotExist:
            return Response(
                {
                    "detail": f"GroundwaterLevelDossier met id '{gld_id}' bestaat niet."
                },
                status=status.HTTP_410_GONE,
            )

        observations = Observation.objects.filter(
            groundwater_level_dossier=gld,
            observation_metadata__observation_type=observation_type,
            observation_metadata__status=validatie_status,
        )

        if not observations.exists():
            return Response(
                {
                    "detail": (
                        "Geen observatie gevonden voor "
                        f"gld_id='{gld_id}', observation_type='{observation_type}', "
                        f"validatie_status='{validatie_status}'."
                    )
                },
                status=status.HTTP_411_LENGTH_REQUIRED,
            )

        updated = []
        not_found = []

        for item in data["measurements"]:
            measurement_time = item["measurement_time"]
            tvp = (
                MeasurementTvp.objects.filter(
                    observation__in=observations,
                    measurement_time=measurement_time,
                )
                .select_related("observation", "measurement_point_metadata")
                .first()
            )

            if tvp is None:
                not_found.append({"observation_pk": None, "measurement_time": _isoformat(measurement_time)})
                continue

            _apply_measurement_update(tvp, item)
            updated.append({"observation_pk": tvp.observation_id, "measurement_time": _isoformat(measurement_time)})

        if updated:
            _flag_observations_for_correction(observations)

        return Response(
            {
                "updated": updated,
                "not_found": not_found,
            },
            status=status.HTTP_200_OK,
        )


def _isoformat(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


def _apply_measurement_update(tvp: MeasurementTvp, item: dict) -> None:
    if "calculated_value" in item and item["calculated_value"] is not None:
        if tvp.initial_calculated_value is None:
            tvp.initial_calculated_value = tvp.calculated_value
        tvp.calculated_value = item["calculated_value"]
    if "comment" in item:
        tvp.comment = item["comment"]
    tvp.save()

    metadata = tvp.measurement_point_metadata
    if metadata is None:
        return

    if "status_quality_control" in item:
        metadata.status_quality_control = item["status_quality_control"]
    if "status_quality_control_reason_datalens" in item:
        metadata.status_quality_control_reason_datalens = item[
            "status_quality_control_reason_datalens"
        ]
    if "value_limit" in item:
        metadata.value_limit = item["value_limit"]
    metadata.save()


def _flag_observations_for_correction(observations) -> None:
    to_correct = observations.filter(up_to_date_in_bro=True) | observations.filter(
        observation_id_bro__isnull=False
    )
    to_correct.distinct().update(
        correction_reason="eigenCorrectie", up_to_date_in_bro=False
    )
