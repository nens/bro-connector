import re
from typing import Literal, get_args


def camel_to_label(value: str) -> str:
    spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", value)
    # Capitalize first letter only
    return spaced.capitalize()


def literal_to_choices(literal_type):
    choices = []
    for value in get_args(literal_type):
        if value is None:
            continue  # Skip None values for choices
        choices.append((value, camel_to_label(value)))
    return choices


QualityRegimeOptions = Literal["IMBRO", "IMBRO/A"]
CorrectionReasonOptions = Literal[
    "eigenCorrectie", "bronhouder", "kwaliteitsregime", "inOnderzoek"
]
BroDomainOptions = Literal["GMW", "GMN", "GAR", "GLD", "FRD", "GUF"]
RequestTypeOptions = Literal["registration", "replace", "insert", "move", "delete"]
RegistrationTypeOptions = Literal[
    "GMW_Construction",
    "GMW_ElectrodeStatus",
    "GMW_GroundLevel",
    "GMW_GroundLevelMeasuring",
    "GMW_Insertion",
    "GMW_Lengthening",
    "GMW_Maintainer",
    "GMW_Owner",
    "GMW_Positions",
    "GMW_PositionsMeasuring",
    "GMW_Removal",
    "GMW_Shift",
    "GMW_Shortening",
    "GMW_TubeStatus",
    "GMW_WellHeadProtector",
    "GMN_Startregistration",
    "GMN_MeasuringPoint",
    "GMN_MeasuringPointEndDate",
    "GMN_TubeReference",
    "GMN_Closure",
    "GAR",
    "GLD_StartRegistration",
    "GLD_Addition",
    "GLD_Closure",
    "GUF_StartRegistration",
    "GUF_Completion",
    "GPD_StartRegistration",
    "GPD_AddReport",
    "GPD_EndRegistration",
]

LimitSymbolOptions = Literal["LT", "GT"]

# GUF-specific value lists (from Section 6 of the BRO GUF Catalog)

# 6.1 Bodemlustype (Soil Loop Type)
DesignLoopTypeOptions = Literal[
    "horizontaal",
    "korf",
    "verticaal",
]

# 6.3 Filtertype (Filter Type) - used for screen_type in wells
FilterTypeOptions = Literal["nietVerticaal", "verticaal", "onbekend"]

# 6.4 Gebruiksdoel (Usage Purpose) - used for primary/secondary usage types
UsageTypeOptions = Literal[
    "agrarischeDoeleinden",
    "bemaling",
    "brandblusvoorziening",
    "geslotenBodemenergiesysteem",
    "grondwatersanering",
    "industrieleToepassing",
    "openBodemenergiesysteem",
    "openbareDrinkwatervoorziening",
    "overigeDoeleinden",
]

# 6.5 Installatiefunctie (Installation Function)
InstallationFunctionOptions = Literal[
    "geslotenBodemenergiesysteem",
    "onttrekkingEnRetournering",
    "onttrekking",
    "infiltratie",
    "infiltratieEnOnttrekking",
    "openBodemenergiesysteem",
]

# 6.6 KaderAanlevering (Delivery Framework) - used for delivery_context
GUFDeliveryContextOptions = Literal[
    "waterwet",
    "omgevingswet",
]

# 6.7 Putfunctie (Well Function) - used for well_functions
WellFunctionOptions = Literal["infiltratie", "onttrekking", "retournering", "onbekend"]

# 6.8 Rechtstype (Legal Type) - used for legal_type
LegalTypeOptions = Literal[
    "melding",
    "beschikking",
]

# 6.9 Registratiestatus (Registration Status)
RegistrationStatusOptions = Literal[
    "geregistreerd",
    "tijdelijkGeregistreerd",
]

# 6.10 RelatieveTemperatuur (Relative Temperature) - used for relative_temperature
RelativeTemperatureOptions = Literal[
    "koud",
    "warm",
    "onbekend",
]

# 6.11 Verplaatsingsrichting (Displacement Direction) - used for licensed_in_out
DisplacementDirectionOptions = Literal[
    "inbrengen",
    "onttrekken",
]

IndicationYesNoOptions = Literal["ja", "nee", "onbekend"]
WaterInOutOptions = Literal["ingebracht", "onttrokken"]
TemperatureOptions = Literal["koud", "warm", "onbekend", None]
PubliclyAvailableOptions = Literal["ja", "nee", None]
MethodOptions = Literal["berekening", "watermeter", "onbekend"]
