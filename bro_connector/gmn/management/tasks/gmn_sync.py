import logging

from bro.models import Organisation
from gmn.models import GroundwaterMonitoringNet, IntermediateEvent
from main.management.commands.tasks.gmn_tasks.gmn_request_handlers import (
    ClosureGMN,
    MeasuringPointAddition,
    MeasuringPointRemoval,
    StartRegistrationGMN,
)
from main.settings.base import ENV

logger = logging.getLogger(__name__)


def is_demo():
    if ENV == "production":
        return False
    return True


def _get_token(owner: Organisation):
    return {
        "user": owner.bro_user,
        "pass": owner.bro_token,
    }


def form_bro_info(gmn: GroundwaterMonitoringNet) -> dict:
    if (
        gmn.delivery_accountable_party.bro_token is None
        or gmn.delivery_accountable_party.bro_user is None
    ):
        return {
            "token": _get_token(gmn.delivery_responsible_party),
            "projectnummer": gmn.project.project_number,
        }
    return {
        "token": _get_token(gmn.delivery_accountable_party),
        "projectnummer": gmn.project.project_number,
    }


def bro_info_missing(bro_info: dict, gmn_name: str) -> bool:
    skip = False
    if bro_info["projectnummer"] is None:
        skip = True
        logger.info(f"No projectnumber for GMN ({gmn_name})")

    if bro_info["token"]["user"] is None or bro_info["token"]["pass"] is None:
        skip = True
        logger.info(f"No user or pass for GMN ({gmn_name})")

    return skip


def sync_gmn(selected_gmn_qs=None, check_only=False):
    demo = is_demo()
    if selected_gmn_qs:
        events = IntermediateEvent.objects.filter(
            synced_to_bro=False, deliver_to_bro=True, gmn__in=selected_gmn_qs
        )
    else:
        events = IntermediateEvent.objects.filter(
            synced_to_bro=False, deliver_to_bro=True
        )

    for event in events:
        print(event)
        bro_info = form_bro_info(event.gmn)
        print(bro_info)
        if bro_info_missing(bro_info, event.gmn.id):
            continue

        event.refresh_from_db()
        # Synced_to_bro might be updated during the handling of another event.
        if event.synced_to_bro:
            continue

        print(event.event_type)
        if event.event_type == "GMN_StartRegistration":
            print(
                f"De startregistratie van {event.gmn} wordt geinitialiseerd of opgepakt"
            )
            registration = StartRegistrationGMN(event, demo, bro_info)
            registration.handle(check_only)

        if event.event_type == "GMN_MeasuringPoint":
            print(
                f"De toevoeging van {event.measuring_point} aan het {event.gmn} wordt geinitialiseerd of opgepakt"
            )
            addition = MeasuringPointAddition(event, demo, bro_info)
            addition.handle(check_only)

        if event.event_type == "GMN_MeasuringPointEndDate":
            print(
                f"De verwijdering van {event.measuring_point} aan het {event.gmn} wordt geinitialiseerd of opgepakt"
            )
            removal = MeasuringPointRemoval(event, demo, bro_info)
            removal.handle(check_only)

        if event.event_type == "GMN_Closure":
            print(
                f"De eindregistratie van {event.gmn} wordt geinitialiseerd of opgepakt"
            )
            closure = ClosureGMN(event, demo, bro_info)
            closure.handle(check_only)
