from django.conf import settings
from django.core.management.base import BaseCommand

from shapely.geometry import Point
from shapely.ops import unary_union
import geopandas as gpd

from gmw.models import GroundwaterMonitoringWellStatic


class Command(BaseCommand):
    def handle(self, *args, **options):
        if hasattr(settings, "POLYGON_SHAPEFILE"):
            print(settings.POLYGON_SHAPEFILE)
            gdb: gpd.GeoDataFrame = gpd.read_file(settings.POLYGON_SHAPEFILE)

            wells = GroundwaterMonitoringWellStatic.objects.filter(coordinates__isnull=False).all()
            for well in wells:
                print(well)
                point = Point(well.coordinates.x, well.coordinates.y)
                is_within  = gdb.contains(point).item()
                
                if not is_within:
                    well.delete()

            
