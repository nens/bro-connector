QUALITYREGIME = (
    ("IMBRO", "IMBRO"),
    ("IMBRO/A", "IMBRO/A"),
)

REGISTRATIONSTATUS = (
    ("geregistreerd", "geregistreerd"),
    ("aangevuld", "aangevuld"),
    ("voltooid", "voltooid"),
)

PROCESSREFERENCE = (
    ("NEN5120v1991", "NEN5120v1991"),
    ("NEN_EN_ISO22475v2006_C11v2010", "NEN_EN_ISO22475v2006_C11v2010"),
    ("NEN_ISO21413v2005", "NEN_ISO21413v2005"),
    ("NPR_ISO.TR23211v2009", "NPR_ISO.TR23211v2009"),
    ("RWSgwmon", "RWSgwmon"),
    ("STOWAgwst", "STOWAgwst"),
    ("vitensMeetprotocolGrondwater", "vitensMeetprotocolGrondwater"),
    ("waternetMeetprocedure", "waternetMeetprocedure"),
    ("onbekend", "onbekend"),
)

MEASUREMENTINSTRUMENTTYPE = (
    ("akoestischeSensor", "akoestischeSensor"),
    ("akoestischHandapparaat", "akoestischHandapparaat"),
    ("analoogPeilklokje", "analoogPeilklokje"),
    ("druksensor", "druksensor"),
    ("elektronischPeilklokje", "elektronischPeilklokje"),
    ("opzetStuk", "opzetStuk"),
    ("radarsensor", "radarsensor"),
    ("stereoDruksensor", "stereoDruksensor"),
    ("onbekend", "onbekend"),
    ("onbekendPeilklokje", "onbekendPeilklokje"),
)

AIRPRESSURECOMPENSATIONTYPE = (
    ("capillair", "capillair"),
    ("gecorrigeerdLokaleMeting", "gecorrigeerdLokaleMeting"),
    ("KNMImeting", "KNMImeting"),
    ("monitoringnetmeting", "monitoringnetmeting"),
    ("putlocatiemeting", "putlocatiemeting"),
    ("onbekend", "onbekend"),
)

PROCESSTYPE = (("algoritme", "algoritme"),)

EVALUATIONPROCEDURE = (
    ("brabantWater2013", "brabantWater2013"),
    ("eijkelkampDataValidatiev0.0.9", "eijkelkampDataValidatiev0.0.9"),
    ("oordeelDeskundige", "oordeelDeskundige"),
    (
        "PMBProtocolDatakwaliteitscontroleQC2018v2.0",
        "PMBProtocolDatakwaliteitscontroleQC2018v2.0",
    ),
    ("RWSAATGrondwaterv1.0", "RWSAATGrondwaterv1.0"),
    ("validatieprocedureEvidesWaterbedrijf", "validatieprocedureEvidesWaterbedrijf"),
    ("vitensBeoordelingsprotocolGrondwater", "vitensBeoordelingsprotocolGrondwater"),
    (
        "warecoWaterDataValidatieProtocolv20200219",
        "warecoWaterDataValidatieProtocolv20200219",
    ),
    ("waternetBeoordelingsprocedure", "waternetBeoordelingsprocedure"),
    ("onbekend", "onbekend"),
)

STATUSCODE = (
    ("volledigBeoordeeld", "volledigBeoordeeld"),
    ("voorlopig", "voorlopig"),
    ("onbekend", "onbekend"),
)

OBSERVATIONTYPE = (
    ("controlemeting", "controlemeting"),
    ("reguliereMeting", "reguliereMeting"),
)

STATUSQUALITYCONTROL = (
    ("afgekeurd", "afgekeurd"),
    ("goedgekeurd", "goedgekeurd"),
    ("nogNietBeoordeeld", "nogNietBeoordeeld"),
    ("onbeslist", "onbeslist"),
    ("onbekend", "onbekend"),
)

flag_schema_qc = {
    "0": "nogNietBeoordeeld",
    "1": "goedgekeurd",
    "9": "afgekeurd",
    "99": "onbeslist",
    "100": "onbekend",
}

CENSORREASON = (
    ("groterDanLimietwaarde", "groterDanLimietwaarde"),
    ("kleinerDanLimietwaarde", "kleinerDanLimietwaarde"),
    ("onbekend", "onbekend"),
)

INTERPOLATIONTYPE = (("discontinu", "discontinu"),)
