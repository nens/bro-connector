# Create your views here.
from django.shortcuts import render
from gmw.models import GroundwaterMonitoringWellStatic
from pyproj import Transformer


def gmw_map_context(request):
    well_instances = list(GroundwaterMonitoringWellStatic.objects.all())
    wells = []

    transformer = Transformer.from_crs(crs_from="EPSG:28992", crs_to="EPSG:4326")

    for well in well_instances:
        (x, y) = transformer.transform(well.coordinates.x, well.coordinates.y)
        wells.append(
            {
                "object_id": well.groundwater_monitoring_well_static_id,
                "bro_id": well.bro_id,
                "latitude": x,
                "longitude": y,
                "quality_regime": well.quality_regime,
                "accountable_party": well.delivery_accountable_party,
            }
        )

    context = {"wells": wells}
    return render(request, "gmw/gmw_map.html", context)
