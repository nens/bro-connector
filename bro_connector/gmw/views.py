# Create your views here.
from django.shortcuts import render
from gld.models import (
    GroundwaterLevelDossier,
)
from gmw.models import (
    GroundwaterMonitoringWellStatic,
)
from bro.models import Company
from main import localsecret as ls
from . import serializers
import bro.serializers as bro_serializers



def gmw_map_context(request):
    gmw_qs = GroundwaterMonitoringWellStatic.objects.all()
    gmw_serializer = serializers.GMWSerializer(gmw_qs, many=True)
    wells = gmw_serializer.data

    print(wells[0])

    instantie_qs = Company.objects.all()
    instantie_serializer = bro_serializers.CompanySerializer(instantie_qs, many=True)
    instanties = instantie_serializer.data

    gld_qs = GroundwaterLevelDossier.objects.all()
    gld_serializer = serializers.GLDSerializer(gld_qs, many=True)
    glds = gld_serializer.data

    # Get all the gmns from the wells
    gmns = []
    for index in range(len(wells)):
        linked_gmns = wells[index]["linked_gmns"]
        for index in range(len(linked_gmns)):
            linked_gmn = linked_gmns[index]
            if linked_gmn not in gmns:
                gmns.append(linked_gmn)

    context = {
        "wells": wells,
        "gmns": gmns,
        "organisations": instanties,
        "groundwater_level_dossiers": glds,
        "maptiler_key": ls.maptiler_key,
    }
    return render(request, "map.html", context)
