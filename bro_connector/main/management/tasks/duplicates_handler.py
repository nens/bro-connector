import requests
import json
import time
import geopandas as gpd
from shapely.geometry import Point
from collections import Counter, defaultdict
import csv
from pathlib import Path
from datetime import datetime
import json

from gmw.models import GroundwaterMonitoringWellStatic

class RANKING:
    class NAMES:
        TUBE_RANKING = "Tube Ranking"
        QUALITY_RANKING = "Quality Regime Ranking"
        UKNONWN_RANKING = "Unknwon Values Ranking"
        EMPTY_RANKING = "Empty Values Ranking"
        DATE_RANKING = "Construction Date Ranking"
    class WEIGHTS:
        TUBE_WEIGHT = 1
        QUALTIY_WEIGHT = 1
        UNKNOWN_WEIGHT = 1
        EMPTY_WEIGHT = 1
        DATE_WEIGHT = 1

class GMWDuplicatesHandler:
    def __init__(self, features):
        self.features = features

    def get_duplicates(self, properties: list[str] = ["well_code"]):        
        # duplicates = defaultdict(list)
        # seen = defaultdict(list)

        # for feature in self.features:
        #     bro_id = feature["properties"].get("bro_id")
        #     property_values = [feature["properties"].get(prop) for prop in properties]

        #     for i,prop in enumerate(property_values):
        #         if prop == None:
        #             property_values[i] = ""
        #     seen[property_values[0]].append(bro_id)

        # for prop, bro_ids in seen.items():
        #     if len(bro_ids) > 1:
        #         duplicates[prop].extend(bro_ids)

        # self.duplicates = dict(duplicates)

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

    # def get_duplicates(self, properties: list[str] = ["well_code"]):
    #     duplicates = defaultdict(list)

    #     for prop in properties:
    #         seen = defaultdict(list)
    #         for feature in self.features:
    #             bro_id = feature["properties"].get("bro_id")
    #             value = feature["properties"].get(prop)
                
    #             if value is None or value == "":
    #                 continue  # skip missing or empty values

    #             seen[value].append(bro_id)
            
    #         for value, bro_ids in seen.items():
    #             if len(bro_ids) > 1:
    #                 duplicates[(prop, value)].extend(bro_ids)
        
    #     return duplicates

    def rank_duplicates(self):
        ## 2. IMBRO is better than IMBRO/A (after 01-01-2021)
        ## 3. least amount of onbekend is best
        ## 4. most amount of tubes is best
        ## 5. take the latest registration time
        ## 6. empty ground level position is bad
        ## 7. check if it has a GLD
        
        ## 


        # --> For every test, rank the bro ids. Then take the average ranking.
        def get_duplicate_features(features: list[dict], bro_ids: list):
            duplicate_features = []
            for feature in features:
                bro_id = feature["properties"].get("bro_id",None)
                if bro_id in bro_ids:
                    duplicate_features.append(feature)
                    
            return duplicate_features
        
        def normalize_ranking(ranking: dict) -> dict:
            # Normalize ranks to scores: score = 1 - (rank - 1) / (max_rank - 1)
            normalized = {}
            max_rank = max(ranking.values())
            for bro_id, rank in ranking.items():
                if max_rank == 1:
                    score = 1.0
                else:
                    score = 1 - (rank - 1) / (max_rank - 1)
                normalized[bro_id] = round(score, 4)

            return normalized
        
        def isoformat(date_string: str):
                if date_string:
                    if "-" not in date_string:
                        return date_string + "-01-01"
                return date_string

        def amount_of_tubes_ranking(features: list[dict]):
            tubes = {}
            ranking = {}

            for feature in features:
                properties: dict = feature.get("properties", {})
                bro_id = properties.get("bro_id",None)
                n_tubes = properties.get("number_of_monitoring_tubes",0)
                tubes[bro_id] = n_tubes

            prev_tubes = None
            current_rank = 0
            tubes_sorted = sorted(tubes.items(), key=lambda x: -x[1]) ## descending sorting for n_tubes
            for i, (bro_id, n_tubes) in enumerate(tubes_sorted):
                if n_tubes != prev_tubes:
                    current_rank = i + 1
                    prev_tubes = n_tubes
                ranking[bro_id] = current_rank

            return normalize_ranking(ranking)

        def quality_regime_ranking(features: list[dict]):
            ranking = {}
            ranking_tiers = defaultdict(list)

            for feature in features:
                properties: dict = feature.get("properties", {})
                bro_id = properties.get("bro_id", None)
                regime = properties.get("quality_regime", None)

                # Extract relevant timestamps
                ## get the latest data from the GLD

                timestamps = [
                    # properties.get("object_registration_time", None),
                    # properties.get("latest_addition_time", None),
                    # properties.get("registration_completion_time", None)
                    isoformat(properties.get("well_construction_date", None))
                ]
                # Parse and find the most recent non-None datetime
                dates = [datetime.fromisoformat(ts) for ts in timestamps if ts]
                latest_date = max(dates) if dates else None

                if regime == "IMBRO":
                    tier = "IMBRO"
                elif regime == "IMBRO/A":
                    if latest_date and latest_date <= datetime(2021, 1, 1):#, tzinfo=latest_date.tzinfo):
                        tier = "IMBRO/A_OLD"
                    else:
                        tier = "IMBRO/A_NEW"
                else:
                    tier = "OTHER"

                ranking_tiers[tier].append(bro_id)

            tier_priority = ["IMBRO", "IMBRO/A_OLD", "IMBRO/A_NEW", "OTHER"]

            # Assign dynamic ranks
            current_rank = 1
            for tier in tier_priority:
                if tier in ranking_tiers:
                    for bro_id in ranking_tiers[tier]:
                        ranking[bro_id] = current_rank
                    current_rank += 1

            return normalize_ranking(ranking)

        def unknown_values_ranking(features: list[dict]):
            ranking = {}
            unknowns = {}

            for feature in features:
                properties: dict = feature.get("properties", {})
                bro_id = properties.get("bro_id")
                unknown_count = 0

                for prop, value in properties.items():
                    if "date" in prop.lower() or "time" in prop.lower():
                        continue
                    if isinstance(value, str) and value.strip().lower() == "onbekend":
                        unknown_count += 1

                unknowns[bro_id] = unknown_count

            prev_count = None
            current_rank = 0
            unkonwns_sorted = sorted(unknowns.items(), key=lambda x: x[1])
            for i, (bro_id, count) in enumerate(unkonwns_sorted):
                if count != prev_count:
                    current_rank = i + 1
                    prev_count = count
                ranking[bro_id] = current_rank

            return normalize_ranking(ranking)

        def empty_values_ranking(features: list[dict]):
            ranking = {}
            empties = {}

            for feature in features:
                properties: dict = feature.get("properties", {})
                bro_id = properties.get("bro_id", None)
                empty_count = 0

                for key, value in properties.items():
                    if "date" in key.lower() or "time" in key.lower():
                        continue
                    if value is None or (isinstance(value, str) and value.strip() == ""):
                        empty_count += 1

                empties[bro_id] = empty_count

            prev_count = None
            current_rank = 0
            empties_sorted = sorted(empties.items(), key=lambda x: x[1])
            for i, (bro_id, count) in enumerate(empties_sorted):
                if count != prev_count:
                    current_rank = i + 1
                    prev_count = count
                ranking[bro_id] = current_rank

            return normalize_ranking(ranking)

        def well_construction_date_ranking(features: list[dict[str, dict]]):            
            ranking = {}
            dates = {}

            for feature in features:
                properties = feature.get("properties", {})
                bro_id = properties.get("bro_id", None)
                date_str = isoformat(properties.get("well_construction_date", None))

                if date_str:
                    try:
                        date_obj = datetime.fromisoformat(date_str)
                        dates[bro_id] = date_obj
                    except ValueError:
                        raise Exception("Something went wrong with converting to isoformat")

            prev_date = None
            current_rank = 0
            dates_sorted = sorted(dates.items(), key=lambda x: x[1], reverse=True)
            for i, (bro_id, date) in enumerate(dates_sorted):
                if date != prev_date:
                    current_rank = i + 1
                    prev_date = date
                ranking[bro_id] = current_rank

            return normalize_ranking(ranking)

        def get_overall_ranking(features: list, duplicates: dict, rankings: dict):
            features_ranked = []
            ranks = {}
            scores = {}

            for (prop_name, prop), bro_ids in duplicates.items():
                scores[prop] = {}
                for bro_id in bro_ids:
                    score = score_feature(rankings[prop], bro_id)
                    scores[prop][bro_id] = score

            def convert_scores_to_ranks(scores: dict[str, dict[str]], features: list[dict]) -> dict:
                # Preprocess: Map bro_id to registration_time
                times = {}
                for feature in features:
                    bro_id = feature.get("properties", {}).get("bro_id")
                    time_str = feature.get("properties", {}).get("object_registration_time")
                    if bro_id and time_str:
                        try:
                            times[bro_id] = datetime.fromisoformat(time_str)
                        except ValueError:
                            times[bro_id] = datetime.min  # fallback to oldest if parse fails

                ranks = {}

                for prop, bro_scores in scores.items():
                    # Prepare sortable list: (bro_id, score, registration_time)
                    scored_items = [
                        (bro_id, score, times.get(bro_id, datetime.min))
                        for bro_id, score in bro_scores.items()
                    ]

                    # Sort: highest score first, then latest time first
                    sorted_items = sorted(scored_items, key=lambda x: (-x[1], -x[2].timestamp()))

                    prop_ranks = {}
                    prev_score, prev_time = None, None
                    current_rank = 0
                    for i, (bro_id, score, reg_time) in enumerate(sorted_items):
                        if score != prev_score or reg_time != prev_time:
                            current_rank = i + 1
                            prev_score = score
                            prev_time = reg_time
                        prop_ranks[bro_id] = current_rank

                    ranks[prop] = prop_ranks

                return ranks
            
            ranks = convert_scores_to_ranks(scores, features)

            for (prop_name, prop), bro_ids in duplicates.items():
                for bro_id in bro_ids:
                    ranking = ranks[prop][bro_id]
                    feature = get_feature(features, bro_id)
                    if feature:
                        feature["properties"]["ranking"] = ranking
                        features_ranked.append(feature)

            return features_ranked

        def score_feature(ranking: dict, bro_id: str) -> float:
            ranks_weighted = []
            sum_weights = 0
            for ranking_name, ranking_data in ranking.items():
                # print(ranking_name)
                # print(ranking_data)
                ranking_data: dict
                rank = ranking_data.get(bro_id, None)
                
                if rank != None:
                    match ranking_name:
                        case RANKING.NAMES.TUBE_RANKING:
                            weight = 0
                            if ranking.get(RANKING.NAMES.TUBE_RANKING, None):
                                weight = RANKING.WEIGHTS.TUBE_WEIGHT
                            sum_weights += weight
                            rank_weighted = weight*rank
                            ranks_weighted.append(rank_weighted)
                        case RANKING.NAMES.QUALITY_RANKING:
                            weight = 0
                            if ranking.get(RANKING.NAMES.QUALITY_RANKING, None):
                                weight = RANKING.WEIGHTS.QUALTIY_WEIGHT
                            sum_weights += weight
                            rank_weighted = weight*rank
                            ranks_weighted.append(rank_weighted)
                        case RANKING.NAMES.UKNONWN_RANKING:
                            weight = 0
                            if ranking.get(RANKING.NAMES.UKNONWN_RANKING, None):
                                weight = RANKING.WEIGHTS.UNKNOWN_WEIGHT
                            sum_weights += weight
                            rank_weighted = weight*rank
                            ranks_weighted.append(rank_weighted)
                        case RANKING.NAMES.EMPTY_RANKING:
                            weight = 0
                            if ranking.get(RANKING.NAMES.EMPTY_RANKING, None):
                                weight = RANKING.WEIGHTS.EMPTY_WEIGHT
                            sum_weights += weight
                            rank_weighted = weight*rank
                            ranks_weighted.append(rank_weighted)
                        case RANKING.NAMES.DATE_RANKING:
                            weight = 0
                            if ranking.get(RANKING.NAMES.DATE_RANKING, None):
                                weight = RANKING.WEIGHTS.DATE_WEIGHT
                            sum_weights += weight
                            rank_weighted = weight*rank
                            ranks_weighted.append(rank_weighted)
                
            ranking = None
            if ranks_weighted and sum_weights != 0:
                ranking = sum(ranks_weighted) / sum_weights

            return ranking  

        def get_feature(features: list, bro_id: str):
            for feature in features:
                if bro_id == feature["properties"].get("bro_id", None):
                    return feature
                
            return None
            
        ranking = {}
        duplicates = self.duplicates

        for (prop_name, prop), bro_ids in duplicates.items():
            features = get_duplicate_features(self.features, bro_ids)
            ranking[prop] = {}
            ranking[prop][RANKING.NAMES.TUBE_RANKING] = amount_of_tubes_ranking(features)
            ranking[prop][RANKING.NAMES.QUALITY_RANKING] = quality_regime_ranking(features)
            ranking[prop][RANKING.NAMES.UKNONWN_RANKING] = unknown_values_ranking(features)
            ranking[prop][RANKING.NAMES.EMPTY_RANKING] = empty_values_ranking(features)
            ranking[prop][RANKING.NAMES.DATE_RANKING] = well_construction_date_ranking(features)      

        duplicate_ids = [bro_id for bro_ids in duplicates.values() for bro_id in bro_ids]
        duplicate_features = get_duplicate_features(self.features, duplicate_ids)
        ranked_features = get_overall_ranking(duplicate_features, duplicates, ranking)
        self.features_ranked = ranked_features
        self.ranking = ranking

    def store_duplicates(self):

        duplicates = self.duplicates
        sorted_keys = sorted(duplicates.keys(), key=lambda x: str(x[1]))

        features_ranked  = self.features_ranked
        features_dict = {
            feature["properties"].get("bro_id"): feature
            for feature in features_ranked
        }
        features = []
        for prop, value in sorted_keys:
            bro_ids = duplicates[(prop, value)]
            for bro_id in bro_ids:
                feature = features_dict[bro_id]
                features.append(feature)

        # Prepare the CSV file
        json_file = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "duplicates" / "ranking_output.json"
        json_file1 = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "duplicates" / "bro_gmw_duplicate_well_codes.json"
        csv_file = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "duplicates" / "bro_gmw_duplicate_well_codes.csv"

        with open(json_file, "w") as f:
            json.dump(self.ranking, f, indent=4)

        with open(json_file1, "w") as f:
            json.dump(self.features, f, indent=4)

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
                coordinates = feature.get('geometry',{}).get('coordinates',())
                if coordinates:
                    coordinates = str(tuple(coordinates)).replace(",","")
                
                row['coordinates'] = coordinates
                writer.writerow(row)