import requests
import json
import time
import geopandas as gpd
from shapely.geometry import Point
from collections import Counter, defaultdict
import csv
from pathlib import Path

from gmw.models import GroundwaterMonitoringWellStatic
from ...utils.bbox_extractor import BBOX_EXTRACTOR

class DataRetrieverBBOX:
    def __init__(self, bbox: BBOX_EXTRACTOR.BBOX):
        self.xmin = bbox.xmin
        self.xmax = bbox.xmax
        self.ymin = bbox.ymin
        self.ymax = bbox.ymax
        self.bbox = bbox.bbox
        self.bro_ids = []

    def request_bro_ids(self, type):
        options = ["gmw", "frd", "gar", "gmn", "gld"]
        if type.lower() not in options:
            raise Exception(f"Unknown type: {type}. Use a correct option: {options}.")
        
        features = process_request_for_bbox(type,self.bbox)
        self.features = features
        self.bro_ids = [feature["properties"].get("bro_id",None) for feature in features]

    def filter_ids_kvk(self, kvk_number):
        if kvk_number:
            for feature in self.features:
                kvk_id = feature["properties"].get("delivery_accountable_party",None)
                if kvk_number != kvk_id:
                    self.features.remove(feature)
            self.bro_ids = [feature["properties"].get("bro_id",None) for feature in self.features]
        
        print(f"{len(self.bro_ids)} points after filtering for kvk {kvk_number}.")

    def enforce_shapefile(self, shp, delete=False):
        gdf = gpd.read_file(shp)
        crs_bro = "EPSG:4326"
        crs_shp = gdf.crs.to_string()
        if crs_shp != crs_bro:
            gdf = gdf.to_crs(crs_bro)

        print("Number of bro ids before enforcing shapefile: ",len(self.bro_ids))
        for feature in self.features[:]:
            coord = feature["geometry"].get("coordinates",None)
            if not coord:
                raise Exception("No coordinate data found in feature")
            
            point = Point(coord[0], coord[1])
            if not gdf.contains(point).item():
                self.features.remove(feature)
        self.bro_ids = [feature["properties"].get("bro_id",None) for feature in self.features]

        print("Number of bro ids after enforcing shapefile: ",len(self.bro_ids))

        if delete:
            wells = GroundwaterMonitoringWellStatic.objects.filter(coordinates__isnull=False).all()
            for well in wells:
                point = Point(well.coordinates.x, well.coordinates.y)
                crs_shp = gdf.crs.to_string()
                if crs_shp != "EPSG:28992":
                    gdf = gdf.to_crs("EPSG:28992")

                if not gdf.contains(point).item():
                    well.delete()

    def get_ids_ogc(self):
        self.gmw_ids = []
        self.gld_ids = []
        self.frd_ids = []
        self.gar_ids = []
        self.gmn_ids = []
        self.other_ids = []

        for id in self.bro_ids:
            #print(id)
            if id.startswith("GMW"):
                self.gmw_ids.append(id)

            elif id.startswith("GLD"):
                self.gld_ids.append(id)

            elif id.startswith("FRD"):
                self.frd_ids.append(id)

            elif id.startswith("GAR"):
                self.gar_ids.append(id)

            elif id.startswith("GMN"):
                self.gmn_ids.append(id)

            else:
                self.other_ids.append(id)

def request_from_pdok(type,bbox) -> list:
    basis_url = "https://api.pdok.nl"
    ogc_verzoek = requests.get(
        f"{basis_url}/bzk/bro-gminsamenhang-karakteristieken/ogc/v1/collections/gm_{type}/items?bbox={bbox[0]}%2C{bbox[1]}%2C{bbox[2]}%2C{bbox[3]}&f=json&limit=1000"
    )
    try:
        features = json.loads(ogc_verzoek.text)["features"]
    except Exception as e:
        print("Exception when requesting data from PDOK: ",e)    
        
    return features

def subdivide_bbox(bbox):
    """
    Subdivide a bbox into four equal parts.
    """
    xmin, ymin, xmax, ymax = bbox
    xmid = (xmin + xmax) / 2
    ymid = (ymin + ymax) / 2
    return [
        (xmin, ymin, xmid, ymid),  # Bottom-left
        (xmid, ymin, xmax, ymid),  # Bottom-right
        (xmin, ymid, xmid, ymax),  # Top-left
        (xmid, ymid, xmax, ymax),  # Top-right
    ]

def process_request_for_bbox(type,bbox):
    """
    Recursively process and subdivide bbox until point count is under 1000.
    """
    stack = [bbox]
    features = []
    idx = 0

    while stack:
        current_bbox = stack.pop()
        results = request_from_pdok(type,current_bbox)
        print(f"Processing bbox {current_bbox}, found {len(results)} points")

        if len(results) < 1000:
            features.extend(results)
        else:
            stack.extend(subdivide_bbox(current_bbox))

        idx += 1
        if idx > 1e4:
            raise Exception("Forced an exception because amount of iterations was too high (>1000).")

        time.sleep(0.01)

    return features