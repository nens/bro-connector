# Create your views here.
from django.views.decorators.cache import cache_page
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

def get_map_center(settings):
    wells = GroundwaterMonitoringWellStatic.objects.all()

    if settings.USE_WELLS_AS_MAP_CENTER and len(wells) > 0:
        latitudes, longitudes = [w.lat for w in wells], [w.lon for w in wells]
        center_coordinate = {"lat": sum(latitudes) / len(latitudes), "lon": sum(longitudes) / len(longitudes)}

    else:
        center_coordinate = {"lat": settings.MAP_CENTER[1], "lon": settings.MAP_CENTER[0]}

    return center_coordinate

import time

def get_cache_key(request):
    if request.path.startswith("/map/validation"):
        cache_base = "/map"
    else:
        cache_base = request.path

    session_id = request.session.session_key or "anon"
    cache_key = f"map:{session_id}:{cache_base}"

    return cache_key

from django.db.models import Max, Q

def get_glds_with_latest_data_fast():
    print("# Step 1: Find newest observation per GLD (batch query)")
    latest_obs_per_gld = (
        gld_models.Observation.objects
        .values('groundwater_level_dossier')
        .annotate(latest_obs_id=Max('observation_id', filter=Q(observation_starttime__isnull=False)))
    )
    obs_id_map = {
        row['groundwater_level_dossier']: row['latest_obs_id']
        for row in latest_obs_per_gld if row['latest_obs_id']
    }

    print("# Step 2: Fetch all GLDs in one go")
    glds = list(gld_models.GroundwaterLevelDossier.objects.all())

    print("# Step 3: Get all latest observations in one go")
    observations = list(
        gld_models.Observation.objects.filter(pk__in=obs_id_map.values())
    )
    obs_map = {o.pk: o for o in observations}

    print("# Step 4: Find newest measurement per observation (batch query)")
    latest_meas_per_obs = (
        gld_models.MeasurementTvp.objects
        .filter(observation_id__in=obs_map.keys())
        .values('observation_id')
        .annotate(latest_meas_id=Max('measurement_tvp_id', filter=Q(measurement_time__isnull=False)))
    )
    meas_id_map = {
        row['observation_id']: row['latest_meas_id']
        for row in latest_meas_per_obs if row['latest_meas_id']
    }

    print("# Step 5: Fetch those measurements in bulk")
    measurements = {
        m.pk: m
        for m in gld_models.MeasurementTvp.objects.filter(pk__in=meas_id_map.values())
    }

    print("# Step 6: Attach to objects") 
    for obs in observations:
        obs.latest_measurement = measurements.get(meas_id_map.get(obs.pk))

    for gld in glds:
        gld.latest_observation = obs_map.get(obs_id_map.get(gld.pk))

    return glds


def prefetch_lastest_measurements():
    print("# 1️⃣ Subquery for latest observation per GLD")
    latest_obs_subquery = (
        gld_models.Observation.objects
        .filter(groundwater_level_dossier=OuterRef('pk'))
        .order_by('-observation_starttime')
        .values('observation_id')[:1]
    )

    print("# 2️⃣ Add latest_observation_id to each GLD")
    glds_with_latest_obs = (
        gld_models.GroundwaterLevelDossier.objects
        .annotate(latest_observation_id=Subquery(latest_obs_subquery))
    )

    print("# 3️⃣ Get all latest observations in one go")
    latest_observations = list(
        gld_models.Observation.objects.filter(
            pk__in=[g.latest_observation_id for g in glds_with_latest_obs if g.latest_observation_id]
        )
    )

    print("# 4️⃣ Subquery for latest measurement per observation")
    latest_meas_subquery = (
        gld_models.MeasurementTvp.objects
        .filter(observation=OuterRef('pk'))
        .order_by('-measurement_time')
        .values('measurement_tvp_id')[:1]
    )

    print("# 5️⃣ Annotate observations with latest_measurement_id")
    observations_with_latest_meas = (
        gld_models.Observation.objects
        .filter(pk__in=[o.pk for o in latest_observations])
        .annotate(latest_measurement_id=Subquery(latest_meas_subquery))
    )
    print([o.lastest_measurement_id for o in observations_with_latest_meas])

    print("# 6️⃣ Fetch all latest measurements in one go")
    latest_measurements = {
        m.pk: m
        for m in gld_models.MeasurementTvp.objects.filter(
            pk__in=[o.latest_measurement_id for o in observations_with_latest_meas if o.latest_measurement_id]
        )
    }

    print("# 7️⃣ Attach latest_measurement to each observation")
    observations_by_id = {}
    for obs in observations_with_latest_meas:
        obs.latest_measurement = latest_measurements.get(obs.latest_measurement_id)
        observations_by_id[obs.pk] = obs

    print("# 8️⃣ Attach latest_observation to each GLD")
    for gld in glds_with_latest_obs:
        gld.latest_observation = observations_by_id.get(gld.latest_observation_id)

    return glds_with_latest_obs



def serialize_map(request):
    ## Prefetch gmws
    ## Prefetch observations
    ## Prefetch measurement tvps
    ## Prefetch observation types
    ## Prefetch organisations
    return

def gmw_map_context(request):
    cache.clear()
    cache_key = get_cache_key(request)
    response = cache.get(cache_key)
    if response:
        print("already cached")
        return response
    
    gld_qs = get_glds_with_latest_data_fast()
    for gld in gld_qs:
        obs = gld.latest_observation
        meas = obs.latest_measurement if obs else None
        print(gld.pk, obs, meas)
        if not meas == None:
            stop

    # Pre-fetch related data to reduce database hits
    # print("Prefetching GMWs")
    # gmw_qs = GroundwaterMonitoringWellStatic.objects.prefetch_related(
    #     Prefetch(
    #         "tube__measuring_point",  # Adjust the related field names
    #         queryset=gmn_models.MeasuringPoint.objects.select_related("gmn"),
    #     ),
    #     Prefetch(
    #         "picture",
    #         queryset=gmw_models.Picture.objects.only(
    #             "is_main", "picture", "recording_datetime", "picture_id"
    #         ).order_by("-is_main", "-recording_datetime", "-picture_id")
    #     ),
    # )

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

    # print("wells: ")
    # start = time.time()
    # wells = serializers.GMWSerializer(gmw_qs, many=True).data
    # end = time.time()
    # print(f"finished in {end-start}s")
    
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

    # # Get unique party IDs and related organisations in one query
    # party_ids = GroundwaterMonitoringWellStatic.objects.values_list(
    #     "delivery_accountable_party", flat=True
    # ).distinct()
    # instantie_qs = Organisation.objects.filter(id__in=party_ids)
    # instanties = bro_serializers.OrganisationSerializer(instantie_qs, many=True).data

    # # Use a set for unique GMNs
    # gmns = {gmn for well in wells for gmn in well.get("linked_gmns", [])}

    # context = {
    #     "wells": wells,
    #     "gmns": list(gmns),  # Convert set to list
    #     "organisations": instanties,
    # }
    context = {}

    response = render(request, "map.html", context)

    cache.set(cache_key, response, timeout=3600)

    return response

def gmw_map_validation_status_context(request):
    cache.clear()
    cache_key = get_cache_key(request)
    cache.clear()
    response = cache.get(cache_key)
    if response:
        print("already cached")
        return response

    # find a way to read the request and only load the wells that are shown in the main map

    # Pre-fetch related data to reduce database hits
    gmw_qs = GroundwaterMonitoringWellStatic.objects.prefetch_related(
        Prefetch(
            "tube__measuring_point",  # Adjust the related field names
            queryset=gmn_models.MeasuringPoint.objects.select_related("gmn"),
        )
    )
    print(gmw_qs[0])
    print(gmw_qs[0].quality_regime)
    print("Serializing wells")
    # Serialize GroundwaterMonitoringWellStatic with only required fields
    wells = serializers.GMWSerializer(gmw_qs, many=True).data

    print("getting gld ids")
    gld_ids = set()
    for well in wells:
        ids = well.get("glds", None)
        if ids:
            for gld in ids:
                gld_ids.add(gld)

    gld_qs = GroundwaterLevelDossier.objects.filter(groundwater_level_dossier_id__in=gld_ids)
    
    print("serializing glds")
    glds = serializers.GLDSerializer(gld_qs, many=True).data

    print("finished")
    context = {
        "wells": wells,
        "gmns": list(gmns),  # Convert set to list
        "organisations": instanties,
    }
    return render(request, "map.html", context)


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
