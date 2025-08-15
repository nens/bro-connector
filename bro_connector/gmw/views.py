# Create your views here.
from django.db.models import Prefetch
from django.shortcuts import render
from gmw.models import (
    GroundwaterMonitoringWellStatic,
)
from bro.models import Organisation
import gmn.models as gmn_models
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

def gmw_map_context(request):
    # Pre-fetch related data to reduce database hits
    map_center = get_map_center(settings)

    gmw_qs = GroundwaterMonitoringWellStatic.objects.prefetch_related(
        Prefetch(
            "tube__measuring_point",  # Adjust the related field names
            queryset=gmn_models.MeasuringPoint.objects.select_related("gmn"),
        )
    )

    # Serialize GroundwaterMonitoringWellStatic with only required fields
    wells = serializers.GMWSerializer(gmw_qs, many=True).data

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
        "gmns": list(gmns),  # Convert set to list
        "organisations": instanties,
        "groundwater_level_dossiers": {},
        "map_center": map_center,
    }
    print(context)
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
