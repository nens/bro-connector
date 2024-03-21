from django.db.models.signals import post_save
from django.dispatch import receiver
from gmw.models import GroundwaterMonitoringWellDynamic, Event
from datetime import date

@receiver(post_save, sender=GroundwaterMonitoringWellDynamic)
def groundwater_well_dynamic_created(sender, instance, created, **kwargs):
    """Signal for groundwater monitoring well dynamic.
    Creates a event, based on the information of the new instance
    """
    if created:
        create_new_event(instance)

    else:
        #Wat te doen als een dynamic gmw aan wordt gepast?
        pass
        

def create_new_event(instance: GroundwaterMonitoringWellDynamic) -> None:
    """creates a event after a gmw dynamic is created"""

    try:
        Event.objects.create(
            event_name="Constructie",
            event_date=date.today(),
            groundwater_monitoring_well_static=instance.groundwater_monitoring_well_static,
            groundwater_monitoring_well_dynamic=instance,
            delivered_to_bro=True,        
        )
    except Exception as e:
        # Handle error
        print(f"Error creating event: {e}")