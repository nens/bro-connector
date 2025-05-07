import requests
import json
import time
import geopandas as gpd
from shapely.geometry import Point
from collections import Counter, defaultdict
import csv
from pathlib import Path

from gmw.models import GroundwaterMonitoringWellStatic

class DataRetrieverOGC:
    def __init__(self, bbox):
        self.xmin = bbox.xmin
        self.xmax = bbox.xmax
        self.ymin = bbox.ymin
        self.ymax = bbox.ymax
        self.bbox = (self.xmin, self.ymin, self.xmax, self.ymax)
        self.bro_ids = []

    def request_bro_ids(self, type):
        options = ["gmw", "frd", "gar", "gmn", "gld"]
        if type.lower() not in options:
            raise Exception(f"Unknown type: {type}. Use a correct option: {options}.")
        

        features = process_request_for_bbox(type,self.bbox)
        # self.features = features

        self.bro_ids = []
        self.bro_coords = []
        self.kvk_ids = []
        self.well_codes = []
        self.bro_features = []
        if features:
            print(f"{len(features)} received from bbox")
            ## add a while loop that divides the bbox into smaller ones if the len = 1000
            for feature in features:
                if feature["properties"]["bro_id"] == "GMW000000064982":
                    print(feature)

                self.bro_ids.append(feature["properties"]["bro_id"])
                self.bro_coords.append(feature["geometry"]["coordinates"])
                self.kvk_ids.append(feature["properties"]["delivery_accountable_party"])
                self.well_codes.append(feature["properties"]["well_code"])
            
            self.bro_features = features

        

    def filter_ids_kvk(self, kvk_number):
        if kvk_number:
            for bro_id, kvk_id in zip(self.bro_ids[:], self.kvk_ids):
                if kvk_number != kvk_id:
                    #print("Removing ",bro_id)
                    self.bro_ids.remove(bro_id)
        
        print(f"{len(self.bro_ids)} points after filtering for kvk {kvk_number}.")

    def enforce_shapefile(self, shp, delete=False):
        gdf = gpd.read_file(shp)
        crs_bro = "EPSG:4326"
        crs_shp = gdf.crs.to_string()
        if crs_shp != crs_bro:
            gdf = gdf.to_crs(crs_bro)

        print("Number of bro ids before enforcing shapefile: ",len(self.bro_ids))
        for id,coord,code,feat in zip(self.bro_ids[:], self.bro_coords[:], self.well_codes[:], self.bro_features[:]):
            point = Point(coord[0], coord[1])
            is_within = gdf.contains(point).item()

            if not is_within:
                self.bro_ids.remove(id)
                self.bro_coords.remove(coord)
                self.well_codes.remove(code)
                self.bro_features.remove(feat)

        print("Number of bro ids after enforcing shapefile: ",len(self.bro_ids))

        if delete:
            wells = GroundwaterMonitoringWellStatic.objects.filter(coordinates__isnull=False).all()
            for well in wells:
                point = Point(well.coordinates.x, well.coordinates.y)
                crs_shp = gdf.crs.to_string()
                if crs_shp != "EPSG:28992":
                    gdf = gdf.to_crs("EPSG:28992")

                is_within = gdf.contains(point).item()
                if not is_within:
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

    def get_ids_with_duplicate_well_codes(self):
        bro_ids = self.bro_ids
        well_codes = self.well_codes
        nitg_codes = [feat["properties"]["nitg_code"] for feat in self.bro_features]

        print(len(bro_ids))
        print(len(well_codes))

        duplicates = {}
        for bro_id, well_code, nitg_code in zip(bro_ids,well_codes,nitg_codes):
            if Counter(well_codes)[well_code] > 1 and Counter(nitg_codes)[nitg_code] > 1: ## do we want functionality for None values of well code?
                if not well_code in duplicates.keys():
                    duplicates[well_code] = []
                duplicates[well_code].append(bro_id)


        self.duplicate_well_codes = duplicates

    def store_duplicates_as_csv(self, type):

        duplicates = self.duplicate_well_codes
        well_codes = list(duplicates.keys())
        well_code_ordering = {key: index for index, key in enumerate(well_codes)}
        features_all = self.bro_features
        ## sort based on well code
        features_unsorted = [feat for feat in features_all if feat["properties"]["well_code"] in well_codes]
        features = sorted(features_unsorted, key=lambda d:well_code_ordering.get(d["properties"]["well_code"], len(well_code_ordering)))

        print(len(features_all))
        print(len(features))

        # Prepare the CSV file
        csv_file = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "csv" / "bro_gmw_duplicate_well_codes.csv"

        with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
            if not features:
                raise ValueError("No features to write")

            # Extract column headers from the first feature
            first_feature = features[0]
            feature_attributes = list(first_feature['properties'].keys()) + ["coordinates"]
            fieldnames = feature_attributes

            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()

            # Write rows for each feature
            for feature in features:
                row = feature['properties'].copy()
                print(row["bro_id"],row["well_code"])
                if row["well_code"] == "":
                    print("Huh")
                coordinates = feature.get('geometry',{}).get('coordinates',())
                if coordinates:
                    coordinates = str(tuple(coordinates)).replace(",","")
                
                row['coordinates'] = coordinates
                writer.writerow(row)


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