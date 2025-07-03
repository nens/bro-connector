KADER_AANLEVERING_GMN = (
    ("waterwetStrategischGrondwaterbeheer", "waterwetStrategischGrondwaterbeheer"),
    ("waterwetGrondwaterzorgplicht", "waterwetGrondwaterzorgplicht"),
    ("waterwetOnttrekkingInfiltratie", "waterwetOnttrekkingInfiltratie"),
    ("waterwetPeilbeheer", "waterwetPeilbeheer"),
    (
        "waterwetWaterstaatswerkAanlegWijziging",
        "waterwetWaterstaatswerkAanlegWijziging",
    ),
    ("waterwetWaterstaatswerkIngreep", "waterwetWaterstaatswerkIngreep"),
    ("waterwetWaterstaatswerkBeheer", "waterwetWaterstaatswerkBeheer"),
    ("kaderrichtlijnWater", "kaderrichtlijnWater"),
    ("waterschapswet", "waterschapswet"),
    ("drinkwaterwet", "drinkwaterwet"),
    ("ontgrondingenwet", "ontgrondingenwet"),
    ("wetNatuurbescherming", "wetNatuurbescherming"),
)

PROVINCIE_NAMEN = (
    ("Prov DR", "Drenthe"),
    ("Prov FL", "Flevoland"),
    ("Prov FR", "Friesland"),
    ("Prov GE", "Gelderland"),
    ("Prov GR", "Groningen"),
    ("Prov LB", "Limburg"),
    ("Prov NB", "Noord-Brabant"),
    ("Prov NH", "Noord-Holland"),
    ("Prov OV", "Overijssel"),
    ("Prov UT", "Utrecht"),
    ("Prov ZH", "Zuid-Holland"),
    ("Prov ZL", "Zeeland"),
)

BRO_DOMEINEN = (
    ("GMW", "GMW"),
    ("GLD", "GLD"),
    ("FRD", "FRD"),
    ("GAR", "GAR"),
)

MONITORINGDOEL = (
    ("strategischBeheerKwaliteitLandelijk", "strategischBeheerKwaliteitLandelijk"),
    ("strategischBeheerKwantiteitLandelijk", "strategischBeheerKwantiteitLandelijk"),
    ("strategischBeheerKwaliteitRegionaal", "strategischBeheerKwaliteitRegionaal"),
    ("strategischBeheerKwantiteitRegionaal", "strategischBeheerKwantiteitRegionaal"),
    ("beheersingStedelijkGebied", "beheersingStedelijkGebied"),
    ("gevolgenOnttrekkingKwaliteit", "gevolgenOnttrekkingKwaliteit"),
    ("gevolgenOnttrekkingKwantiteit", "gevolgenOnttrekkingKwantiteit"),
    ("gevolgenPeilbeheer", "gevolgenPeilbeheer"),
    ("gevolgenWaterstaatswerkKwaliteit", "gevolgenWaterstaatswerkKwaliteit"),
    ("gevolgenWaterstaatswerkKwantiteit", "gevolgenWaterstaatswerkKwantiteit"),
    ("waterstaatswerkBeheerKwaliteit", "waterstaatswerkBeheerKwaliteit"),
    ("waterstaatswerkBeheerKwantiteit", "waterstaatswerkBeheerKwantiteit"),
    ("veiligstellingGrondwaterKwaliteit", "veiligstellingGrondwaterKwaliteit"),
    ("veiligstellingGrondwaterKwantiteit", "veiligstellingGrondwaterKwantiteit"),
    ("waterstaatkundigeVerzorgingKwaliteit", "waterstaatkundigeVerzorgingKwaliteit"),
    ("waterstaatkundigeVerzorgingKwantiteit", "waterstaatkundigeVerzorgingKwantiteit"),
    (
        "veiligstellingDrinkwatervoorzieningKwaliteit",
        "veiligstellingDrinkwatervoorzieningKwaliteit",
    ),
    (
        "veiligstellingDrinkwatervoorzieningKwantiteit",
        "veiligstellingDrinkwatervoorzieningKwantiteit",
    ),
    ("gevolgenOntgronding", "gevolgenOntgronding"),
    ("natuurbescherming", "natuurbescherming"),
    ("natuurbeheer", "natuurbeheer"),
)

DELIVERY_TYPE_CHOICES = (
    ("register", "register"),
    ("replace", "replace"),
    ("insert", "insert"),
    ("move", "move"),
    ("delete", "delete"),
)

LEVERINGSTATUS_CHOICES = [
    ("0", "Nog niet aangeleverd"),
    ("1", "1 keer gefaald"),
    ("2", "2 keer gefaald"),
    ("3", "3 keer gefaald"),
    ("4", "Succesvol aangeleverd"),
]

EVENT_TYPE_CHOICES = [
    ("GMN_StartRegistration", "Startregistratie"),
    ("GMN_MeasuringPoint", "Meetpunt toevoegen"),
    ("GMN_MeasuringPointEndDate", "Einddatum meetpunt"),
    ("GMN_TubeReference", "Buis vervangen"),
    ("GMN_Closure", "Meetnet afsluiten"),
]
