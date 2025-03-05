import logging

import requests
from django.conf import settings

from gmw import models as gmw_models


logger = logging.getLogger(__name__)


### GENERAL UTILITY FUNCTION FOR OTHER VALIDATORS
def get_meetpunt_from_obj(obj) -> gmw_models.GroundwaterMonitoringWellStatic:
    if hasattr(obj, "groundwater_monitoring_well_static"):
        meetpunt = obj.groundwater_monitoring_well_static
    elif hasattr(obj, "groundwater_monitoring_tube_static"):
        meetpunt = obj.groundwater_monitoring_tube_static.groundwater_monitoring_well_static
    else:
        print(
            f"Currently not implemented object was given to the function: {type(obj)}"
        )
        meetpunt = None

    return meetpunt

def get_ahn_from_lizard(obj) -> float:
    meetpunt = get_meetpunt_from_obj(obj)
    # groundwatermonitoringwell = 

    url = "https://demo.lizard.net/api/v4/rasters/81ecd7d4-cff2-4704-9704-c5d6433b2824/point/"

    geom = f"SRID=28992;POINT({meetpunt.coordinates[0]} {meetpunt.coordinates[1]})"

    try:
        res = requests.get(
            url=url,
            headers=settings.LIZARD_SETTINGS["headers"],
            params={"geom": geom},
        )
        res.raise_for_status()
    except requests.exceptions.HTTPError:
        return -9999

    print(res.json(), settings.LIZARD_SETTINGS["headers"])
    print(res.json()["results"][0]["value"])

    return res.json()["results"][0]["value"]



#######################
###     FILTERS     ###
#######################

### FILTER (STATIC) AANPASSINGEN ###
def filter_top_higher_than_reference_heigth(filter: gmw_models.GroundwaterMonitoringTubeStatic) -> tuple:
    filtergeschiedenis = (
        gmw_models.GroundwaterMonitoringTubeDynamic.objects.filter(filter=filter)
        .order_by("datum_vanaf")
        .last()
    )

    valid = True
    message = ""

    try: 
        if filter.diepte_bovenkant_filter >= filtergeschiedenis.tube_top_position:
            valid = False
            message = f"De bovenkant filter waarde voor filter: {filter} was hoger dan de bovenkantbuis, daarom is die niet aangepast/ingevuld."
    except:  # noqa: E722
        logger.exception("Bare except")
        pass

    return (valid, message)

def filter_top_lower_than_filter_bottom(filter: gmw_models.GroundwaterMonitoringTubeStatic) -> tuple:
    valid = True
    message = ""

    if (
        filter.diepte_bovenkant_filter is not None
        and filter.diepte_onderkant_filter is not None
    ):
        if filter.diepte_bovenkant_filter <= filter.diepte_onderkant_filter:
            valid = False
            message = f"De bovenkant filter waarde voor filter: {filter} was lager dan de onderkant van het filter, daarom is die niet aangepast/ingevuld."

    return (valid, message)

def validate_filter_top_depth(obj: gmw_models.GroundwaterMonitoringTubeStatic) -> tuple:
    valid = []
    message = []

    (v, m) = filter_top_higher_than_reference_heigth(obj)
    valid.append(v)
    message.append(m)

    (v, m) = filter_top_lower_than_filter_bottom(obj)
    valid.append(v)
    message.append(m)

    if False in valid:
        valid = False
        message = " ".join(message)

    else:
        valid = True
        message = ""

    return (valid, message)



def filter_top_higher_than_reference_heigth(filter: gmw_models.GroundwaterMonitoringTubeStatic) -> tuple:
    filtergeschiedenis = (
        gmw_models.GroundwaterMonitoringTubeDynamic.objects.filter(filter=filter)
        .order_by("groundwater_monitoring_tube_dynamic_id")
        .last()
    )

    valid = True
    message = ""

    try:
        if filter.diepte_bovenkant_filter >= filtergeschiedenis.referentiehoogte:
            valid = False
            message = f"De bovenkant filter waarde voor filter: {filter} was hoger dan de bovenkantbuis, daarom is die niet aangepast/ingevuld."
    except:  # noqa: E722
        logger.exception("Bare except")
        pass

    return (valid, message)

def filter_top_changed_too_much(obj: gmw_models.GroundwaterMonitoringTubeStatic) -> tuple:
    valid = True
    message = ""
    max_verschil = 0.5

    originele_filter = gmw_models.GroundwaterMonitoringTubeStatic.objects.get(
        groundwater_monitoring_tube_static_id=obj.groundwater_monitoring_tube_static_id
        )

    if (
        originele_filter.scree is None
        or obj.diepte_bovenkant_filter is None
    ):
        return (valid, message)

    if obj.diepte_bovenkant_filter >= (
        originele_filter.diepte_bovenkant_filter + max_verschil
    ) or obj.diepte_bovenkant_filter <= (
        originele_filter.diepte_bovenkant_filter - max_verschil
    ):
        valid = False
        message = f"LET OP!! De waarde voor de diepte bovenkant filter is met meer dan \
            {max_verschil} meter veranderd, dit is niet toegestaan."

    return (valid, message)




### FILTERGESCHIEDENIS (DYNAMIC) AANPASSINGEN ###
def validate_logger_depth_filter(obj: gmw_models.GroundwaterMonitoringTubeDynamic) -> tuple:
    valid = True
    message = ""

    if (
        obj.meetinstrumentdiepte is not None
        and obj.referentiehoogte is not None
        and obj.filter.diepte_onderkant_buis is not None
    ):
        afstand_tot_onderkant_buis = (
            obj.referentiehoogte - obj.filter.diepte_onderkant_buis
        )

        if obj.meetinstrumentdiepte > afstand_tot_onderkant_buis:
            valid = False
            message = f"De meetinstrumentdiepte ({obj.meetinstrumentdiepte}) is langer dan de \
                afstand tot de onderkant van de buis ({afstand_tot_onderkant_buis})."

    return (valid, message)

def validate_reference_height(obj) -> tuple: 
    # filter = obj.groundwater_monitoring_tube_static
    valid = True

    if obj.screen_top_position is not None and obj.tube_top_position is not None:
        if obj.screen_top_position >= obj.tube_top_position:
            valid = False

    message = f"De ingevulde referentie hoogte voor filtergeschiedenis {obj} is lager dan de bovenkant één van zijn filters. \
        Daarom is de waarde niet aangepast."

    return (valid, message)

def validate_reference_height_ahn(obj: gmw_models.GroundwaterMonitoringTubeDynamic) -> tuple:
    valid = True
    message = ""

    ahn = get_ahn_from_lizard(obj)

    max_verschil = 3.0  # 3 meter verschil met AHN is maximum voor buiswaarde

    if obj.tube_top_position >= (ahn + max_verschil):
        valid = False
        message = f"LET OP!: De opgegeven referentie hoogte ({obj.tube_top_position}) is meer dan {max_verschil} \
            meter hoger dan de AHN2 waarde ({round(ahn, 2)})."

    elif obj.tube_top_position <= (ahn - max_verschil):
        valid = False
        message = f"LET OP!: De opgegeven referentie hoogte ({obj.tube_top_position}) is meer dan {max_verschil} \
            meter lager dan de AHN2 waarde ({round(ahn, 2)})."

    return (valid, message)

#######################
###      PUTTEN     ###
#######################

### MEETPUNT AANPASSINGEN ###

def x_within_netherlands(obj: gmw_models.GroundwaterMonitoringWellStatic) -> tuple:
    valid = True
    min_x = 0
    max_x = 270000
    message = "x-coordinaat ligt niet binnen de grenzen van Nederland voor EPSG:28892"
    
    if obj.coordinates[0]< min_x or obj.coordinates[0] > max_x:
        valid = False

    return (valid, message)

def y_within_netherlands(obj: gmw_models.GroundwaterMonitoringWellStatic) -> tuple:
    valid = True
    min_y = 150000
    max_y = 620000
    message = "y-coordinaat ligt niet binnen de grenzen van Nederland voor EPSG:28892"

    if obj.coordinates[1]< min_y or obj.coordinates[1] > max_y:
        valid = False

    return (valid, message)


def validate_x_coordinaat(obj: gmw_models.GroundwaterMonitoringWellStatic) -> tuple:
    valid = True
    max_afwijking = 100
    message = f"x-coordinaat wijkt meer dan {max_afwijking} meter af, daarom is de waarde niet aangepast."

    originele_put = gmw_models.GroundwaterMonitoringWellStatic.objects.filter(groundwater_monitoring_well_static_id=obj.groundwater_monitoring_well_static_id).first()

    verschil = abs(obj.coordinates[0] - originele_put.coordinates[0])

    if verschil > max_afwijking:
        valid = False

    return (valid, message)


def validate_y_coordinaat(obj: gmw_models.GroundwaterMonitoringWellStatic) -> tuple:
    valid = True
    max_afwijking = 100
    message = f"y-coordinaat wijkt meer dan {max_afwijking} meter af, daarom is de waarde niet aangepast."

    originele_put = gmw_models.GroundwaterMonitoringWellStatic.objects.filter(groundwater_monitoring_well_static_id=obj.groundwater_monitoring_well_static_id).first()

    verschil = abs(obj.coordinates[1] - originele_put.coordinates[1])

    if verschil > max_afwijking:
        valid = False

    return (valid, message)


### MEETPUNTGESCHIEDENIS (GroundwaterMonitoringWellDynamic) AANPASSINGEN ###
def validate_surface_height_filter(obj: gmw_models.GroundwaterMonitoringWellDynamic) -> tuple:
    valid = True
    
    filters = gmw_models.GroundwaterMonitoringTubeStatic.objects.filter(
        groundwater_monitoring_well_static=obj.groundwater_monitoring_well_static
    )
    
    for filter in filters:
        filters_dynamic = (
            gmw_models.GroundwaterMonitoringTubeDynamic.objects.filter(
                groundwater_monitoring_tube_static=filter.groundwater_monitoring_tube_static
            )
        .order_by("datum_vanaf")
        .last()
        )

        
        try:
            if obj.ground_level_position <= filter.diepte_onderkant_filter:
                valid = False
        except:  # noqa: E722
            logger.exception("Bare except")
            pass

    message = f"De ingevulde maaiveld hoogte voor meetpuntgeschiedenis {obj} is lager dan de onderkant van één van zijn filters. \
        Daarom is de waarde niet aangepast."

    return (valid, message)

def validate_surface_height_ahn(obj: gmw_models.GroundwaterMonitoringWellDynamic) -> tuple:
    valid = True
    message = ""

    ahn = get_ahn_from_lizard(obj)

    if not obj.ground_level_position:
        valid = False
        message = f"LET OP: Er is geen ingevulde maaiveldhoogte voor de meetpuntgeschiedenis van {obj}."

    elif obj.ground_level_position > (ahn + 0.50):
        valid = False
        message = f"LET OP: De ingevulde maaiveld hoogte voor meetpuntgeschiedenis {obj} is hoger dan de AHN2 + 50 cm ({round(ahn, 2)})."

    elif obj.ground_level_position < (ahn - 0.50):
        valid = False
        message = f"LET OP: De ingevulde maaiveld hoogte voor meetpuntgeschiedenis {obj} is lager dan de AHN2 - 50 cm ({round(ahn, 2)})."

    return (valid, message)

