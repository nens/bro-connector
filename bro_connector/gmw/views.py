# Create your views here.
from django.views.decorators.cache import cache_page
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache

from django.http import HttpResponse
from django.db.models import OuterRef, Subquery, Prefetch
from django.shortcuts import render
from gmw.models import (
    GroundwaterMonitoringWellStatic,
)
from bro.models import Organisation
from gld.models import GroundwaterLevelDossier
import gmn.models as gmn_models
import gld.models as gld_models
import gmw.models as gmw_models
from . import serializers
import bro.serializers as bro_serializers
from django.conf import settings
import time

@csrf_exempt
def gmw_visible_wells(request):
    print("doing the funky visible well request")
    if request.method == "POST":
        try:
            content = json.loads(request.body)
            cache_key = get_cache_key(request)
            cache.set(cache_key, content, timeout=3600)

            ids = []
            if content:
                ids = content.get("ids", [])
            return JsonResponse({"status": "ok", "count": len(ids)})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)

def get_map_center(settings):
    wells = GroundwaterMonitoringWellStatic.objects.all()

    if settings.USE_WELLS_AS_MAP_CENTER and len(wells) > 0:
        latitudes, longitudes = [w.lat for w in wells], [w.lon for w in wells]
        center_coordinate = {"lat": sum(latitudes) / len(latitudes), "lon": sum(longitudes) / len(longitudes)}

    else:
        center_coordinate = {"lat": settings.MAP_CENTER[1], "lon": settings.MAP_CENTER[0]}

    return center_coordinate

def get_cache_key(request):
    if not request.session.session_key:
        request.session.save()

    if request.path.startswith("/map/validation"):
        cache_base = "/map/"
    else:
        cache_base = request.path

    session_id = request.session.session_key
    cache_key = f"map:{session_id}:{cache_base}"
    print("Created cache key: ",cache_key)
    return cache_key

from django.db.models import Max, Q

def get_glds_with_latest_data_fast():
    start = time.time()
    print("# Step 1: Find newest observation per GLD (based on observation_starttime)")
    latest_obs_subquery = (
        gld_models.Observation.objects
        .filter(
            groundwater_level_dossier=OuterRef('pk'),
            observation_starttime__isnull=False
        )
        .order_by('-observation_starttime')
        .values('pk')[:1]
    )
    latest_obs_per_gld = (
        gld_models.GroundwaterLevelDossier.objects
        .annotate(latest_obs_id=Subquery(latest_obs_subquery))
        .values('pk', 'latest_obs_id')
    )
    obs_id_map = {
        row['pk']: row['latest_obs_id']
        for row in latest_obs_per_gld if row['latest_obs_id']
    }

    start = time.time()
    print("# Step 2: Fetch all GLDs in one go")
    glds = list(gld_models.GroundwaterLevelDossier.objects.all())
    end = time.time()
    print(f"time to run step: {end-start}")

    print("# Step 3: Get all latest observations in one go")
    observations = list(
        gld_models.Observation.objects.filter(pk__in=obs_id_map.values())
    )
    obs_map = {o.pk: o for o in observations}
    end = time.time()
    print(f"time to run step: {end-start}")
    
    start = time.time()
    print("# Step 4: Find newest measurement per observation (batch query)")
    # latest_meas_per_obs = (
    #     gld_models.MeasurementTvp.objects
    #     .filter(observation_id__in=obs_map.keys())
    #     .values('observation_id')
    #     .annotate(latest_meas_id=Max('measurement_tvp_id', filter=Q(measurement_time__isnull=False)))
    # )
    latest_meas_subquery = (
        gld_models.MeasurementTvp.objects
        .filter(observation=OuterRef("pk"), measurement_time__isnull=False)
        .order_by("-measurement_time")
        .values("pk")[:1]
    )

    latest_meas_per_obs = (
        gld_models.Observation.objects
        .filter(pk__in=obs_map.keys())
        .annotate(latest_meas_id=Subquery(latest_meas_subquery))
    )
    meas_id_map = {
        o.observation_id: o.latest_meas_id
        for o in latest_meas_per_obs if o.latest_meas_id
    }
    end = time.time()
    print(f"time to run step: {end-start}")

    start = time.time()
    print("# Step 5: Fetch those measurements in bulk")
    measurements = {
        m.pk: m
        for m in gld_models.MeasurementTvp.objects.filter(pk__in=meas_id_map.values())
    }
    end = time.time()
    print(f"time to run step: {end-start}")

    start = time.time()
    print("# Step 6: Attach to objects") 
    for obs in observations:
        obs.latest_measurement = measurements.get(meas_id_map.get(obs.pk))

    for gld in glds:
        gld.latest_observation = obs_map.get(obs_id_map.get(gld.pk))

    end = time.time()
    print(f"time to run step: {end-start}")

    return glds

def gmw_map_context(request):
    # cache.clear()
    cache_key = get_cache_key(request)
    cached_context = cache.get(cache_key)
    if cached_context:
        print("already cached")
        response = render(request, "map.html", cached_context)
        return response
    
    map_center = get_map_center(settings)

    gld_qs = get_glds_with_latest_data_fast()
    print("wells: ")
    start = time.time()
    glds = serializers.GLDSerializer(gld_qs, many=True).data
    end = time.time()
    print(f"finished in {end-start}s")
    # print(gld.latest_measurement)
    # print(gld.latest_observation)
    # print(gld.latest_observation.latest_measurement)

    # Pre-fetch related data to reduce database hits
    print("Prefetching GMWs")
    gmw_qs = GroundwaterMonitoringWellStatic.objects.prefetch_related(
        Prefetch(
            "tube__measuring_point",  # Adjust the related field names
            queryset=gmn_models.MeasuringPoint.objects.select_related("gmn"),
        ),
        Prefetch(
            "picture",
            queryset=gmw_models.Picture.objects.only(
                "is_main", "picture", "recording_datetime", "picture_id"
            ).order_by("-is_main", "-recording_datetime", "-picture_id")
        ),
    )

    # print("Prefetching GLDs")
    # gld_qs = gld_models.GroundwaterLevelDossier.objects.prefetch_related(
    #     Prefetch(
    #         "most_recent_measurement",
    #     ),
    # )

    ## Prefetch measurementtvps and their observations
    # mtvp_qs = gld_models.MeasurementTvp.objects.prefetch_related(
    #     Prefetch(
    #         "measurement"
    #     ),
    #     queryset=gld_models.Observation.objects.order_by("-observation_starttime")
    # )

    # mtvp_qs = gld_models.Observation.objects.prefetch_related(
    #     Prefetch("measurement"),
    #     queryset=gld_models.Observation. ## measurment is the relation of the observationthat are connected to mtvps
    # )
    # obs_dates = [
    #     mtvp.observation.observation_starttime for mtvp in gld_models.MeasurementTvp.objects.all()
    # ]


    # Per locatie per filter

    # Check GLD voor 

    # Observatie controle last timestamp

    # Observatie regulier last timestamp



    ## When loading the last mtvp, doesnt matter if you base it on gld or obs, takes 9s
    ## Insane amount of mtvps is the slowing factor
    ## Need a quick and efficient way to get the first mtvp for every obs or the ones I specify

    print("wells: ")
    start = time.time()
    wells = serializers.GMWSerializer(gmw_qs, many=True).data
    end = time.time()
    print(f"finished in {end-start}s")
    
    # ## use observation serializer
    # ## find the most recent measurementtvp
    # ## 
    # print("serializing obs")
    # obs_ids = set()
    # for well in wells:
    #     ids = well.get("obs", None)
    #     if ids:
    #         for obs in ids:
    #             obs_ids.add(obs)
    # obs_qs = gld_models.Observation.objects.filter(observation_id__in=[list(obs_ids)[0]])
    # print(f"{len(obs_qs)} obs")
    # start = time.time()
    # obs = serializers.ObservationSerializer(obs_qs, many=True).data
    # end = time.time()
    # print(f"finished in {end-start}s")
    # stop

    # print("serializing glds")
    # gld_ids = set()
    # for well in wells:
    #     ids = well.get("glds", None)
    #     if ids:
    #         for gld in ids:
    #             gld_ids.add(gld)
    # gld_qs = GroundwaterLevelDossier.objects.filter(groundwater_level_dossier_id__in=[list(gld_ids)[0]])
    # print(f"{len(gld_qs)} glds")
    # start = time.time()
    # glds = serializers.GLDSerializer(gld_qs, many=True).data
    # end = time.time()
    # print(f"finished in {end-start}s")

    # Get unique party IDs and related organisations in one query
    party_ids = GroundwaterMonitoringWellStatic.objects.values_list(
        "delivery_accountable_party", flat=True
    ).distinct()
    instantie_qs = Organisation.objects.filter(id__in=party_ids)
    instanties = bro_serializers.OrganisationSerializer(instantie_qs, many=True).data

    # Use a set for unique GMNs
    gmns = {gmn for well in wells for gmn in well.get("linked_gmns", [])}

    context = {
        "wells": wells,
        "glds": glds,
        "gmns": list(gmns),  # Convert set to list
        "organisations": instanties,
        "map_center": map_center
    }
    # context = {}

    response = render(request, "map.html", context)

    cache.set(cache_key, context, timeout=3600)

    return response

def gmw_map_validation_status_context(request):
    # cache.clear()
    cache_key = get_cache_key(request)
    cache_key_content = cache_key + "ids/"    
    cached_context = cache.get(cache_key, {})
    cached_content = cache.get(cache_key_content, {})

    content = {
        "ids": [],
        "lon": None,
        "lat": None,
        "zoom": None,
    }
        
    if cached_context:
        if cached_content:
            content["ids"] = cached_content.get("ids", [])
            content["lon"] = cached_content.get("lon")
            content["lat"] = cached_content.get("lat")
            content["zoom"] = cached_content.get("zoom")

        context = cached_context
        context["content"] = content
        context["wells"] = [
            well for well in cached_context.get("wells", [])
            if well.get("groundwater_monitoring_well_static_id") in content["ids"]
        ]

        response = render(request, "map_validation_status.html", context)

        return response

    ## Ideally, load the latest_measurement for controle and reguliere metingen
    ## Make sure that we filter for one of the other, or empty
    ## For regular, store the status. Make sure that we can filter for volledigBeoordeeld, voorlopig, onbekend (for controle this is not used)
    ## The popup box should only show what is checked. The dot should ideally update when checking on of these boxes

    gld_qs = get_glds_with_latest_data_fast()
    print("glds: ")
    start = time.time()
    glds = serializers.GLDSerializer(gld_qs, many=True).data
    end = time.time()
    print(f"finished in {end-start}s")

    # find a way to read the request and only load the wells that are shown in the main map

    print("Prefetching GMWs")
    gmw_qs = GroundwaterMonitoringWellStatic.objects.prefetch_related(
        Prefetch(
            "tube__measuring_point",  # Adjust the related field names
            queryset=gmn_models.MeasuringPoint.objects.select_related("gmn"),
        ),
        Prefetch(
            "picture",
            queryset=gmw_models.Picture.objects.only(
                "is_main", "picture", "recording_datetime", "picture_id"
            ).order_by("-is_main", "-recording_datetime", "-picture_id")
        ),
    )
    # Serialize GroundwaterMonitoringWellStatic with only required fields
    wells = serializers.GMWSerializer(gmw_qs, many=True).data

    # print("getting gld ids")
    # gld_ids = set()
    # for well in wells:
    #     ids = well.get("glds", None)
    #     if ids:
    #         for gld in ids:
    #             gld_ids.add(gld)

    # gld_qs = GroundwaterLevelDossier.objects.filter(groundwater_level_dossier_id__in=gld_ids)
    
    # print("serializing glds")
    # glds = serializers.GLDSerializer(gld_qs, many=True).data

    print("finished")
    context = {
        "wells": wells,
        "glds": glds,
        "content": content
    }

    response = render(request, "map_validation_status.html", context)

    cache.set(cache_key, context, timeout=3600)

    return response


def gmw_map_detail_context(request):
    # Pre-fetch related data to reduce database hits
    id = request.GET.get("id", None)
    if id is None:
        gmw_qs = GroundwaterMonitoringWellStatic.objects.prefetch_related(
            Prefetch(
                "tube__measuring_point",  # Adjust the related field names
                queryset=gmn_models.MeasuringPoint.objects.select_related("gmn"),
            )
        )
    else:
        gmw_qs = GroundwaterMonitoringWellStatic.objects.filter(
            groundwater_monitoring_well_static_id=id
        ).prefetch_related(
            Prefetch(
                "tube__measuring_point",  # Adjust the related field names
                queryset=gmn_models.MeasuringPoint.objects.select_related("gmn"),
            )
        )

    # Serialize GroundwaterMonitoringWellStatic with only required fields
    wells = serializers.GMWSerializer(gmw_qs, many=True).data
    context = {
        "wells": wells,
    }
    return render(request, "detail_map.html", context)
