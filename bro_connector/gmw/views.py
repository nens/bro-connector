# Create your views here.
from django.db.models import Prefetch
from django.shortcuts import render
from gmw.models import (
    GroundwaterMonitoringWellStatic,
)
from bro.models import Organisation
from gld.models import GroundwaterLevelDossier
import gmn.models as gmn_models
from . import serializers
import bro.serializers as bro_serializers


def gmw_map_context(request):
    # Pre-fetch related data to reduce database hits
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
    }
    return render(request, "map.html", context)


def gmw_map_validation_status_context(request):
    print(request)
    # find a way to read the request and only load the wells that are shown in the main map

    # Pre-fetch related data to reduce database hits
    print("Prefetching gmw")
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

    gld_ids = set()
    for well in wells:
        ids = well.get("glds", None)
        if ids:
            for gld in ids:
                gld_ids.add(gld)
    print(gld_ids)

    gld_qs = GroundwaterLevelDossier.objects.filter(groundwater_level_dossier_id__in=gld_ids)
    glds = serializers.GLDSerializer(gld_qs, many=True).data

    context = {
        "wells": wells,
        "groundwater_level_dossiers": glds,
    }

    return render(request, "map_validation_status.html", context)


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
