from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import GroundwaterMonitoringNet
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=GroundwaterMonitoringNet)
def save_measuring_points(sender, instance: GroundwaterMonitoringNet, **kwargs):
    logger.info(instance.project_number)
    
    measuring_points = instance.measuring_points.all()
    for point in measuring_points:
        gmw = point.groundwater_monitoring_tube.groundwater_monitoring_well_static
        gmw.project_number = instance.project_number
        gmw.save(update_fields=["project_number"])