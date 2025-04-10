from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from .models import GroundwaterMonitoringNet, MeasuringPoint, Subgroup
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=GroundwaterMonitoringNet)
def save_measuring_points(sender, instance: GroundwaterMonitoringNet, **kwargs):
    logger.info(instance.project_number)

    measuring_points = instance.measuring_point.all()
    for point in measuring_points:
        gmw = point.groundwater_monitoring_tube.groundwater_monitoring_well_static
        gmw.project = instance.project
        gmw.save(update_fields=["project"])


@receiver(m2m_changed, sender=MeasuringPoint.subgroup.through)
def validate_subgroup_gmn(sender, instance, action, pk_set, **kwargs):
    """
    Ensure that all added subgroups belong to the same GMN as the MeasuringPoint.
    """
    if action in ["pre_add", "pre_bulk_add"]:
        invalid_subgroups = []
        subgroups = Subgroup.objects.filter(pk__in=pk_set)

        for subgroup in subgroups:
            if subgroup.gmn != instance.gmn:
                invalid_subgroups.append(subgroup)

        if invalid_subgroups:
            # Remove invalid subgroups from the operation
            pk_set.difference_update({subgroup.pk for subgroup in invalid_subgroups})
