from copy import deepcopy
from pathlib import Path

import i18n
import numpy as np
import plotly.express as px
import plotly.graph_objs as go
import traval
from icecream import ic
from pandas import Timedelta

from gwdatalens.app.settings import settings

from .util import get_model_sim_pi


class TravalInterface:
    def __init__(self, db, pstore=None):
        self.db = db
        self.pstore = pstore
        self.ruleset = None
        self._ruleset = None

        self.traval_result = None
        self.traval_figure = None

        # set ruleset in data object
        self.ruleset = self.get_default_ruleset()
        self._ruleset = deepcopy(self.ruleset)

    def get_default_ruleset(self):
        # ruleset
        # initialize RuleSet object
        ruleset = traval.RuleSet(name="default")

        # add rules
        ruleset.add_rule(
            "spikes",
            traval.rulelib.rule_spike_detection,
            apply_to=0,
            kwargs={"threshold": 0.40, "spike_tol": 0.20, "max_gap": "30D"},
        )

        def get_tube_top_level(name):
            return self.db.gmw_gdf.loc[name, "tube_top_position"].item()

        ruleset.add_rule(
            "hardmax",
            traval.rulelib.rule_hardmax,
            apply_to=0,
            kwargs={
                "threshold": get_tube_top_level,
            },
        )
        ruleset.add_rule(
            "flat_signal",
            traval.rulelib.rule_flat_signal,
            apply_to=0,
            kwargs={"window": 100, "min_obs": 5, "std_threshold": 2e-2},
        )
        # ruleset.add_rule(
        #     "offsets",
        #     traval.rulelib.rule_offset_detection,
        #     apply_to=0,
        #     kwargs={
        #         "threshold": 0.5,
        #         "updown_diff": 0.5,
        #         "max_gap": "100D",
        #         "search_method": "time",
        #     },
        # )
        ci = 0.99
        ruleset.add_rule(
            "pastas",
            traval.rulelib.rule_pastas_outside_pi,
            apply_to=0,
            kwargs={
                "ml": lambda name: self.pstore.models[name],
                "ci": ci,
                "min_ci": 0.1,
                "smoothfreq": "30D",
                "savedir": Path(".pi_cache/"),
                # "verbose": True,
            },
        )
        ruleset.add_rule(
            "combine_results",
            traval.rulelib.rule_combine_nan_or,
            apply_to=(1, 2, 3, 4),
        )
        return ruleset

    def run_traval(
        self,
        gmw_id,
        tube_id,
        ruleset=None,
        tmin=None,
        tmax=None,
        only_unvalidated=False,
    ):
        name = f"{gmw_id}-{int(tube_id):03g}"
        ic(f"Running traval for {name}...")
        ts = self.db.get_timeseries(gmw_id, tube_id)

        if tmin is not None:
            ts = ts.loc[tmin:]
        if tmax is not None:
            ts = ts.loc[:tmax]
        series = ts.loc[:, self.db.value_column]
        series.name = f"{gmw_id}-{tube_id}"
        detector = traval.Detector(series)
        ruleset = self._ruleset
        detector.apply_ruleset(ruleset)

        # NOTE: store detector for now to inspect result
        # self.detector = detector

        comments = detector.get_comment_series()

        # df = detector.series.to_frame().loc[comments.index]
        df = ts.join(detector.get_results_dataframe())

        # add id column
        df["id"] = range(df.index.size)

        # set flagged
        df["flagged"] = 0  # 1=flagged, 0=not flagged
        df.loc[comments.index, "flagged"] = 1

        # set comments based on traval result
        df["comment"] = ""
        df.loc[comments.index, "comment"] = comments

        # rename some stuff
        df.rename(columns={"base series": "values"}, inplace=True)
        df.index.name = "datetime"

        # set incoming status_quality_control value from database
        df["incoming_status_quality_control"] = ts[self.db.qualifier_column]
        if settings["LOCALE"] == "en":
            bro_nl_to_en = {
                "": "",
                "onbekend": "unknown",
                "onbeslist": "undecided",
                "afgekeurd": "unreliable",
                "goedgekeurd": "reliable",
                "unknown": "unknown",
                "undecided": "undecided",
                "unreliable": "unreliable",
                "reliable": "reliable",
            }
            df["incoming_status_quality_control"] = df[
                "incoming_status_quality_control"
            ].apply(lambda v: bro_nl_to_en[v])

        # set current status to blank and mark suspect observations unreliable as
        # suggestion
        df["status_quality_control"] = ""
        df.loc[df["flagged"] == 1, "status_quality_control"] = i18n.t(
            "general.unreliable"
        )

        df["category"] = ""  # for QC Protocol category

        # filter out observations that were already checked
        if only_unvalidated:
            mask = df["incoming_status_quality_control"].isin(
                [
                    i18n.t("general.reliable"),
                    i18n.t("general.unreliable"),
                    i18n.t("general.undecided"),
                ]
            )

            df.loc[mask, "flagged"] = -1  # set already checked to (-1)
            df.loc[mask, "comment"] = ""  # set comments already checked to empty
            df.loc[mask, "status_quality_control"] = ""  # set qc check to empty

            ignore = df.loc[mask].index

            if mask.sum() == df.index.size:
                raise ValueError(i18n.t("general.alert_all_observations_checked"))

            # NOTE: uncomment below to filter out already checked observations from
            # table this is a pain in the @$$ for synchronizing selections between
            # table/chart though, so turning it off for now.
            # df = df.loc[~mask]
        else:
            ignore = None

        try:
            ml = self.pstore.get_models(series.name)
        except Exception as _:
            ml = None
        figure = self.plot_traval_result(
            detector,
            ml,
            tmin=tmin,
            tmax=tmax,
            ignore=ignore,
            qualifiers=ts[self.db.qualifier_column],
        )
        return df, figure

    @staticmethod
    def plot_traval_result(
        detector, model=None, tmin=None, tmax=None, ignore=None, qualifiers=None
    ):
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
            selected={"marker": {"opacity": 1.0, "size": 6, "color": "black"}},
            unselected={"marker": {"opacity": 1.0, "size": 3, "color": "gray"}},
            selectedpoints=[],
        )
        traces.append(trace_0)

        if qualifiers is not None:
            # plot different qualifiers
            for qualifier in qualifiers.unique():
                mask = qualifiers == qualifier
                ts = ts0.loc[mask]
                legendrank = 1000
                if qualifier in ["goedgekeurd"]:
                    color = "green"
                elif qualifier in ["onbeslist"]:
                    color = "orange"
                elif qualifier in ["afgekeurd"]:
                    color = "red"
                elif qualifier == "":
                    color = "#636EFA"
                    # legendrank = 999
                else:
                    color = "gray"
                trace_i = go.Scattergl(
                    x=ts.index,
                    y=ts.values,
                    mode="markers",
                    marker={"color": color, "size": 4},
                    name=qualifier,
                    legendgroup=qualifier,
                    showlegend=True,
                    legendrank=legendrank,
                )
                traces.append(trace_i)

        colors = px.colors.qualitative.Dark24
        for step, corrections in detector.corrections.items():
            if isinstance(corrections, np.ndarray) or corrections.empty:
                continue
            if ignore is not None:
                idx = corrections.index.difference(ignore)
            else:
                idx = corrections.index

            if idx.size == 0:
                continue

            ts_i = ts0.loc[idx]
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

            try:
                savedir = detector.ruleset.get_rule(stepname="pastas")["kwargs"][
                    "savedir"
                ]
            except KeyError:
                savedir = None

            sim, pi = get_model_sim_pi(
                model,
                ts0,
                ci=ci,
                tmin=tmin,
                tmax=tmax,
                smoothfreq="30D",
                savedir=savedir,
            )
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
            "margin": dict(l=50, r=20),
        }
        # set axes limits
        if ignore is not None:
            idxlim = ts0.index.difference(ignore)
            dx = Timedelta(
                days=0.05 * (idxlim[-1] - idxlim[0]).total_seconds() / (24 * 60 * 60)
            )
            layout["xaxis"] = {"range": [idxlim[0] - dx, idxlim[-1] + dx]}
            ymax = ts0.loc[idxlim].max()
            if model is not None:
                ymax = np.max([ymax, pi.loc[idxlim].iloc[:, 1].max()])
            ymin = ts0.loc[idxlim].min()
            if model is not None:
                ymin = np.min([ymin, pi.loc[idxlim].iloc[:, 0].min()])
            dy = 0.05 * (ymax - ymin)
            layout["yaxis"]["range"] = [ymin - dy, ymax + dy]

        return dict(data=traces, layout=layout)
