from django.core.management.base import BaseCommand
from gld.models import (
    GroundwaterLevelDossier,
    Observation,
)
import datetime


class Command(BaseCommand):
    def handle(self, *args, **options):
        """
        Add a new observation for every GLD that has no open observation
        An observation is open if it has no status. Once it has a status, it is
        (being) delivered to BRO and no new time-value pairs can be added.

        This function does not create the first observation of a GLD, this
        should be done manually because of connections with the metadata.
        """

        glds = GroundwaterLevelDossier.objects.all()
        for gld in glds:
            gld_id = gld.groundwater_level_dossier_id
            observations_per_gld = Observation.objects.filter(
                groundwater_level_dossier_id=gld_id
            )
            observation_status_per_gld = observations_per_gld.filter(status=None)

            # if there is no empty observation status, a new observation is needed
            if not observation_status_per_gld:
                # gather information about the previous observation
                try:
                    previous_gld_observation = observations_per_gld.last()
                    previous_observation_metadata_id = (
                        previous_gld_observation.observation_metadata_id
                    )
                    previous_observation_process_id = (
                        previous_gld_observation.observation_process_id
                    )
                except:
                    print(
                        "No observations exist yet for GLD {}, please create an observation".format(
                            gld_id
                        )
                    )
                    continue
                # use the metadata id and process id from the previous observation
                new_observation = Observation(
                    observation_starttime=datetime.datetime.utcnow().replace(
                        tzinfo=datetime.timezone.utc
                    ),
                    observation_metadata_id=previous_observation_metadata_id,
                    observation_process_id=previous_observation_process_id,
                    groundwater_level_dossier_id=gld_id,
                )
                new_observation.save()
