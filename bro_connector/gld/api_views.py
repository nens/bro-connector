from rest_framework import status
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from gld.models import GroundwaterLevelDossier, MeasurementTvp, Observation
from gld.serializers import MeasurementUpdateRequestSerializer


class ObservationMeasurementsUpdateView(APIView):
    """Update measurement_tvp values (and quality metadata) for one or more
    observations belonging to a GroundwaterLevelDossier."""

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
                status=status.HTTP_400_BAD_REQUEST,
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
                status=status.HTTP_400_BAD_REQUEST,
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
                not_found.append(_isoformat(measurement_time))
                continue

            _apply_measurement_update(tvp, item)
            updated.append(_isoformat(measurement_time))

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
