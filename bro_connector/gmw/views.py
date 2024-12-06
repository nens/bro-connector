# Create your views here.
import time
from django.db.models import Prefetch
from django.shortcuts import render
from gld.models import (
    GroundwaterLevelDossier,
)
from gmw.models import (
    GroundwaterMonitoringWellStatic,
)
from bro.models import Organisation
import gmn.models as gmn_models
from . import serializers
import bro.serializers as bro_serializers


def gmw_map_context(request):
    start_time = time.time()

    # Pre-fetch related data to reduce database hits
    gmw_qs = GroundwaterMonitoringWellStatic.objects.prefetch_related(
        Prefetch(
            'tube__measuringpoint_set',  # Adjust the related field names
            queryset=gmn_models.MeasuringPoint.objects.select_related('gmn')
        )
    )


    # Serialize GroundwaterMonitoringWellStatic with only required fields
    wells = serializers.GMWSerializer(gmw_qs, many=True).data

    # Get unique party IDs and related organisations in one query
    party_ids = GroundwaterMonitoringWellStatic.objects.values_list('delivery_accountable_party', flat=True).distinct()
    instantie_qs = Organisation.objects.filter(id__in=party_ids)
    instanties = bro_serializers.OrganisationSerializer(instantie_qs, many=True).data

    # Serialize GroundwaterLevelDossier
    glds = serializers.GLDSerializer(GroundwaterLevelDossier.objects.all(), many=True).data

    # Use a set for unique GMNs
    gmns = {gmn for well in wells for gmn in well.get('linked_gmns', [])}

    context = {
        "wells": wells,
        "gmns": list(gmns),  # Convert set to list
        "organisations": instanties,
        "groundwater_level_dossiers": glds,
    }

    print(wells[0])

    end_time = time.time()
    print(f"Time taken: {end_time - start_time:.2f}s")
    return render(request, "map.html", context)