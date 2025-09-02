# Create your views here.
from django.views.decorators.cache import cache_page
import json
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache

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
from gmw.utils import compute_map_view
import bro.serializers as bro_serializers
from django.conf import settings
import time

@csrf_exempt
def gmw_map_state(request):
    if request.method == "POST":
        try:
            state = json.loads(request.body)  
            cache_key = get_cache_key(request)
            cache.set(cache_key, state, timeout=settings.CACHE_TIMEOUT)

            ids = []
            if state:
                ids = state.get("ids", [])
            return JsonResponse({"status": "ok", "count": len(ids)})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)

def get_map_settings(settings):
    wells = GroundwaterMonitoringWellStatic.objects.all()

    if settings.USE_WELLS_AS_MAP_CENTER and wells:
        map_settings = compute_map_view(wells)
        print(map_settings)
    else:
        map_settings = {
            "lon": settings.MAP_CENTER[0],
            "lat": settings.MAP_CENTER[1], 
            "zoom": settings.MAP_ZOOM,
        }

    return map_settings

def get_cache_key(request: HttpRequest):
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

from django.db.models import Max

def get_glds_with_latest_data_fast():
    # 1️⃣ Fetch all GLDs
    glds = list(gld_models.GroundwaterLevelDossier.objects.all())

    # 2️⃣ Fetch all observations for these GLDs (with metadata prefetch for efficiency)
    observations = list(
        gld_models.Observation.objects.select_related("observation_metadata").filter(
            groundwater_level_dossier__in=glds,
            observation_starttime__isnull=False
        )
    )
    obs_map = {obs.pk: obs for obs in observations}
    # print(obs_map[4304])
    # for o,v in obs_map.items():
    #     if o == 4304:
    #         print(v)

    # 3️⃣ Aggregate latest measurement_time per observation
    latest_meas_per_obs = (
        gld_models.MeasurementTvp.objects
        .filter(
            observation_id__in=obs_map.keys(),
            measurement_time__isnull=False
        )
        .values('observation_id')
        .annotate(latest_time=Max('measurement_time'))
    )
    obs_latest_time_map = {row['observation_id']: row['latest_time'] for row in latest_meas_per_obs}
    # print(obs_latest_time_map[4304])
    # for o,v in obs_latest_time_map.items():
    #     if o == 4304:
    #         print(v)

    # 4️⃣ Fetch actual MeasurementTvp rows in bulk
    latest_measurements = gld_models.MeasurementTvp.objects.filter(
        observation_id__in=obs_latest_time_map.keys(),
        measurement_time__in=obs_latest_time_map.values()
    ).order_by("observation_id", "-measurement_time")

    meas_map = {}
    for m in latest_measurements:
        if m.observation_id not in meas_map:
            meas_map[m.observation_id] = m
    # print(meas_map[4304])

    # 5️⃣ Attach latest measurement to each observation
    for obs in observations:
        obs.latest_measurement = meas_map.get(obs.pk)

    # 6️⃣ Determine latest measurement per GLD + observation_type
    gld_type_meas_map = {}
    gld_type_obs_map = {}
    for obs in observations:
        gld_id = obs.groundwater_level_dossier.groundwater_level_dossier_id
        obs_type = getattr(obs.observation_metadata, "observation_type", None)
        meas = obs.latest_measurement
        # if obs.observation_id == 4304:
        #     print(meas)
        #     stop
        if meas:
            key = (gld_id, obs_type)
            current = gld_type_meas_map.get(key)
            if not current or meas.measurement_time > current.measurement_time:
                gld_type_meas_map[key] = meas
                gld_type_obs_map[key] = obs

    # 7️⃣ Attach per-type latest measurement/observation to GLDs
    for gld in glds:
        # initialize
        for obs_type in ["regular", "controle"]:
            setattr(gld, f"latest_measurement_{obs_type}", None)
            setattr(gld, f"latest_observation_{obs_type}", None)

        # fill
        for obs_type in ["regular", "controle"]:
            if obs_type == "regular":
                obs_type_value = "reguliereMeting"
            if obs_type == "controle":
                obs_type_value = "controlemeting"
            key = (gld.groundwater_level_dossier_id, obs_type_value)
            if key in gld_type_meas_map:
                setattr(gld, f"latest_measurement_{obs_type}", gld_type_meas_map[key])
                setattr(gld, f"latest_observation_{obs_type}", gld_type_obs_map[key])

    # for key in gld_type_meas_map.keys():
    #     if key[0] == 6972:
    #         print(key[1], gld_type_meas_map[key])


    return glds

# def get_glds_with_latest_data_fast():
#     # 1️⃣ Fetch all GLDs
#     glds = list(gld_models.GroundwaterLevelDossier.objects.all())

#     # 2️⃣ Fetch all observations for these GLDs
#     observations = list(
#         gld_models.Observation.objects.filter(
#             groundwater_level_dossier__in=glds,
#             observation_starttime__isnull=False
#         )
#     )
#     obs_map = {obs.pk: obs for obs in observations}

#     # 3️⃣ Aggregate latest measurement_time per observation
#     latest_meas_per_obs = (
#         gld_models.MeasurementTvp.objects
#         .filter(
#             observation_id__in=obs_map.keys(),
#             measurement_time__isnull=False
#         )
#         .values('observation_id')
#         .annotate(latest_time=Max('measurement_time'))
#     )
#     # Map: observation_id -> latest measurement_time
#     obs_latest_time_map = {row['observation_id']: row['latest_time'] for row in latest_meas_per_obs}

#     # 4️⃣ Fetch actual MeasurementTvp rows in bulk
#     latest_measurements = gld_models.MeasurementTvp.objects.filter(
#         observation_id__in=obs_latest_time_map.keys(),
#         measurement_time__in=obs_latest_time_map.values()
#     )
#     meas_map = {m.observation_id: m for m in latest_measurements}

#     # 5️⃣ Attach latest measurement to each observation
#     for obs in observations:
#         obs.latest_measurement = meas_map.get(obs.pk)

#     # 6️⃣ Determine latest measurement and its observation per GLD
#     gld_meas_map = {}
#     gld_obs_map = {}
#     for obs in observations:
#         gld_id = obs.groundwater_level_dossier_id
#         meas = obs.latest_measurement
#         if meas:
#             current = gld_meas_map.get(gld_id)
#             # Keep the newest measurement across all observations
#             if not current or meas.measurement_time > current.measurement_time:
#                 gld_meas_map[gld_id] = meas
#                 gld_obs_map[gld_id] = obs

#     # 7️⃣ Attach latest measurement to GLDs
#     for gld in glds:
#         gld.latest_measurement = gld_meas_map.get(gld.groundwater_level_dossier_id)
#         gld.latest_observation = gld_obs_map.get(gld.groundwater_level_dossier_id)

#     return glds

def gmw_map_context(request):
    # cache.clear()
    cache_key = get_cache_key(request)
    cache_key_state = cache_key + "state/"    
    cached_context = cache.get(cache_key, {})
    cached_state = cache.get(cache_key_state, {})

    context = {
        "wells": [],
        "glds": [],
        "gmns": [],
        "organisations": [],
        "state": {}
    }
    state = {
        "ids": [],
        "lon": None,
        "lat": None,
        "zoom": None,
        "checkboxes": {},
    }

    if cached_state:   
        state["ids"] = cached_state.get("ids", [])
        state["lon"] = cached_state.get("lon")
        state["lat"] = cached_state.get("lat")
        state["zoom"] = cached_state.get("zoom")
        state["checkboxes"] = cached_state.get("checkboxes", {})

    else:
        map_settings = get_map_settings(settings)
        state["lon"] = map_settings.get("lon")
        state["lat"] = map_settings.get("lat")
        state["zoom"] = map_settings.get("zoom")

    if cached_context:
        context = cached_context
        context["state"] = state
        response = render(request, "map.html", context)
        return response
    
    else:
        ## SERIALIZING GLDS
        start = time.time()
        ## store latest_controle_measurement
        ## store latest_regular_measurement
        ## base the coloring on the time of both measurements if applicable
        ## if both are shown: show the time and color of that type of measurement
        ## 

        gld_qs = get_glds_with_latest_data_fast()
        # print([gld for gld in gld_qs if gld.groundwater_level_dossier_id == 6972])
        # stop
        glds = serializers.GLDSerializer(gld_qs, many=True).data
        end = time.time()
        print(f"finished serializing GLDs in {end-start}s")
    
        ## SERIALIZING GMWS
        start = time.time()
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
        wells = serializers.GMWSerializer(gmw_qs, many=True).data
        end = time.time()
        print(f"finished serializing GMWs in {end-start}s")
        
        ## SERIALIZING ORGS AND GMNS
        start = time.time()
        party_ids = GroundwaterMonitoringWellStatic.objects.values_list(
            "delivery_accountable_party", flat=True
        ).distinct()
        instantie_qs = Organisation.objects.filter(id__in=party_ids)
        instanties = bro_serializers.OrganisationSerializer(instantie_qs, many=True).data
        gmns = list({gmn for well in wells for gmn in well.get("linked_gmns", [])})
        end = time.time()
        print(f"finished serializing Organisations and GMNs in {end-start}s")

        context["wells"] = wells
        context["glds"] = glds
        context["gmns"] = gmns
        context["organisations"] = instanties
        context["state"] = state
        response = render(request, "map.html", context)
        cache.set(cache_key, context, timeout=settings.CACHE_TIMEOUT)

        return response

def gmw_map_validation_status_context(request):
    # cache.clear()
    cache_key = get_cache_key(request)
    cache_key_state = cache_key + "state/"    
    cached_context = cache.get(cache_key, {})
    cached_state = cache.get(cache_key_state, {})

    if not cached_context:
        raise Exception("No cache found of the BRO-Connector map. It might have been deleted manually or due to a timeout. Please reload to main map and then go back to the validation map.")

    context = {
        "wells": [],
        "glds": [],
        "gmns": [],
        "organisations": [],
        "state": {}
    }
    state = {
        "ids": [],
        "lon": None,
        "lat": None,
        "zoom": None,
        "checkboxes": {}
    }

    if cached_state:              
        state["ids"] = cached_state.get("ids", [])
        state["lon"] = cached_state.get("lon")
        state["lat"] = cached_state.get("lat")
        state["zoom"] = cached_state.get("zoom")
        state["checkboxes"] = cached_state.get("checkboxes", {})
        
    else:
        map_settings = get_map_settings(settings)
        state["lon"] = map_settings.get("lon")
        state["lat"] = map_settings.get("lat")
        state["zoom"] = map_settings.get("zoom")

    context = cached_context
    context["state"] = state
    response = render(request, "map_validation_status.html", context)

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
