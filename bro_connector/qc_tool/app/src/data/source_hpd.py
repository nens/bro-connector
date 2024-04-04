import logging
import os
import pickle
from functools import lru_cache
from typing import List, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import traval
from icecream import ic

from .util import get_model_sim_pi

logger = logger = logging.getLogger(__name__)


class DataSourceHydropandas:
    def __init__(self, oc=None, fname=None, source="dino"):
        if oc is None:
            if fname is None:
                fname = "obs_collection.pickle"
            if os.path.isfile(fname):
                with open(fname, "rb") as file:
                    oc = pickle.load(file)
            else:
                import hydropandas as hpd

                extent = [18000, 38000, 384000, 403000]
                extent = [18000, 25000, 393000, 403000]
                extent = [48000, 52000, 422000, 427000]
                oc = hpd.read_bro(extent, tmin="2020", tmax="2024")
                with open(fname, "wb") as file:
                    pickle.dump(oc, file)
            # only keep locations with time series
            # oc = oc[[not oc.loc[index]["obs"].empty for index in oc.index]]

        self.source = source
        if self.source == "bro":
            self.value_column = "values"
            self.qualifier_column = "qualifier"
        else:
            self.value_column = "stand_m_tov_nap"
            self.qualifier_column = "bijzonderheid"

        # oc = oc[
        #     [
        #         not oc.loc[index, "obs"].loc[:, self.value_column].dropna().empty
        #         for index in oc.index
        #     ]
        # ]
        self.oc = oc
        self.traval_result = None

    @lru_cache
    def gmw_to_gdf(self):
        """Return all groundwater monitoring wells (gmw) as a GeoDataFrame"""
        oc = self.oc
        gdf = gpd.GeoDataFrame(oc, geometry=gpd.points_from_xy(oc.x, oc.y))
        columns = {
            "monitoring_well": "bro_id",
            "screen_bottom": "screen_bot",
            "tube_nr": "tube_number",
        }
        gdf = gdf.rename(columns=columns)
        gdf["nitg_code"] = ""

        # add number of measurements
        gdf["metingen"] = self.oc.stats.n_observations

        gdf["bro_id"] = gdf.index.tolist()

        return gdf

    @lru_cache
    def list_locations(self) -> List[Tuple[str, int]]:
        """Return a list of locations that contain groundwater level dossiers, where
        each location is defines by a tuple of length 2: bro-id and tube_id"""
        oc = self.oc
        locations = []
        mask = [not x.loc[:, self.value_column].dropna().empty for x in oc["obs"]]
        for index in oc[mask].index:
            locations.append(tuple(oc.loc[index, ["monitoring_well", "tube_nr"]]))
        return locations

    def list_locations_sorted_by_distance(self, name):
        gdf = self.gmw_gdf.copy()
        p = gdf.loc[name, "geometry"]
        gdf.drop(name, inplace=True)
        dist = gdf.distance(p)
        dist.name = "distance"
        distsorted = self.oc.join(dist, how="right").sort_values(
            "distance", ascending=True
        )
        return distsorted
        # return list(
        #     distsorted.loc[:, ["monitoring_well", "tube_nr"]]
        #     .apply(tuple, axis=1)
        #     .values
        # )

    def get_timeseries(self, gmw_id: str, tube_id: int, column="values") -> pd.Series:
        """Return a Pandas Series for the measurements at the requested bro-id and
        tube-id, im m. Return None when there are no measurements."""

        if self.source == "bro":
            name = f"{gmw_id}_{tube_id}"  # bro
        elif self.source == "dino":
            name = f"{gmw_id}-{tube_id}"  # dino
        else:
            raise ValueError

        columns = [self.value_column, self.qualifier_column]
        df = pd.DataFrame(self.oc.loc[name, "obs"].loc[:, columns])
        return df

    def run_traval(self, gmw_id, tube_id):
        name = f"{gmw_id}-{tube_id}"
        ic(f"Running traval for {name}...")
        ts = self.get_timeseries(gmw_id, tube_id)

        series = ts.loc[:, self.value_column]
        series.name = f"{gmw_id}-{tube_id}"
        detector = traval.Detector(series)
        detector.apply_ruleset(self.ruleset)

        comments = detector.get_comment_series()

        df = detector.series.to_frame().loc[comments.index]
        df.columns = ["values"]
        df["comment"] = ""
        df.loc[comments.index, "comment"] = comments

        df.index.name = "datetime"
        # table = df.reset_index().to_dict("records")

        # self.
        try:
            ml = self.pstore.get_models(series.name)
        except Exception as e:
            ic(e)
            ml = None
        figure = plot_traval_result(detector, ml)
        return df, figure

    def attach_pastastore(self, pstore):
        self.pstore = pstore

    def load_ruleset(self):
        # ruleset
        # initialize RuleSet object
        rset = traval.RuleSet(name="basic")

        # add rules
        rset.add_rule(
            "spikes",
            traval.rulelib.rule_spike_detection,
            apply_to=0,
            kwargs={"threshold": 0.15, "spike_tol": 0.15, "max_gap": "7D"},
        )
        rset.add_rule(
            "hardmax",
            traval.rulelib.rule_ufunc_threshold,
            apply_to=0,
            kwargs={
                "ufunc": (np.greater,),
                "threshold": lambda name: self.oc.loc[name, "obs"].meta["tube_top"],
            },
        )
        rset.add_rule(
            "flat_signal",
            traval.rulelib.rule_flat_signal,
            apply_to=0,
            kwargs={"window": 100, "min_obs": 5, "std_threshold": 2e-2},
        )
        rset.add_rule(
            "offsets",
            traval.rulelib.rule_offset_detection,
            apply_to=0,
            kwargs={
                "threshold": 0.5,
                "updown_diff": 0.5,
                "max_gap": "100D",
                "search_method": "time",
            },
        )
        ci = 0.99
        rset.add_rule(
            "pastas",
            traval.rulelib.rule_pastas_outside_pi,
            apply_to=0,
            kwargs={
                "ml": lambda name: self.pstore.models[name],
                "ci": ci,
                "min_ci": 0.1,
                "smoothfreq": "30D",
                "verbose": True,
            },
        )
        rset.add_rule(
            "combine_results", traval.rulelib.rule_combine_nan_or, apply_to=(1, 2, 3, 4)
        )

        # set ruleset in data object
        self.ruleset = rset


def plot_traval_result(detector, model=None):
    traces = []

    ts0 = detector.series

    trace_0 = go.Scattergl(
        x=ts0.index,
        y=ts0.values,
        mode="markers+lines",
        line={
            "width": 1,
            "color": "gray",
        },
        marker={
            "size": 3,
            "line_color": "gray",
        },
        name=ts0.name,
        legendgroup=ts0.name,
        showlegend=True,
    )
    traces.append(trace_0)

    colors = px.colors.qualitative.Dark24
    for step, corrections in detector.corrections.items():
        if isinstance(corrections, np.ndarray) or corrections.empty:
            continue
        ts_i = ts0.loc[corrections.index]
        label = detector.ruleset.get_step_name(step)
        trace_i = go.Scattergl(
            x=ts_i.index,
            y=ts_i.values,
            mode="markers",
            marker={
                "size": 8,
                "symbol": "x-thin",
                "line_width": 2,
                "line_color": colors[(step - 1) % len(colors)],
            },
            name=label,
            legendgroup=label,
            showlegend=True,
            legendrank=1003,
        )
        traces.append(trace_i)

    if model is not None:
        try:
            ci = detector.ruleset.get_rule(stepname="pastas")["kwargs"]["ci"]
        except KeyError:
            ci = 0.95
        sim, pi = get_model_sim_pi(model, ts0, ci=ci, smoothfreq="30D")
        trace_sim = go.Scattergl(
            x=sim.index,
            y=sim.values,
            mode="lines",
            line={
                "width": 1,
                "color": "cornflowerblue",
            },
            name="model simulation",
            legendgroup="model simulation",
            showlegend=True,
            legendrank=1001,
        )
        trace_lower = go.Scattergl(
            x=pi.index,
            y=pi.iloc[:, 0].values,
            mode="lines",
            line={"width": 0.5, "color": "rgba(100,149,237,0.35)"},
            name=f"PI ({ci:.1%})",
            legendgroup="PI",
            showlegend=False,
            fill="tonexty",
            legendrank=1005,
        )
        trace_upper = go.Scattergl(
            x=sim.index,
            y=pi.iloc[:, 1].values,
            mode="lines",
            line={"width": 0.5, "color": "rgba(100,149,237,0.35)"},
            name=f"PI ({ci:.1%})",
            legendgroup="PI",
            showlegend=True,
            fill="tonexty",
            fillcolor="rgba(100,149,237,0.1)",
            legendrank=1002,
        )

        traces = [trace_lower, trace_upper] + traces + [trace_sim]

    layout = {
        # "xaxis": {"range": [sim.index[0], sim.index[-1]]},
        "yaxis": {"title": "(m NAP)"},
        "legend": {
            "traceorder": "reversed+grouped",
            "orientation": "h",
            "xanchor": "left",
            "yanchor": "bottom",
            "x": 0.0,
            "y": 1.02,
        },
        # "hovermode": "x",
        "dragmode": "pan",
        # "margin": dict(t=70, b=40, l=40, r=10),
    }

    return dict(data=traces, layout=layout)
