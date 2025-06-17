import json
from collections import defaultdict
import csv
from pathlib import Path
from datetime import datetime

from ...utils.duplicate_checks import (
    scenario_1,
    scenario_2,
    scenario_3,
    rank_based_on_tubes,
    rank_based_on_dates,
    rank_based_on_quality,
    rank_based_on_bro_id,
)


class GMWDuplicatesHandler:
    def __init__(self, features):
        self.features = features

    def get_duplicates(self, properties: list):
        duplicates = defaultdict(list)
        seen = {prop: defaultdict(list) for prop in properties}
        assigned_bro_ids = set()

        # Collect all values for each property
        for feature in self.features:
            bro_id = feature["properties"].get("bro_id")
            if not bro_id:
                continue

            for prop in properties:
                value = feature["properties"].get(prop)
                if value is None or value == "":
                    continue
                seen[prop][value].append(bro_id)

        # Assign each bro_id to one duplicate group only
        for prop in properties:
            for value, bro_ids in seen[prop].items():
                if len(bro_ids) > 1:
                    for bro_id in bro_ids:
                        if bro_id not in assigned_bro_ids:
                            duplicates[(prop, value)].append(bro_id)
                            assigned_bro_ids.add(bro_id)

        self.duplicates = duplicates

    def rank_duplicates(self):
        features = self.features
        duplicates = self.duplicates
        features_dict = {
            feature["properties"].get("bro_id", None): feature for feature in features
        }
        self.features_ranked = []

        logging = (
            f"{datetime.now()} - INFO - Inputs"
            + "\nBBOX: _BBOX"
            + "\nKVK: _KVK"
            + "\nProperties: _PROPERTIES"
            + f"\n{datetime.now()} - START - Log"
        )
        for (prop, value), bro_ids in duplicates.items():
            features = [features_dict[bro_id] for bro_id in bro_ids]
            log = f"\n{prop} {value} | "
            if scenario_1(features):
                logging += log + "Scenario 1: Tube number differs"
                features_ranked = rank_based_on_tubes(features)
            elif scenario_2(features):
                logging += log + "Scenario 2: Dates allign"
                features_ranked = rank_based_on_dates(features)
            elif scenario_3(features):
                logging += log + "Scenario 3: Data quality differs"
                features_ranked = rank_based_on_quality(features)
            else:
                logging += (
                    log + "Scenario 4: All checks passed, BRO ID used for ranking"
                )
                features_ranked = rank_based_on_bro_id(features)

            self.features_ranked.extend(features_ranked)
            self.logging = logging + f"\n{datetime.now()} - END - Log"

    def store_duplicates(self, logging: bool, bbox, kvk, properties):
        duplicates = self.duplicates
        sorted_keys = sorted(duplicates.keys(), key=lambda x: str(x[1]))

        features_ranked = self.features_ranked
        features_dict = {
            feature["properties"].get("bro_id"): feature for feature in features_ranked
        }
        features = []
        for prop, value in sorted_keys:
            bro_ids = duplicates[(prop, value)]
            for bro_id in bro_ids:
                feature = features_dict[bro_id]
                features.append(feature)

        # Prepare the CSV file
        downloads_folder = Path.home() / "Downloads"
        date_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        duplicates_folder = downloads_folder / f"duplicates_bro_{date_time}"
        duplicates_folder.mkdir(parents=True, exist_ok=True)

        json_file = duplicates_folder / "bro_gmw_duplicate_well_codes.json"
        with open(json_file, "w") as f:
            json.dump(self.features, f, indent=4)

        csv_file = duplicates_folder / "bro_gmw_duplicate_well_codes.csv"
        with open(csv_file, mode="w", newline="", encoding="utf-8") as file:
            if not features:
                raise ValueError("No features to write")

            # Extract column headers from the first feature
            first_feature = features[0]
            feature_attributes = list(first_feature["properties"].keys()) + [
                "coordinates"
            ]
            fieldnames = feature_attributes

            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()

            # Write rows for each feature
            for feature in features:
                row = feature["properties"].copy()
                coordinates = feature.get("geometry", {}).get("coordinates", ())
                if coordinates:
                    coordinates = str(tuple(coordinates)).replace(",", "")

                row["coordinates"] = coordinates
                writer.writerow(row)

        if logging:
            logging_file = duplicates_folder / "logging.txt"
            with open(logging_file, "w", encoding="utf-8") as f:
                self.logging = self.logging.replace("_BBOX", str(bbox))
                self.logging = self.logging.replace("_KVK", str(kvk))
                self.logging = self.logging.replace("_PROPERTIES", str(properties))
                f.write(self.logging)
