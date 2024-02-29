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

import django.db.models as models
from django.contrib.gis.db import models as geo_models


from pyproj import Transformer


def model_to_dict(instance):
    """
    Convert a Django model instance to a dictionary
    """
    fields = instance._meta.get_fields()
    field_dict = {}
    for field in fields:
        field_name = field.name

        if isinstance(field, (models.ManyToOneRel, models.ManyToManyRel)):
            continue

        field_value = getattr(instance, field_name)

        if isinstance(field, geo_models.PointField) and field_value is not None:
            transformer = Transformer.from_crs(
                crs_from="EPSG:28992", crs_to="EPSG:4326"
            )
            (x, y) = transformer.transform(field_value.x, field_value.y)
            field_dict["x"] = x
            field_dict["y"] = y
            continue

        if isinstance(field, models.ForeignKey) and field_value is not None:
            field_dict[field_name] = field_value.pk
            continue

        field_dict[field_name] = field_value

    return field_dict


def gmw_map_context(request):
    well_instances = list(GroundwaterMonitoringWellStatic.objects.all())
    organisation_instances = list(Instantie.objects.all())
    gld_instances = list(GroundwaterLevelDossier.objects.all())
    organisations = []
    wells = []
    glds = []

    for well in well_instances:
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

            filters.append(model_to_dict(filter))

        wells.append(model_to_dict(well))

    for gld in gld_instances:
        observations = Observation.objects.filter(groundwater_level_dossier=gld)

        glds.append(model_to_dict(gld))

    for organisation in organisation_instances:
        organisations.append(model_to_dict(organisation))

    context = {
        "wells": wells,
        "organisations": organisations,
        "groundwater_level_dossiers": glds,
    }
    print(context["wells"][0:2])
    print(context["organisations"][0:2])
    print(context["groundwater_level_dossiers"][0:2])
    return render(request, "gmw/gmw_map.html", context)
