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
            "zoom": settings.ZOOM,
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

def get_glds_with_latest_data_fast():
    start = time.time()
    print("# Step 1: Find newest measurement per GLD (based on measurement_time)")

    latest_meas_subquery = (
        gld_models.MeasurementTvp.objects
        .filter(
            observation__groundwater_level_dossier=OuterRef("pk"),
            measurement_time__isnull=False,
        )
        .order_by("-measurement_time")
        .values("pk")[:1]
    )

    latest_meas_per_gld = (
        gld_models.GroundwaterLevelDossier.objects
        .annotate(latest_meas_id=Subquery(latest_meas_subquery))
        .values("pk", "latest_meas_id")
    )
    meas_id_map = {
        row["pk"]: row["latest_meas_id"]
        for row in latest_meas_per_gld if row["latest_meas_id"]
    }

    end = time.time()
    print(f"time to run step: {end-start}")

    start = time.time()
    print("# Step 2: Fetch all GLDs in one go")
    glds = list(gld_models.GroundwaterLevelDossier.objects.all())
    end = time.time()
    print(f"time to run step: {end-start}")

    start = time.time()
    print("# Step 3: Fetch all latest measurements in bulk (with observations)")
    measurements = {
        m.pk: m
        for m in gld_models.MeasurementTvp.objects
        .select_related("observation")
        .filter(pk__in=meas_id_map.values())
    }
    end = time.time()
    print(f"time to run step: {end-start}")

    start = time.time()
    print("# Step 4: Attach to objects")
    for gld in glds:
        latest_meas = measurements.get(meas_id_map.get(gld.pk))
        gld.latest_measurement = latest_meas
        gld.latest_observation = latest_meas.observation if latest_meas else None
    end = time.time()
    print(f"time to run step: {end-start}")

    return glds

# def get_glds_with_latest_data_fast():
#     start = time.time()
#     print("# Step 1: Find newest observation per GLD (based on observation_starttime)")
#     latest_obs_subquery = (
#         gld_models.Observation.objects
#         .filter(
#             groundwater_level_dossier=OuterRef('pk'),
#             observation_starttime__isnull=False
#         )
#         .order_by('-observation_starttime')
#         .values('pk')[:1]
#     )
#     latest_obs_per_gld = (
#         gld_models.GroundwaterLevelDossier.objects
#         .annotate(latest_obs_id=Subquery(latest_obs_subquery))
#         .values('pk', 'latest_obs_id')
#     )
#     obs_id_map = {
#         row['pk']: row['latest_obs_id']
#         for row in latest_obs_per_gld if row['latest_obs_id']
#     }

#     start = time.time()
#     print("# Step 2: Fetch all GLDs in one go")
#     glds = list(gld_models.GroundwaterLevelDossier.objects.all())
#     end = time.time()
#     print(f"time to run step: {end-start}")

#     print("# Step 3: Get all latest observations in one go")
#     observations = list(
#         gld_models.Observation.objects.filter(pk__in=obs_id_map.values())
#     )
#     obs_map = {o.pk: o for o in observations}
#     end = time.time()
#     print(f"time to run step: {end-start}")
    
#     start = time.time()
#     print("# Step 4: Find newest measurement per observation (batch query)")
#     # latest_meas_per_obs = (
#     #     gld_models.MeasurementTvp.objects
#     #     .filter(observation_id__in=obs_map.keys())
#     #     .values('observation_id')
#     #     .annotate(latest_meas_id=Max('measurement_tvp_id', filter=Q(measurement_time__isnull=False)))
#     # )
#     latest_meas_subquery = (
#         gld_models.MeasurementTvp.objects
#         .filter(observation=OuterRef("pk"), measurement_time__isnull=False)
#         .order_by("-measurement_time")
#         .values("pk")[:1]
#     )

#     latest_meas_per_obs = (
#         gld_models.Observation.objects
#         .filter(pk__in=obs_map.keys())
#         .annotate(latest_meas_id=Subquery(latest_meas_subquery))
#     )
#     meas_id_map = {
#         o.observation_id: o.latest_meas_id
#         for o in latest_meas_per_obs if o.latest_meas_id
#     }
#     end = time.time()
#     print(f"time to run step: {end-start}")

#     start = time.time()
#     print("# Step 5: Fetch those measurements in bulk")
#     measurements = {
#         m.pk: m
#         for m in gld_models.MeasurementTvp.objects.filter(pk__in=meas_id_map.values())
#     }
#     end = time.time()
#     print(f"time to run step: {end-start}")

#     start = time.time()
#     print("# Step 6: Attach to objects") 
#     for obs in observations:
#         obs.latest_measurement = measurements.get(meas_id_map.get(obs.pk))

#     for gld in glds:
#         gld.latest_observation = obs_map.get(obs_id_map.get(gld.pk))

#     end = time.time()
#     print(f"time to run step: {end-start}")

#     return glds

def gmw_map_context(request):
    cache.clear()
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
        gld_qs = get_glds_with_latest_data_fast()
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
