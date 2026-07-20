from typing import get_args

from main.utils.brostar.type_helpers import RegistrationTypeOptions, RequestTypeOptions


def _literal_to_choices(literal_type):
    return [(v, v) for v in get_args(literal_type) if v is not None]


REGISTRATION_TYPE_CHOICES = _literal_to_choices(RegistrationTypeOptions)

REQUEST_TYPE_CHOICES = _literal_to_choices(RequestTypeOptions)

MESSAGE_STATUS_CHOICES = [
    ("pending", "In wachtrij"),
    ("processing", "In behandeling"),
    ("completed", "Voltooid"),
    ("failed", "Mislukt"),
]
