from django.shortcuts import render
from gmw.models import GroundwaterMonitoringWellStatic


def gmw_map_context(request):
    wells = list(GroundwaterMonitoringWellStatic.objects.values("coordinates"))
    print(wells)
    context = {}
    return render(request, "gmw_map.html", context)
