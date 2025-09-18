import datetime
from logging import getLogger

import reversion
from django.core.management.base import BaseCommand
from gld.models import MeasurementTvp, Observation

logger = getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        for observation in Observation.objects.filter(observation_endtime__isnull=True):
            self.stdout.write(f"Checking observation: {observation}.")
            first_mtvp = (
                MeasurementTvp.objects.filter(observation=observation)
                .order_by("measurement_time")
                .first()
            )

            if observation.up_to_date_in_bro is True:
                with reversion.create_revision():
                    observation.up_to_date_in_bro = False
                    observation.save(update_fields=["up_to_date_in_bro"])
                    reversion.set_comment("Corrected the up to date status.")

            if first_mtvp is None:
                continue

            if first_mtvp.measurement_time < observation.observation_starttime:
                logger.info(f"Observation {observation} is being corrected.")
                logger.info(
                    f"Old date: {observation.observation_starttime}; New date: {first_mtvp.measurement_time - datetime.timedelta(seconds=1)}."
                )

                with reversion.create_revision():
                    observation.observation_starttime = (
                        first_mtvp.measurement_time - datetime.timedelta(seconds=1)
                    )
                    observation.save(update_fields=["observation_starttime"])
                    reversion.set_comment("Corrected the starting date.")
