# Create your views here.
from django.shortcuts import render
from gld.models import (
    GroundwaterLevelDossier,
)
from gmw.models import (
    GroundwaterMonitoringWellStatic,
    Instantie,
)
from main import localsecret as ls
from . import serializers


def gmw_map_context(request):
    gmw_qs = GroundwaterMonitoringWellStatic.objects.all()
    gmw_serializer = serializers.GMWSerializer(gmw_qs, many=True)
    wells = gmw_serializer.data

    print(wells[0])

    instantie_qs = Instantie.objects.all()
    instantie_serializer = serializers.InstantieSerializer(instantie_qs, many=True)
    instanties = instantie_serializer.data

    gld_qs = GroundwaterLevelDossier.objects.all()
    gld_serializer = serializers.GLDSerializer(gld_qs, many=True)
    glds = gld_serializer.data

    context = {
        "wells": wells,
        "organisations": instanties,
        "groundwater_level_dossiers": glds,
        "maptiler_key": ls.maptiler_key,
    }
    return render(request, "map.html", context)