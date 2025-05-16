from django.core.management.base import BaseCommand
from gld import models
import logging
from gld.management.tasks import gld_actions

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        dossiers = models.GroundwaterLevelDossier.objects.all()
        gld_actions.create_registrations_folder()
        # First create all registration logs and deliver them to the BRO
        for dossier in dossiers:
            gld_actions.check_and_deliver_start(dossier)

        # Then check the status of each individual registration log
        dossiers_with_id = dossiers.filter(gld_bro_id__isnull=False)
        for dossier in dossiers_with_id:
            start_log = models.gld_registration_log.objects.get(
                gmw_bro_id=dossier.gmw_bro_id,
                gld_bro_id=dossier.gld_bro_id,
                filter_number=dossier.tube_number,
                quality_regime=dossier.quality_regime
                if dossier.quality_regime
                else dossier.groundwater_monitoring_tube.groundwater_monitoring_well_static.quality_regime,
            )
            start_log.check_delivery_status()

        for dossier in dossiers_with_id:
            gld_actions.check_and_deliver_additions(dossier)

        # Then check the status of each individual registration log
        for dossier in dossiers_with_id:
            for observation in dossier.observation.filter(up_to_date_in_bro=False):
                obs = models.Observation.objects.get(
                    observation_id=observation.observation_id
                )
                addition_log = models.gld_addition_log.objects.filter(
                    observation=obs, addition_type=obs.addition_type
                ).first()
                if addition_log:
                    addition_log.check_delivery_status()

    def check_status(self, request, queryset):
        for dossier in queryset:
            gld_actions.check_status(dossier)
