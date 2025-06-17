from ..tasks.duplicates_handler import GMWDuplicatesHandler
from .bbox_handler import DataRetrieverBBOX
from django.conf import settings


def run(kvk_number, properties, logging):
    if not properties:
        raise Exception(
            "Specificeer minimaal 1 feature property om duplicaten voor te zoeken"
        )

    bbox_settings = settings.BBOX_SETTINGS
    bbox = settings.BBOX
    shp = settings.POLYGON_SHAPEFILE
    if bbox_settings["use_bbox"]:
        DR = DataRetrieverBBOX(bbox)
        DR.request_bro_ids("gmw")
        DR.filter_ids_kvk(kvk_number)
        DR.enforce_shapefile(shp, delete=False)
    else:
        raise Exception("Set use_bbox to true")

    GMWDH = GMWDuplicatesHandler(DR.features)
    if GMWDH.features:
        for feature in GMWDH.features:
            feature_properties = set(feature["properties"])
            if [prop for prop in properties if prop not in feature_properties]:
                raise Exception("Opgegeven properties niet aanwezig in (alle) features")

    GMWDH.get_duplicates(properties)
    GMWDH.rank_duplicates()
    GMWDH.store_duplicates(logging, bbox.bbox, kvk_number, properties)
