import geopandas as gpd

class BBOX_EXTRACTOR:
    def __init__(self,shp,use_bbox):
        self.bbox = self.BBOX(shp)
        self.bbox_settings = self.get_bbox_settings(use_bbox)
    
    class BBOX:
        def __init__(self,shp):
            gdf = gpd.read_file(shp)
            crs_bro = "EPSG:4326"
            crs_shp = gdf.crs.to_string()
            if crs_shp != crs_bro:
                gdf = gdf.to_crs(crs_bro)
            bbox = gdf.total_bounds.tolist()

            self.xmin = bbox[0]
            self.ymin = bbox[1]
            self.xmax = bbox[2]
            self.ymax = bbox[3]
       
    def get_bbox_settings(self,use_bbox):
        return {
            "use_bbox": use_bbox,
            "xmin": self.bbox.xmin,
            "xmax": self.bbox.xmax,
            "ymin": self.bbox.ymin,
            "ymax": self.bbox.ymax,
        }