UNDERPRIVILIGE = (
    ("ja", "ja"),
    ("nee", "nee"),
)

TUBEPACKINGMATERIAL = (
    ("bentoniet", "bentoniet"),
    ("bentonietFiltergrind", "bentonietFiltergrind"),
    ("boorgatmateriaal", "boorgatmateriaal"),
    ("filtergrind", "filtergrind"),
    ("grind", "grind"),
    ("grout", "grout"),
    ("volgensGerelateerdeVerkenning", "volgensGerelateerdeVerkenning"),
    ("onbekend", "onbekend"),
)

ELECTRODEPACKINGMATERIAL = (
    ("filtergrind", "filtergrind"),
    ("klei", "klei"),
    ("volgensGerelateerdeVerkenning", "volgensGerelateerdeVerkenning"),
    ("zand", "zand"),
    ("onbekend", "onbekend"),
)

WELLHEADPROTECTOR = (
    ("geen", "geen"),
    ("kokerDeelsMetaal", "kokerDeelsMetaal"),
    ("kokerMetaal", "kokerMetaal"),
    ("kokerNietMetaal", "kokerNietMetaal"),
    ("potNietWaterdicht", "potNietWaterdicht"),
    ("potWaterdicht", "potWaterdicht"),
    ("koker", "koker"),
    ("onbekend", "onbekend"),
    ("pot", "pot"),
)

TUBEMATERIAL = (
    ("beton", "beton"),
    ("gres", "gres"),
    ("hout", "hout"),
    ("ijzer", "ijzer"),
    ("koper", "koper"),
    ("messing", "messing"),
    ("pe", "pe"),
    ("peHighDensity", "peHighDensity"),
    ("peLowDensity", "peLowDensity"),
    ("peHighDensityPvc", "peHighDensityPvc"),
    ("pePvc", "pePvc"),
    ("pvc", "pvc"),
    ("staal", "staal"),
    ("staalGegalvaniseerd", "staalGegalvaniseerd"),
    ("staalRoestvrij", "staalRoestvrij"),
    ("teflon", "teflon"),
    ("asbest", "asbest"),
    ("houtStaal", "houtStaal"),
    ("koperStaal", "koperStaal"),
    ("onbekend", "onbekend"),
    ("pvcStaal", "pvcStaal"),
)

TUBESTATUS = (
    ("onbruikbaar", "onbruikbaar"),
    ("gebruiksklaar", "gebruiksklaar"),
    ("nietGebruiksklaar", "nietGebruiksklaar"),
    ("onbekend", "onbekend"),  # IMBRO/A
)

TUBETYPE = (
    ("minifilter", "minifilter"),
    ("standaardbuis", "standaardbuis"),
    ("volledigFilter", "volledigFilter"),
    ("filterlozeBuis", "filterlozeBuis"),
)

COORDINATETRANSFORMATION = (
    ("gebruiksklaar", "gebruiksklaar"),
    ("nietGebruiksklaar", "nietGebruiksklaar"),
    ("onbekend", "onbekend"),
)

ELECTRODESTATUS = (
    ("onbruikbaar", "onbruikbaar"),
    ("gebruiksklaar", "gebruiksklaar"),
    ("nietGebruiksklaar", "nietGebruiksklaar"),
    ("onbekend", "onbekend"),  # IMBRO/A
)

SCREENPROTECTION = (
    ("dubbelwandigFilterMetFilterkous", "dubbelwandigFilterMetFilterkous"),
    ("dubbelwandigFilterZonderFilterkous", "dubbelwandigFilterZonderFilterkous"),
    ("filterkousZonderOpvulling", "filterkousZonderOpvulling"),
    ("filterkousMetOpvulling", "filterkousMetOpvulling"),
    ("geen", "geen"),
    ("onbekend", "onbekend"),
)

INITIALFUNCTION = (
    ("brandput", "brandput"),
    ("kwaliteit", "kwaliteit"),
    ("kwaliteitStand", "kwaliteitStand"),
    ("onttrekking", "onttrekking"),
    ("stand", "stand"),
    ("onbekend", "onbekend"),
)

DELIVERYCONTEXT = (
    ("GBM", "GBM"),
    ("KRW", "KRW"),
    ("monitoringBijDrinkwaterwinning", "monitoringBijDrinkwaterwinning"),
    ("NBW", "NBW"),
    ("NR", "NR"),
    ("OGW", "OGW"),
    ("OG", "OW"),
    ("publiekeTaak", "publiekeTaak"),
    ("WW", "WW"),
    ("archiefoverdracht", "archiefoverdracht"),
)

SOCKMATERIAL = (
    ("geen", "geen"),
    ("kopergaas", "kopergaas"),
    ("nylon", "nylon"),
    ("pp", "pp"),
    ("onbekend", "onbekend"),
)

CONSTRUCTIONSTANDARD = (
    ("BWsb", "BWsb"),
    ("geen", "geen"),
    ("IBR", "IBR"),
    ("NEN5104", "NEN5104"),
    ("NEN5744", "NEN5744"),
    ("NEN5766", "NEN5766"),
    ("RWSgwmon", "RWSgwmon"),
    ("SIKB2001v6.0", "SIKB2001v6.0"),
    ("STOWAgwst", "STOWAgwst"),
    ("VKB2001", "VKB2001"),
    ("onbekend", "onbekend"),
)

GLUE = (
    ("geen", "geen"),
    ("ongespecificeerd", "ongespecificeerd"),
    ("onbekend", "onbekend"),
)

LOCALVERTICALREFERENCEPOINT = (("NAP", "NAP"),)

HORIZONTALPOSITIONINGMETHOD = (
    ("DGPS50tot200cm", "DGPS50tot200cm"),
    ("GPS200tot1000cm", "GPS200tot1000cm"),
    ("RTKGPS0tot2cm", "RTKGPS0tot2cm"),
    ("RTKGPS2tot5cm", "RTKGPS2tot5cm"),
    ("RTKGPS5tot10cm", "RTKGPS5tot10cm"),
    ("RTKGPS10tot50cm", "RTKGPS10tot50cm"),
    ("tachymetrie0tot10cm", "tachymetrie0tot10cm"),
    ("tachymetrie10tot50cm", "tachymetrie10tot50cm"),
    ("GBKNOnbekend", "GBKNOnbekend"),
    ("GPSOnbekend", "GPSOnbekend"),
    ("kaartOnbekend", "kaartOnbekend"),
    ("onbekend", "onbekend"),
)

TUBETOPPOSITIONINGMETHOD = (
    ("afgeleidSbl", "afgeleidSbl"),
    ("AHN2", "AHN2"),
    ("AHN3", "AHN3"),
    ("RTKGPS0tot4cm", "RTKGPS0tot4cm"),
    ("RTKGPS4tot10cm", "RTKGPS4tot10cm"),
    ("RTKGPS10tot20cm", "RTKGPS10tot20cm"),
    ("RTKGPS20tot100cm", "RTKGPS20tot100cm"),
    ("tachymetrie0tot10cm", "tachymetrie0tot10cm"),
    ("tachymetrie10tot50cm", "tachymetrie10tot50cm"),
    ("waterpassing0tot2cm", "waterpassing0tot2cm"),
    ("waterpassing2tot4cm", "waterpassing2tot4cm"),
    ("waterpassing4tot10cm", "waterpassing4tot10cm"),
    ("AHN1", "AHN1"),
    ("GPSOnbekend", "GPSOnbekend"),
    ("kaartOnbekend", "kaartOnbekend"),
    ("onbekend", "onbekend"),
)

GROUNDLEVELPOSITIONINGMETHOD = (
    ("afgeleidBovenkantBuis", "afgeleidBovenkantBuis"),
    ("AHN2", "AHN2"),
    ("AHN3", "AHN3"),
    ("RTKGPS0tot4cm", "RTKGPS0tot4cm"),
    ("RTKGPS4tot10cm", "RTKGPS4tot10cm"),
    ("RTKGPS10tot20cm", "RTKGPS10tot20cm"),
    ("RTKGPS20tot100cm", "RTKGPS20tot100cm"),
    ("tachymetrie0tot10cm", "tachymetrie0tot10cm"),
    ("tachymetrie10tot50cm", "tachymetrie10tot50cm"),
    ("waterpassing0tot2cm", "waterpassing0tot2cm"),
    ("waterpassing2tot4cm", "waterpassing2tot4cm"),
    ("waterpassing4tot10cm", "waterpassing4tot10cm"),
    ("AHN1", "AHN1"),
    ("geen", "geen"),
    ("GPSOnbekend", "GPSOnbekend"),
    ("kaartOnbekend", "kaartOnbekend"),
    ("onbekend", "onbekend"),
)

EVENTNAME = (
    ("constructie", "constructie"),
    ("beschermconstructieVeranderd", "beschermconstructieVeranderd"),
    ("buisdeelIngeplaatst", "buisdeelIngeplaatst"),
    ("buisIngekort", "buisIngekort"),
    ("buisOpgelengd", "buisOpgelengd"),
    ("buisstatusVeranderd", "buisstatusVeranderd"),
    ("eigenaarVeranderd", "eigenaarVeranderd"),
    ("elektrodestatusVeranderd", "elektrodestatusVeranderd"),
    ("maaiveldVerlegd", "maaiveldVerlegd"),
    ("nieuweBepalingMaaiveld", "nieuweBepalingMaaiveld"),
    ("nieuweBepalingPosities", "nieuweBepalingPosities"),
    ("nieuweInmetingMaaiveld", "nieuweInmetingMaaiveld"),
    ("nieuweInmetingPosities", "nieuweInmetingPosities"),
    ("onderhouderVeranderd", "onderhouderVeranderd"),
    ("verkenningenAchterafRegistreren", "verkenningenAchterafRegistreren"),
)

WELLSTABILITY = (
    ("instabiel", "instabiel"),
    ("stabielNAP", "stabielNAP"),
    ("onbekend", "onbekend"),
)

CRS = (
    ("RD", "RD"),
    ("ETRS89", "ETRS89"),
)

REGISTRATIONSTATUS = (
    ("aangevuld", "aangevuld"),
    ("geregistreerd", "geregistreerd"),
    ("voltooid", "voltooid"),
)

QUALITYREGIME = (
    ("IMBRO", "IMBRO"),
    ("IMBRO/A", "IMBRO/A"),
)

VERTICALDATUM = (("NAP", "NAP"),)

WELLHEADPROTECTOR_SUBTYPES = (
    ("DNS", "DNS"),
    ("model X", "model X"),
    ("onbekend", "onbekend"),
)

LOCKS = (
    ("sleutel", "sleutel"),
    ("inbus", "inbus"),
    ("onbekend", "onbekend"),
)

LABELS = (
    ("geen", "geen"),
    ("sticker", "sticker"),
    ("aluplaatje", "aluplaatje"),
    ("onbekend", "onbekend"),
)

FOUNDATIONS = (
    ("geen", "geen"),
    ("betonomstorting", "betonomstorting"),
    ("onbekend", "onbekend"),
)

COLLISION_PROTECTION_TYPES = (
    ("geen", "geen"),
    ("palen", "palen"),
    ("hekwerk", "hekwerk"),
    ("onbekend", "onbekend"),
)
