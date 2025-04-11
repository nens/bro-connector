from django.core.management.base import BaseCommand
from gmw.models import (
    GroundwaterMonitoringWellStatic,
)
from logging import getLogger

logger = getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        """
        Delete all duplicates
        """

        gmws = GroundwaterMonitoringWellStatic.objects.all()

        for gmw in gmws:
            gmw_id = gmw.internal_id
            gmws_per_gmw = GroundwaterMonitoringWellStatic.objects.filter(
                internal_id=gmw_id
            )
            gmws_per_gmw_count = gmws_per_gmw.count()

            # if there are duplicates, delete them
            if gmws_per_gmw_count > 1:
                gmws_per_gmw.exclude(pk=gmw.pk).delete()
                logger.info(
                    f"Deleted {gmws_per_gmw_count - 1} duplicates for GMW {gmw_id}"
                )
