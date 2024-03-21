from gmn.models import IntermediateEvent
from main.management.commands.tasks.gmn_tasks.gmn_request_handlers import (
    StartRegistrationGMN,
    MeasuringPointAddition,
    MeasuringPointRemoval,
    ClosureGMN,
)
from main.settings.base import gmn_SETTINGS

def sync_gmn(selected_gmn_qs=None, check_only=False):
    demo = gmn_SETTINGS["demo"]
    if demo:
        acces_token_bro_portal = gmn_SETTINGS["acces_token_bro_portal_demo"]
    else:
        acces_token_bro_portal = gmn_SETTINGS[
            "acces_token_bro_portal_bro_connector"
        ]

    if selected_gmn_qs:
        events = IntermediateEvent.objects.filter(
                    synced_to_bro=False, deliver_to_bro=True, gmn__in=selected_gmn_qs
                )
    else:
        events = IntermediateEvent.objects.filter(
                    synced_to_bro=False, deliver_to_bro=True
                )
    
    for event in events:
        event.refresh_from_db()
        # Synced_to_bro might be updated during the handling of another event.
        if event.synced_to_bro == True:
            continue

        if event.event_type == "GMN_StartRegistration":
            print(
                f"De startregistratie van {event.gmn} wordt geinitialiseerd of opgepakt"
            )
            registration = StartRegistrationGMN(event, demo, acces_token_bro_portal)
            registration.handle(check_only)

        if event.event_type == "GMN_MeasuringPoint":
            print(
                f"De toevoeging van {event.measuring_point} aan het {event.gmn} wordt geinitialiseerd of opgepakt"
            )
            addition = MeasuringPointAddition(event, demo, acces_token_bro_portal)
            addition.handle(check_only)

        if event.event_type == "GMN_MeasuringPointEndDate":
            print(
                f"De verwijdering van {event.measuring_point} aan het {event.gmn} wordt geinitialiseerd of opgepakt"
            )
            removal = MeasuringPointRemoval(event, demo, acces_token_bro_portal)
            removal.handle(check_only)

        if event.event_type == "GMN_Closure":
            print(
                f"De eindregistratie van {event.gmn} wordt geinitialiseerd of opgepakt"
            )
            closure = ClosureGMN(event, demo, acces_token_bro_portal)
            closure.handle(check_only)
