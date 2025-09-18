import math


def generate_put_code(nitg_code: str) -> None | str:
    if not nitg_code.startswith("B"):
        return None

    # Remove B
    nitg_code = nitg_code[1:]

    # Split into 3 sections:
    if len(nitg_code) != 7:
        return None

    initial_code, char, second_code = nitg_code[0:2], nitg_code[2], nitg_code[3:]

    if not initial_code.isdigit():
        return None

    if not second_code.isdigit():
        return None

    if char.isdigit():
        return None

    return f"GMW{initial_code}{char}00{second_code}"


def compute_map_view(
    wells, map_width_px=800, map_height_px=600, tile_size=256, max_zoom=19
):
    """
    Compute center and zoom for fitting given coordinates on a Mapbox/Leaflet map.

    Args:
        wells (sequence of GMW.GroundmonitoringWellStatic).
        map_width_px (int): Width of map viewport in pixels.
        map_height_px (int): Height of map viewport in pixels.
        tile_size (int): Tile size (default 256 for Web Mercator).
        max_zoom (int): Maximum zoom level allowed.

    Returns:
        dict: { "center": [lon, lat], "zoom": zoom_level }
    """
    if not wells:
        raise ValueError("Well list is empty")

    lons = [well.lon for well in wells]
    lats = [well.lat for well in wells]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)

    # Center = midpoint of bounding box
    center_lon = (min_lon + max_lon) / 2
    center_lat = (min_lat + max_lat) / 2

    # Convert latitude to Web Mercator Y
    def lat_to_mercator(lat):
        lat_rad = math.radians(lat)
        return math.log(math.tan(lat_rad / 2 + math.pi / 4))

    min_y = lat_to_mercator(min_lat)
    max_y = lat_to_mercator(max_lat)

    def norm_x(lon):
        return (lon + 180.0) / 360.0

    def norm_y(merc_y):
        return (1 - merc_y / math.pi) / 2

    min_nx, max_nx = norm_x(min_lon), norm_x(max_lon)
    min_ny, max_ny = norm_y(max_y), norm_y(min_y)

    bbox_width = abs(max_nx - min_nx)
    bbox_height = abs(max_ny - min_ny)

    if bbox_width == 0 and bbox_height == 0:
        return {
            "lon": center_lon,
            "lat": center_lat,
            "zoom": max_zoom,
        }

    zoom_x = math.floor(math.log2(map_width_px / (bbox_width * tile_size)))
    zoom_y = math.floor(math.log2(map_height_px / (bbox_height * tile_size)))
    zoom = min(zoom_x, zoom_y, max_zoom)

    return {"lon": center_lon, "lat": center_lat, "zoom": max(0, zoom)}
