PRESENT = (
    ("indicatie", "Indicatie"),
    ("ja", "Ja"),
    ("nee", "Nee"),
    ("onbekend", "Onbekend"),
)


MEASURING_PROCEDURE = (
    ("geen", "geen"),
    ("werkinstructieWaternet", "werkinstructieWaternet"),
    ("manualOpnameZoutwachterOasen", "manualOpnameZoutwachterOasen"),
    ("onbekend", "onbekend"),
)

ASSESSMENT_PROCEDURE = (
    (
        "QCProtocolFormatieweerstandonderzoek2021",
        "QCProtocolFormatieweerstandonderzoek2021",
    ),
    ("oordeelDeskundige", "oordeelDeskundige"),
    ("vergelijkVoorgaandeMetingen", "vergelijkVoorgaandeMetingen"),
    ("onbekend", "onbekend"),
)

ELECTRODE_STATUS = (
    ("gebruiksklaar", "gebruiksklaar"),
    ("nietGebruiksklaar", "nietGebruiksklaar"),
    ("onbekend", "onbekend"),
)

REGISTRATION_STATUS = (
    ("geregistreerd", "geregistreerd"),
    ("aangevuld", "aangevuld"),
    ("voltooid", "voltooid"),
)

ASSESSMENT_TYPE = (
    ("elektromagnetischeBepaling", "elektromagnetischeBepaling"),
    ("geoohmkabelBepaling", "geoohmkabelBepaling"),
)

QUALITY_CONTROL = (
    ("afgekeurd", "afgekeurd"),
    ("goedgekeurd", "goedgekeurd"),
    ("onbeslist", "onbeslist"),
    ("onbekend", "onbekend"),
)


EVENT_TYPE_CHOICES = (
    ("FRD_StartRegistration", "FRD_StartRegistration"),
    ("FRD_Closure", "FRD_Closure"),
    ("FRD_GEM_MeasurementConfiguration", "FRD_GEM_MeasurementConfiguration"),
    ("FRD_GEM_Measurement", "FRD_GEM_Measurement"),
    ("FRD_EMM_InstrumentConfiguration", "FRD_EMM_InstrumentConfiguration"),
    ("FRD_EMM_Measurement", "FRD_EMM_Measurement"),
)

DELIVERY_TYPE_CHOICES = (
    ("register", "register"),
    ("replace", "replace"),
    ("insert", "insert"),
    ("move", "move"),
    ("delete", "delete"),
)

LEVERINGSTATUS_CHOICES = [
    (0, "Nog niet aangeleverd"),
    (1, "1 keer gefaald"),
    (2, "2 keer gefaald"),
    (3, "3 keer gefaald"),
    (4, "Succesvol aangeleverd"),
]
