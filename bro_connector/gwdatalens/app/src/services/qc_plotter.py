"""Figure generation for quality control visualization.

Handles creation of plotly figures for QC result visualization,
including traval detection markers, model simulations, and
additional series overlays.
"""

import logging
from typing import Any, Dict, List, Optional, Union

import numpy as np
import plotly.express as px
import plotly.graph_objs as go
import traval
from pandas import DataFrame, Series, Timedelta

from gwdatalens.app.constants import PlotConstants, QCDefaults
from gwdatalens.app.src.data.util import get_model_sim_pi

logger = logging.getLogger(__name__)


class QCPlotter:
    """Creates plotly figures for quality control visualization.

    Responsible for:
    - Building time series traces
    - Adding detection markers
    - Overlaying model simulations and prediction intervals
    - Layout configuration
    - Axes limit calculation

    This class isolates visualization logic from detection
    and data formatting.
    """

    def plot_detection_result(
        self,
        detector: traval.Detector,
        model: Optional[Any] = None,
        tmin: Optional[Any] = None,
        tmax: Optional[Any] = None,
        ignore: Optional[List] = None,
        qualifiers: Optional[Series] = None,
        additional_series: Optional[Union[Series, DataFrame, List]] = None,
    ) -> Dict[str, Any]:
        """Create a complete QC detection result plot.

        Parameters
        ----------
        detector : traval.Detector
            Detector instance with detection results
        model : object, optional
            Pastas time series model for simulation/PI, by default None
        tmin : datetime-like, optional
            Plot start time, by default None
        tmax : datetime-like, optional
            Plot end time, by default None
        ignore : list-like, optional
            Indices to ignore (e.g., already validated), by default None
        qualifiers : Series, optional
            Qualifiers to color-code observations, by default None
        additional_series : Series/DataFrame/list, optional
            Additional series to overlay, by default None

        Returns
        -------
        dict
            Plotly figure dict with 'data' (traces) and 'layout' keys
        """
        logger.info("Creating QC plot for %s", detector.series.name)

        traces = []

        # Add main time series trace
        traces.append(self._create_main_series_trace(detector))

        # Add qualifier-based color coding if provided
        if qualifiers is not None:
            traces.extend(self._create_qualifier_traces(detector, qualifiers))

        # Add additional series (e.g., manual observations)
        if additional_series is not None:
            traces.extend(self._create_additional_series_traces(additional_series))

        # Add detection markers
        traces.extend(self._create_detection_marker_traces(detector, ignore))

        # Add model simulation and prediction interval
        if model is not None:
            model_traces, _ = self._create_model_traces(detector, model, tmin, tmax)
            traces = model_traces + traces

        # Create layout
        layout = self._create_layout(detector, model, tmin, tmax, ignore)

        # Compute trace metadata: has_pastas and observations_trace_index
        has_pastas = model is not None
        observations_trace_index = 0
        if has_pastas:
            # Model traces are prepended, so observations shift right
            # Count model traces: CI + simulation = 3
            observations_trace_index = 3

        trace_info = {
            "has_pastas": has_pastas,
            "observations_trace_index": observations_trace_index,
        }

        return (
            {"data": traces, "layout": layout},
            trace_info,
        )

    def _create_main_series_trace(self, detector: traval.Detector) -> go.Scattergl:
        """Create trace for main time series.

        Parameters
        ----------
        detector : traval.Detector
            Detector with series

        Returns
        -------
        go.Scattergl
            Main series trace
        """
        ts = detector.series
        return go.Scattergl(
            x=ts.index,
            y=ts.values,
            mode="markers+lines",
            line={"width": 1, "color": "gray"},
            marker={"size": 3, "line_color": "gray"},
            name=ts.name,
            legendgroup=ts.name,
            showlegend=True,
            selected={"marker": {"opacity": 1.0, "size": 6, "color": "black"}},
            unselected={"marker": {"opacity": 1.0, "size": 3, "color": "gray"}},
            selectedpoints=[],
        )

    def _create_qualifier_traces(
        self, detector: traval.Detector, qualifiers: Series
    ) -> List[go.Scattergl]:
        """Create traces for different data qualifiers.

        Parameters
        ----------
        detector : traval.Detector
            Detector with series
        qualifiers : Series
            Qualifier values per observation

        Returns
        -------
        list of go.Scattergl
            Qualifier traces
        """
        traces = []
        ts = detector.series
        qualifier_colors = {
            "goedgekeurd": "green",
            "onbeslist": "orange",
            "afgekeurd": "red",
            "": "#636EFA",
        }

        for qualifier in qualifiers.unique():
            mask = qualifiers == qualifier
            ts_qual = ts.loc[mask]

            color = qualifier_colors.get(qualifier, "gray")
            trace = go.Scattergl(
                x=ts_qual.index,
                y=ts_qual.values,
                mode="markers",
                marker={"color": color, "size": 4},
                name=qualifier or "(empty)",
                legendgroup=qualifier,
                showlegend=True,
                legendrank=1000,
            )
            traces.append(trace)

        return traces

    def _create_additional_series_traces(
        self, additional_series: Union[Series, DataFrame, List]
    ) -> List[go.Scattergl]:
        """Create traces for additional series (e.g., manual observations).

        Parameters
        ----------
        additional_series : Series/DataFrame/list
            Additional series to plot

        Returns
        -------
        list of go.Scattergl
            Additional series traces
        """
        if isinstance(additional_series, (Series, DataFrame)):
            additional_series = [additional_series]
        elif not isinstance(additional_series, list):
            raise ValueError("additional_series should be a Series, DataFrame, or list")

        traces = []
        for add_series in additional_series:
            trace = go.Scattergl(
                x=add_series.index,
                y=add_series.values if isinstance(add_series, Series) else add_series,
                mode="markers",
                marker={"color": "red", "size": 6},
                name=getattr(add_series, "name", "additional data"),
                legendgroup="manual obs",
                showlegend=True,
                legendrank=1001,
            )
            traces.append(trace)

        return traces

    def _create_detection_marker_traces(
        self, detector: traval.Detector, ignore: Optional[List] = None
    ) -> List[go.Scattergl]:
        """Create traces for detection markers.

        Parameters
        ----------
        detector : traval.Detector
            Detector with corrections
        ignore : list, optional
            Indices to ignore

        Returns
        -------
        list of go.Scattergl
            Detection marker traces
        """
        traces = []
        ts = detector.series
        colors = px.colors.qualitative.Dark24

        for step, corrections in detector.corrections.items():
            if isinstance(corrections, np.ndarray) or corrections.empty:
                continue

            # Filter out ignored indices if provided
            if ignore is not None:
                idx = corrections.index.difference(ignore)
            else:
                idx = corrections.index

            if idx.size == 0:
                continue

            ts_marked = ts.loc[idx]
            label = detector.ruleset.get_step_name(step)

            trace = go.Scattergl(
                x=ts_marked.index,
                y=ts_marked.values,
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
            traces.append(trace)

        return traces

    def _create_model_traces(
        self,
        detector: traval.Detector,
        model: Any,
        tmin: Optional[Any] = None,
        tmax: Optional[Any] = None,
    ) -> tuple:
        """Create traces for model simulation and prediction interval.

        Parameters
        ----------
        detector : traval.Detector
            Detector with series and ruleset
        model : object
            Pastas model
        tmin : datetime-like, optional
            Simulation start time
        tmax : datetime-like, optional
            Simulation end time
        ignore : list, optional
            Indices to ignore for PI limits

        Returns
        -------
        tuple
            (list of traces, dict with sim and pi)
        """
        ts = detector.series

        # Get confidence interval from ruleset
        try:
            ci = detector.ruleset.get_rule(stepname="pastas")["kwargs"]["ci"]
        except (KeyError, IndexError):
            ci = QCDefaults.PASTAS_CI

        # Get save directory for PI cache
        try:
            savedir = detector.ruleset.get_rule(stepname="pastas")["kwargs"]["savedir"]
        except (KeyError, IndexError):
            savedir = None

        # Get model simulation and PI
        sim, pi = get_model_sim_pi(
            model,
            ts,
            ci=ci,
            tmin=tmin,
            tmax=tmax,
            smoothfreq="30D",
            savedir=savedir,
        )

        # Create traces
        trace_sim = go.Scattergl(
            x=sim.index,
            y=sim.values,
            mode="lines",
            line={"width": 1, "color": PlotConstants.SIM_LINE_COLOR},
            name="model simulation",
            legendgroup="model simulation",
            showlegend=True,
            legendrank=1001,
        )

        trace_lower = go.Scattergl(
            x=pi.index,
            y=pi.iloc[:, 0].values,
            mode="lines",
            line={"width": 0.5, "color": PlotConstants.CI_LINE_COLOR},
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
            line={"width": 0.5, "color": PlotConstants.CI_LINE_COLOR},
            name=f"PI ({ci:.1%})",
            legendgroup="PI",
            showlegend=True,
            fill="tonexty",
            fillcolor=PlotConstants.CI_FILL_COLOR,
            legendrank=1002,
        )

        return [trace_lower, trace_upper, trace_sim], {"sim": sim, "pi": pi}

    def _create_layout(
        self,
        detector: traval.Detector,
        model: Optional[Any] = None,
        tmin: Optional[Any] = None,
        tmax: Optional[Any] = None,
        ignore: Optional[List] = None,
    ) -> Dict[str, Any]:
        """Create plotly layout configuration.

        Parameters
        ----------
        detector : traval.Detector
            Detector with series
        model : object, optional
            Model for PI calculation
        tmin : datetime-like, optional
            Plot start time
        tmax : datetime-like, optional
            Plot end time
        ignore : list, optional
            Indices to ignore for axis limits

        Returns
        -------
        dict
            Layout configuration
        """
        layout = {
            "yaxis": {"title": "(m NAP)"},
            "legend": {
                "traceorder": "reversed+grouped",
                "orientation": "h",
                "xanchor": "left",
                "yanchor": "bottom",
                "x": 0.0,
                "y": 1.02,
            },
            "dragmode": "pan",
            "margin": {"l": 50, "r": 20},
        }

        # Set axis limits based on data range
        if ignore is not None:
            layout = self._set_axis_limits_with_ignore(layout, detector, model, ignore)

        return layout

    def _set_axis_limits_with_ignore(
        self,
        layout: Dict[str, Any],
        detector: traval.Detector,
        model: Optional[Any],
        ignore: List,
    ) -> Dict[str, Any]:
        """Set axis limits for plot with ignored indices.

        Parameters
        ----------
        layout : dict
            Layout to update
        detector : traval.Detector
            Detector with series
        model : object, optional
            Model for PI calculation
        ignore : list
            Indices to ignore

        Returns
        -------
        dict
            Updated layout
        """
        ts = detector.series
        idxlim = ts.index.difference(ignore)

        if len(idxlim) == 0:
            return layout

        # Set x-axis limits with padding
        dx = Timedelta(
            days=0.05 * (idxlim[-1] - idxlim[0]).total_seconds() / (24 * 60 * 60)
        )
        layout["xaxis"] = {"range": [idxlim[0] - dx, idxlim[-1] + dx]}

        # Set y-axis limits with padding
        ymax = ts.loc[idxlim].max()
        ymin = ts.loc[idxlim].min()

        if model is not None:
            # Also consider PI bounds
            try:
                ci = detector.ruleset.get_rule(stepname="pastas")["kwargs"]["ci"]
            except (KeyError, IndexError):
                ci = QCDefaults.PASTAS_CI

            try:
                savedir = detector.ruleset.get_rule(stepname="pastas")["kwargs"][
                    "savedir"
                ]
            except (KeyError, IndexError):
                savedir = None

            _, pi = get_model_sim_pi(
                model,
                ts,
                ci=ci,
                smoothfreq="30D",
                savedir=savedir,
            )
            ymax = np.max([ymax, pi.loc[idxlim].iloc[:, 1].max()])
            ymin = np.min([ymin, pi.loc[idxlim].iloc[:, 0].min()])

        dy = 0.05 * (ymax - ymin)
        layout["yaxis"]["range"] = [ymin - dy, ymax + dy]

        return layout
