import datetime

import pytest
from django.utils import timezone

from gld.management.tasks.gld_actions import (
    gen_val_and_deliver_additions,
    observation_measurements_incomplete,
)
from gld.models import MeasurementTvp, gld_addition_log


@pytest.mark.django_db
class TestObservationMeasurementsIncomplete:
    def test_complete_measurement_is_not_incomplete(self, default_measurement_tvp):
        observation = default_measurement_tvp.observation
        assert observation_measurements_incomplete(observation) is False

    def test_missing_calculated_value_is_incomplete(self, default_observation):
        MeasurementTvp.objects.create(
            observation=default_observation,
            measurement_time=timezone.now() - datetime.timedelta(hours=1),
            field_value=None,
            field_value_unit="m",
        )
        assert observation_measurements_incomplete(default_observation) is True

    def test_missing_metadata_is_incomplete(self, default_measurement_tvp):
        observation = default_measurement_tvp.observation
        MeasurementTvp.objects.filter(pk=default_measurement_tvp.pk).update(
            measurement_point_metadata=None
        )
        assert observation_measurements_incomplete(observation) is True


@pytest.mark.django_db
def test_gen_val_and_deliver_additions_skips_incomplete_closed_observation(
    default_groundwater_level_dossier, default_observation
):
    now = timezone.now()
    default_observation.observation_endtime = now
    default_observation.result_time = now
    default_observation.up_to_date_in_bro = False
    default_observation.save()

    MeasurementTvp.objects.create(
        observation=default_observation,
        measurement_time=now - datetime.timedelta(hours=1),
        field_value=None,
        field_value_unit="m",
    )

    skipped = gen_val_and_deliver_additions(default_groundwater_level_dossier)

    assert skipped == [default_observation]
    assert not gld_addition_log.objects.filter(
        observation=default_observation
    ).exists()
