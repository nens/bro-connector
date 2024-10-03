import i18n
import numpy as np
import plotly.graph_objs as go
from dash import dcc

from gwdatalens.app.settings import MAPBOX_ACCESS_TOKEN, settings
from gwdatalens.app.src.cache import TIMEOUT, cache
from gwdatalens.app.src.components import ids
from gwdatalens.app.src.data import DataInterface
from gwdatalens.app.src.utils import conditional_cache

try:
    mapbox_access_token = open(MAPBOX_ACCESS_TOKEN, "r").read()
except FileNotFoundError:
    mapbox_access_token = None


@conditional_cache(
    cache.memoize,
    (not settings["DJANGO_APP"] and settings["CACHING"]),
    timeout=TIMEOUT,
)
def render(
    data: DataInterface,
    selected_data=None,
):
    df = data.db.gmw_gdf.reset_index()
    return dcc.Graph(
        id=ids.OVERVIEW_MAP,
        figure=draw_map(
            df,
            mapbox_access_token,
            selected_data=selected_data,
        ),
        style={
            "margin-top": "15",
            "height": "45vh",
        },
        config={
            "displayModeBar": True,
            "displaylogo": False,
            "scrollZoom": True,
            "modeBarButtonsToAdd": ["zoom", "zoom2d"],
        },
    )


def draw_map(
    df,
    mapbox_access_token=MAPBOX_ACCESS_TOKEN,
    selected_data=None,
):
    """Draw ScatterMapBox.

    Parameters
    ----------
    df : pandas.DataFrame
        data to plot
    mapbox_access_token : str
        mapbox access token, see Readme for more information

    Returns
    -------
    dict
        dictionary containing plotly maplayout and mapdata
    """
    mask = df["metingen"] > 0

    if selected_data is not None:
        pts_data = np.nonzero(df.loc[mask, "name"].isin(selected_data))[0].tolist()
        # pts_nodata = np.nonzero(df.loc[~mask, "name"].isin(selected_data))[0].tolist()
    else:
        pts_data = None
        # pts_nodata = None

    # NOTE: this does not work as map and table have to be similarly ordered for
    # synchronized selection to work.
    # df = df.sort_values(["nitg_code", "tube_number"], ascending=[False, False])

    # oseries data for map
    pb_data = {
        "lat": df.loc[mask, "lat"],
        "lon": df.loc[mask, "lon"],
        "name": "PMG Kwantiteit",
        # customdata=df.loc[mask, "z"],
        "type": "scattermapbox",
        "text": df.loc[mask, "name"].tolist(),
        "textposition": "top center" if mapbox_access_token else None,
        "textfont": {"size": 12, "color": "black"} if mapbox_access_token else None,
        "mode": "markers" if mapbox_access_token else "markers",
        "marker": go.scattermapbox.Marker(
            size=6,
            # sizeref=0.5,
            # sizemin=2,
            # sizemode="area",
            opacity=0.7,
            color="black",
            # colorscale=px.colors.sequential.Reds,
            # reversescale=False,
            # showscale=True,
            # colorbar={
            #     "title": "depth<br>(m NAP)",
            #     "x": -0.1,
            #     "y": 0.95,
            #     "len": 0.95,
            #     "yanchor": "top",
            # },
        ),
        "hovertemplate": (
            "<b>%{text}</b><br>"
            # + "<b>z:</b> NAP%{marker.color:.2f} m"
            # + "<extra></extra> "
        ),
        "showlegend": True,
        "legendgroup": "DATA",
        "selectedpoints": pts_data,
        "unselected": {"marker": {"opacity": 0.5, "color": "black", "size": 6}},
        "selected": {"marker": {"opacity": 1.0, "color": "red", "size": 9}},
    }

    pb_nodata = {
        "lat": df.loc[~mask, "lat"],
        "lon": df.loc[~mask, "lon"],
        "name": i18n.t("general.no_data"),
        # customdata=df.loc[~mask, "z"],
        "type": "scattermapbox",
        "text": df.loc[~mask, "name"].tolist(),
        "textposition": "top center" if mapbox_access_token else None,
        "textfont": {"size": 12, "color": "black"} if mapbox_access_token else None,
        "mode": "markers" if mapbox_access_token else "markers",
        "marker": go.scattermapbox.Marker(
            symbol="circle",
            size=5,
            opacity=0.8,
            # sizeref=0.5,
            # sizemin=2,
            # sizemode="area",
            color="grey",
            # colorscale=px.colors.sequential.Reds,
            # reversescale=False,
            # showscale=True,
            # colorbar={
            #     "title": "depth<br>(m NAP)",
            #     "x": -0.1,
            #     "y": 0.95,
            #     "len": 0.95,
            #     "yanchor": "top",
            # },
        ),
        "hovertemplate": (
            "<b>%{text}</b><br>"
            # + "<b>z:</b> NAP%{marker.color:.2f} m"
            # + "<extra></extra> "
        ),
        "showlegend": True,
        "legendgroup": "NODATA",
        # selectedpoints=pts_nodata,
        "unselected": {"marker": {"opacity": 0.5, "color": "grey", "size": 5}},
        "selected": {"marker": {"opacity": 1.0, "color": "red", "size": 9}},
    }

    # if selected_rows is None:
    zoom, center = get_plotting_zoom_level_and_center_coordinates(
        df.lon.values, df.lat.values
    )

    mapdata = [pb_nodata, pb_data]

    maplayout = {
        # top, bottom, left and right margins
        "margin": {"t": 0, "b": 0, "l": 0, "r": 0},
        "font": {"color": "#000000", "size": 11},
        "paper_bgcolor": "white",
        "clickmode": "event+select",
        "mapbox": {
            # here you need the token from Mapbox
            "accesstoken": mapbox_access_token,
            "bearing": 0,
            # where we want the map to be centered
            "center": center,
            # we want the map to be "parallel" to our screen, with no angle
            "pitch": 0,
            # default level of zoom
            "zoom": zoom,
            # default map style (some options listed, not all support labels)
            "style": "outdoors" if mapbox_access_token else "open-street-map",
            # public styles
            # style="carto-positron",
            # style="open-street-map",
            # style="stamen-terrain",
            # mapbox only styles (requires access token):
            # style="basic",
            # style="streets",
            # style="light",
            # style="dark",
            # style="satellite",
            # style="satellite-streets"
        },
        # relayoutData=mapbox_cfg,
        "legend": {"x": 0.01, "y": 0.99, "xanchor": "left", "yanchor": "top"},
        "uirevision": False,
        "modebar": {
            "bgcolor": "rgba(255,255,255,0.9)",
        },
    }

    return {"data": mapdata, "layout": maplayout}


def get_plotting_zoom_level_and_center_coordinates(longitudes=None, latitudes=None):
    """Get zoom level and center coordinate for ScatterMapbox.

    Basic framework adopted from Krichardson under the following thread:
    https://community.plotly.com/t/dynamic-zoom-for-mapbox/32658/7
    Returns the appropriate zoom-level for these plotly-mapbox-graphics along with
    the center coordinate tuple of all provided coordinate tuples.

    Parameters
    ----------
    longitudes : array, optional
        longitudes
    latitudes : array, optional
        latitudes

    Returns
    -------
    zoom : float
        zoom level
    dict
        dictionary containing lat/lon coordinates of center point.
    """
    # Check whether both latitudes and longitudes have been passed,
    # or if the list lenghts don't match
    if (latitudes is None or longitudes is None) or (len(latitudes) != len(longitudes)):
        # Otherwise, return the default values of 0 zoom and the coordinate
        # origin as center point
        return 0, (0, 0)

    # Get the boundary-box
    b_box = {}
    b_box["height"] = latitudes.max() - latitudes.min()
    b_box["width"] = longitudes.max() - longitudes.min()
    b_box["center"] = {"lon": np.mean(longitudes), "lat": np.mean(latitudes)}

    # get the area of the bounding box in order to calculate a zoom-level
    area = b_box["height"] * b_box["width"]

    # * 1D-linear interpolation with numpy:
    # - Pass the area as the only x-value and not as a list, in order to return a
    #   scalar as well
    # - The x-points "xp" should be in parts in comparable order of magnitude of the
    #   given area
    # - The zoom-levels are adapted to the areas, i.e. start with the smallest area
    #   possible of 0 which leads to the highest possible zoom value 20, and so forth
    #   decreasing with increasing areas as these variables are antiproportional
    zoom = np.interp(
        x=area,
        xp=[0, 5**-10, 4**-10, 3**-10, 2**-10, 1**-10, 1**-5],
        fp=[20, 15, 14, 13, 12, 7, 5],
    )

    zoom = min([zoom, 15])  # do not use zoom 20

    # Finally, return the zoom level and the associated boundary-box center coordinates

    # NOTE: manual correction to view all of obs for Zeeland ...
    # (because of non-square window/extent?).
    return zoom - 1.25, b_box["center"]
