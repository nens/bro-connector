class Ranking:
    class Names:
        unknown_ranking = "Unknwon Values Ranking"
        empty_ranking = "Empty Values Ranking"
    class Weights:
        unknown_weight = 1
        empty_weight = 1

def score_data_quality(features: list, unkown_data: dict, empty_data: dict):
    ranking_unknown = {}
    prev_count = None
    current_rank = 0
    unknowns_sorted = sorted(unkown_data.items(), key=lambda x: x[1])

    for i, (bro_id, count) in enumerate(unknowns_sorted):
        if count != prev_count:
            current_rank = i + 1
            prev_count = count
        ranking_unknown[bro_id] = current_rank

    ranking_empty = {}
    prev_count = None
    current_rank = 0
    empties_sorted = sorted(empty_data.items(), key=lambda x: x[1])
    for i, (bro_id, count) in enumerate(empties_sorted):
        if count != prev_count:
            current_rank = i + 1
            prev_count = count
        ranking_empty[bro_id] = current_rank

    scores = {}
    bro_ids = [feature.get("properties").get("bro_id", None) for feature in features]
    for bro_id in bro_ids:
        weight_unknown = Ranking.Weights.unknown_weight
        rank_unknown = ranking_unknown[bro_id]
        weight_empty = Ranking.Weights.empty_weight
        rank_empty = ranking_empty[bro_id]

        rank_weighted = sum([weight_unknown*rank_unknown, weight_empty*rank_empty]) / sum([weight_unknown, weight_empty])
        scores[bro_id] = rank_weighted

    return scores

def rank_scores(data: dict):
    ranking_sorted = sorted(data.items(), key=lambda x: x[1])
    ranking = {}
    current_rank = 1
    i = 0
    while i < len(ranking_sorted):
        # Find all items with same value
        val = ranking_sorted[i][1]
        same_value_keys = [ranking_sorted[i][0]]
        
        j = i + 1
        while j < len(ranking_sorted) and ranking_sorted[j][1] == val:
            same_value_keys.append(ranking_sorted[j][0])
            j += 1
        
        # Assign same rank to all those keys
        for key in same_value_keys:
            ranking[key] = current_rank
        
        current_rank += 1
        i = j
    return ranking

def check_for_tubes(features):
    tubes = [feature["properties"].get("number_of_monitoring_tubes") for feature in features]
    return len(set(tubes)) > 1

def check_for_dates(features):           
    construction_dates = [feature["properties"].get("well_construction_date") for feature in features]
    removal_dates = [feature["properties"].get("well_removal_date") for feature in features]
    return any(date is not None and date in removal_dates for date in construction_dates)

def check_for_data_quality(features):
    unknowns = {}
    empties = {}

    for feature in features:
        properties: dict = feature.get("properties", {})
        bro_id = properties.get("bro_id")
        unknown_count = 0
        empty_count = 0

        for prop, value in properties.items():
            if "date" in prop.lower() or "time" in prop.lower():
                continue
            if isinstance(value, str) and value.strip().lower() == "onbekend":
                unknown_count += 1
            if value is None or (isinstance(value, str) and value.strip() == ""):
                empty_count += 1
        
        unknowns[bro_id] = unknown_count
        empties[bro_id] = empty_count

    scores = score_data_quality(features, unknowns, empties)          
    return len(set(scores.values())) > 1

def rank_based_on_tubes(features):
    return rank_based_on_dates(features)

def rank_based_on_dates(features):
    bro_ids = [feature.get("properties").get("bro_id", None) for feature in features]
    dates = {f["properties"].get("bro_id"): f["properties"].get("well_construction_date") for f in features}
    sorted_dates = sorted(set(dates.values()))  # Unique and sorted dates
    rank_map = {date: rank + 1 for rank, date in enumerate(sorted_dates)}
    ranks = {bro_id: rank_map[date] for bro_id, date in dates.items()}

    for feature in features:
        bro_id = feature["properties"].get("bro_id")
        if bro_id in bro_ids:
            feature["properties"].update({"rank": ranks[bro_id]})

    return features

def rank_based_on_quality(features):
    bro_ids = [feature.get("properties").get("bro_id", None) for feature in features]            
    unknowns = {}
    empties = {}

    for feature in features:
        properties: dict = feature.get("properties", {})
        bro_id = properties.get("bro_id")
        unknown_count = 0
        empty_count = 0

        for prop, value in properties.items():
            if "date" in prop.lower() or "time" in prop.lower():
                continue
            if isinstance(value, str) and value.strip().lower() == "onbekend":
                unknown_count += 1
            if value is None or (isinstance(value, str) and value.strip() == ""):
                empty_count += 1
        
        unknowns[bro_id] = unknown_count
        empties[bro_id] = empty_count

    scores = score_data_quality(features, unknowns, empties)
    ranks = rank_scores(scores)

    for feature in features:
        bro_id = feature["properties"].get("bro_id")
        if bro_id in bro_ids:
            feature["properties"].update({"rank": ranks[bro_id]})

    return features

def rank_based_on_bro_id(features):
    bro_ids = [feature.get("properties").get("bro_id", None) for feature in features]
    sorted_bro_ids = sorted(bro_ids)
    ranks = {bro_id: rank + 1 for rank, bro_id in enumerate(sorted_bro_ids)}

    for feature in features:
        bro_id = feature["properties"].get("bro_id")
        if bro_id in bro_ids:
            feature["properties"].update({"rank": ranks[bro_id]})

    return features