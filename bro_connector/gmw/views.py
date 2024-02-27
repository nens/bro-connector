# Create your views here.
from django.shortcuts import render
from gmn.models import MeasuringPoint
from gld.models import (
    GroundwaterLevelDossier,
    Observation,
)
from gmw.models import (
    GroundwaterMonitoringWellStatic,
    Instantie,
    GroundwaterMonitoringTubeStatic,
)

from pyproj import Transformer


def gmw_map_context(request):
    well_instances = list(GroundwaterMonitoringWellStatic.objects.all())
    organisation_instances = list(Instantie.objects.all())
    gld_instances = list(GroundwaterLevelDossier.objects.all())
    organisations = []
    wells = []
    glds = []

    transformer = Transformer.from_crs(crs_from="EPSG:28992", crs_to="EPSG:4326")

    for well in well_instances:
        (x, y) = transformer.transform(well.coordinates.x, well.coordinates.y)

        filter_instances = GroundwaterMonitoringTubeStatic.objects.filter(
            groundwater_monitoring_well_static=well
        )
        filters = []

        for filter in filter_instances:
            measuring_point = MeasuringPoint.objects.filter(
                groundwater_monitoring_tube=filter
            ).first()

            meetnet = None
            if measuring_point:
                meetnet = measuring_point.gmn

            filters.append(
                {
                    "number": filter.tube_number,
                    "type": filter.tube_type,
                }
            )

        wells.append(
            {
                "object_id": well.groundwater_monitoring_well_static_id,
                "bro_id": well.bro_id,
                "latitude": x,
                "longitude": y,
                "quality_regime": well.quality_regime,
                "BRO-compleet": well.complete_bro,
                "BRO-obligatory": well.deliver_gmw_to_bro,
                "filters": filters,
                "organisation_id": well.delivery_accountable_party.id,
            }
        )

    for gld in gld_instances:
        observations = Observation.objects.filter(groundwater_level_dossier=gld)

        glds.append(
            {
                "gmw_bro_id": gld.gmw_bro_id,
                "research_start_date": gld.research_start_date,
                "research_end_date": gld.research_last_date,
                "observations": len(observations),
            }
        )

    for organisation in organisation_instances:
        organisations.append(
            {
                "organisation_id": organisation.id,
                "organisation_name": organisation.name,
                "organisation_color": organisation.color,
            }
        )

    context = {
        "wells": wells,
        "organisations": organisations,
        "groundwater_level_dossiers": glds,
    }
    return render(request, "gmw/gmw_map.html", context)
