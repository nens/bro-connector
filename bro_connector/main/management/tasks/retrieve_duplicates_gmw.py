from ..tasks.bro_handlers import GMWHandler
from ..tasks.kvk_handler import DataRetrieverKVK
from ..tasks.duplicates_handler import GMWDuplicatesHandler
from .ogc_handler import DataRetrieverOGC
from ..tasks.progressor import Progress
from ..tasks import events_handler
import reversion
import datetime
from django.conf import settings
from collections import Counter

from gmw.models import (
    GroundwaterMonitoringWellStatic,
    GroundwaterMonitoringWellDynamic,
    GroundwaterMonitoringTubeDynamic,
    GroundwaterMonitoringTubeStatic,
    GeoOhmCable,
    Electrode,
)
from bro.models import Organisation

import logging

logger = logging.getLogger(__name__)

def run(kvk_number=None, bro_type: str = "gmw", handler: str = "ogc"):
    bbox_settings = settings.BBOX_SETTINGS
    bbox = settings.BBOX
    shp = settings.POLYGON_SHAPEFILE
    if bbox_settings["use_bbox"] and handler == "ogc":
        print("bbox settings: ",bbox_settings)
        DR = DataRetrieverOGC(bbox)
        DR.request_bro_ids(bro_type)
        DR.filter_ids_kvk(kvk_number)
        DR.enforce_shapefile(shp,delete=False)
    else:
        raise Exception("Set use_bbox to true and set ogc as handler")
    
    GMWDH = GMWDuplicatesHandler(DR.bro_features)
    GMWDH.get_duplicates(properties=["well_code", "nitg_code"])
    GMWDH.rank_duplicates()
    GMWDH.store_duplicates()
    # GMWDH.omit_duplicates()
