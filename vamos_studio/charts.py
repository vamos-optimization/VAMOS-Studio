"""Plotly figures of fronts: in 2D, in 3D, or in parallel coordinates with four or more objectives.

The palette is Transept's (transept/charts.py): the reference front in grey, the front in blue,
the selected solution in red. A front of three objectives is drawn in 3D, which can be rotated,
and in its three two-objective projections, as Transept draws its fronts of three objectives. With
four or more objectives each solution is a line across one axis per objective (parallel
coordinates), each objective scaled to [0, 1] over the reference front, or over the solutions drawn
when there is none.
"""

from __future__ import annotations

from itertools import combinations

import numpy as np
import plotly.graph_objects as go
from numpy.typing import NDArray
from plotly.subplots import make_subplots

REFERENCE_COLOUR = "#b7bcc5"
FRONT_COLOUR = "#1769aa"
SELECTED_COLOUR = "#d62728"
# From this number of objectives on, fronts are drawn in parallel coordinates.
PARALLEL_FROM = 4
# At most this many lines of a reference front are drawn in parallel coordinates.
MAX_PARALLEL_REFERENCE_LINES = 1500

Front = NDArray[np.float64]


def n_objectives(front: Front | None, reference_front: Front | None) -> int:
    """The number of objectives of the figure: that of the front, or of the reference front."""
    for points in (front, reference_front):
        if points is not None and points.ndim == 2 and points.shape[1]:
            return int(points.shape[1])
    return 2


def front_figure(
    front: Front | None,
    reference_front: Front | None = None,
    highlighted: int | None = None,
    highlighted_label: str = "Knee",
    front_label: str = "Front",
) -> go.Figure:
    """A front over its problem's reference front: in 2D, or in 3D for three objectives.

    Args:
        front: The objective values of the solutions, or None while there are none.
        reference_front: The problem's reference front, drawn behind, if known.
        highlighted: A row of `front` to mark, such as the knee.
        highlighted_label: The legend entry of the marked solution.
        front_label: The legend entry of the front.
    """
    labels = (front_label, highlighted_label)
    if n_objectives(front, reference_front) >= PARALLEL_FROM:
        groups = [(front, labels[0], FRONT_COLOUR, 1.5)]
        if front is not None and highlighted is not None:
            groups.append((front[highlighted : highlighted + 1], labels[1], SELECTED_COLOUR, 4.0))
        return parallel_figure(groups, reference_front)
    if n_objectives(front, reference_front) == 3:
        return _figure_3d(front, reference_front, highlighted, labels)
    figure = go.Figure()
    for trace in _traces_2d(front, reference_front, highlighted, labels, (0, 1)):
        figure.add_trace(trace)
    figure.update_layout(
        xaxis_title="f1",
        yaxis_title="f2",
        legend={"orientation": "h", "y": -0.2},
        margin={"t": 20},
    )
    return figure


def projections_figure(
    front: Front | None,
    reference_front: Front | None = None,
    highlighted: int | None = None,
    highlighted_label: str = "Knee",
    front_label: str = "Front",
) -> go.Figure:
    """The three two-objective projections of a front of three objectives, side by side."""
    labels = (front_label, highlighted_label)
    pairs = list(combinations(range(3), 2))
    figure = make_subplots(
        rows=1, cols=len(pairs), subplot_titles=[f"f{a + 1} – f{b + 1}" for a, b in pairs]
    )
    for column, pair in enumerate(pairs, start=1):
        traces = _traces_2d(front, reference_front, highlighted, labels, pair)
        for trace in traces:
            trace.showlegend = column == 1
            figure.add_trace(trace, row=1, col=column)
        figure.update_xaxes(title_text=f"f{pair[0] + 1}", row=1, col=column)
        figure.update_yaxes(title_text=f"f{pair[1] + 1}", row=1, col=column)
    figure.update_layout(legend={"orientation": "h", "y": -0.25}, margin={"t": 40}, height=380)
    return figure


def _traces_2d(
    front: Front | None,
    reference_front: Front | None,
    highlighted: int | None,
    labels: tuple[str, str],
    pair: tuple[int, int],
) -> list[go.Scatter]:
    traces = []
    if reference_front is not None:
        traces.append(_scatter(reference_front, pair, "Reference front", REFERENCE_COLOUR, 3))
    if front is not None and len(front):
        traces.append(_scatter(front, pair, labels[0], FRONT_COLOUR, 7))
        if highlighted is not None:
            point = front[highlighted : highlighted + 1]
            trace = _scatter(point, pair, labels[1], SELECTED_COLOUR, 14)
            trace.marker.symbol = "star"
            traces.append(trace)
    return traces


def _figure_3d(
    front: Front | None,
    reference_front: Front | None,
    highlighted: int | None,
    labels: tuple[str, str],
) -> go.Figure:
    figure = go.Figure()
    if reference_front is not None:
        figure.add_trace(
            _scatter_3d(reference_front, "Reference front", REFERENCE_COLOUR, 2, opacity=0.5)
        )
    if front is not None and len(front):
        figure.add_trace(_scatter_3d(front, labels[0], FRONT_COLOUR, 4))
        if highlighted is not None:
            point = front[highlighted : highlighted + 1]
            trace = _scatter_3d(point, labels[1], SELECTED_COLOUR, 8)
            trace.marker.symbol = "diamond"
            figure.add_trace(trace)
    figure.update_layout(
        height=560,
        margin={"l": 0, "r": 0, "t": 20, "b": 0},
        legend={"orientation": "h", "y": -0.05},
        scene={"xaxis_title": "f1", "yaxis_title": "f2", "zaxis_title": "f3"},
    )
    return figure


def _scatter(points: Front, pair: tuple[int, int], name: str, colour: str, size: int) -> go.Scatter:
    return go.Scatter(
        x=points[:, pair[0]],
        y=points[:, pair[1]],
        mode="markers",
        name=name,
        marker={"size": size, "color": colour},
    )


def _scatter_3d(
    points: Front, name: str, colour: str, size: int, opacity: float = 1.0
) -> go.Scatter3d:
    return go.Scatter3d(
        x=points[:, 0],
        y=points[:, 1],
        z=points[:, 2],
        mode="markers",
        name=name,
        opacity=opacity,
        marker={"size": size, "color": colour},
    )


def series_figure(
    fronts: list[Front], aggregate: Front, reference_front: Front | None = None
) -> go.Figure:
    """The fronts of a series' runs in grey and their non-dominated union in blue.

    As Transept draws the runs of a series (transept/charts.py, series_front_figure).
    """
    if n_objectives(aggregate, reference_front) >= PARALLEL_FROM:
        return parallel_figure(
            [
                (_stacked(fronts), "Runs", REFERENCE_COLOUR, 1.0),
                (aggregate, "Union of the runs", FRONT_COLOUR, 1.5),
            ],
            reference_front,
        )
    three = n_objectives(aggregate, reference_front) == 3
    figure = go.Figure()
    if reference_front is not None:
        figure.add_trace(_any_scatter(reference_front, "Reference front", "#e3e6ea", 2, three))
    for index, front in enumerate(fronts):
        trace = _any_scatter(front, "Runs", REFERENCE_COLOUR, 4, three)
        trace.showlegend = index == 0
        trace.legendgroup = "runs"
        figure.add_trace(trace)
    figure.add_trace(_any_scatter(aggregate, "Union of the runs", FRONT_COLOUR, 6, three))
    layout = {"legend": {"orientation": "h", "y": -0.15}, "margin": {"t": 20}}
    if three:
        layout["scene"] = {"xaxis_title": "f1", "yaxis_title": "f2", "zaxis_title": "f3"}
        layout["height"] = 560
    else:
        layout["xaxis_title"], layout["yaxis_title"] = "f1", "f2"
    figure.update_layout(**layout)
    return figure


def series_live_figure(
    active: list[Front], finished: list[Front], reference_front: Front | None = None
) -> go.Figure:
    """The current fronts of a series' runs in progress in blue, over the finished ones in grey.

    As Transept follows a series (transept/charts.py, series_progress_figure), with fronts.
    """
    drawn = [*active, *finished]
    if n_objectives(drawn[0] if drawn else None, reference_front) >= PARALLEL_FROM:
        return parallel_figure(
            [
                (_stacked(finished), "Finished runs", REFERENCE_COLOUR, 1.0),
                (_stacked(active), "Runs in progress", FRONT_COLOUR, 1.5),
            ],
            reference_front,
        )
    three = n_objectives(drawn[0] if drawn else None, reference_front) == 3
    figure = go.Figure()
    if reference_front is not None:
        figure.add_trace(_any_scatter(reference_front, "Reference front", "#e3e6ea", 2, three))
    groups = (
        (finished, "Finished runs", REFERENCE_COLOUR, 4),
        (active, "Runs in progress", FRONT_COLOUR, 6),  # last, so that they are on top
    )
    for fronts, name, colour, size in groups:
        for index, front in enumerate(fronts):
            trace = _any_scatter(front, name, colour, size, three)
            trace.showlegend = index == 0
            trace.legendgroup = name
            figure.add_trace(trace)
    layout = {"legend": {"orientation": "h", "y": -0.15}, "margin": {"t": 20}}
    if three:
        layout["scene"] = {"xaxis_title": "f1", "yaxis_title": "f2", "zaxis_title": "f3"}
        layout["height"] = 560
    else:
        layout["xaxis_title"], layout["yaxis_title"] = "f1", "f2"
    figure.update_layout(**layout)
    return figure


def _any_scatter(points: Front, name: str, colour: str, size: int, three: bool):
    if three:
        return _scatter_3d(points, name, colour, max(2, size - 2))
    return _scatter(points, (0, 1), name, colour, size)


def parallel_figure(
    groups: list[tuple[Front | None, str, str, float]], reference_front: Front | None = None
) -> go.Figure:
    """Solutions in parallel coordinates: one line per solution across one axis per objective.

    Each objective is scaled to [0, 1] over the reference front, or over the solutions drawn when
    there is none, so that a value above 1 is worse than the reference front's worst. Hovering a
    line shows the objective's value before scaling.

    Args:
        groups: The solutions to draw, in order (the last on top), each as (points, legend entry,
            colour, line width); points may be None or empty.
        reference_front: The reference front, drawn behind in grey (a sample of its lines).
    """
    drawn = [points for points, *_ in groups if points is not None and len(points)]
    known = reference_front if reference_front is not None else _stacked(drawn)
    n_obj = n_objectives(known, None)
    low, span = _scale(known)
    figure = go.Figure()
    if reference_front is not None:
        sample = _sample_rows(reference_front, MAX_PARALLEL_REFERENCE_LINES)
        figure.add_trace(
            _parallel_trace(sample, low, span, "Reference front", "#d5d9df", 1.0, hover=False)
        )
    for points, name, colour, width in groups:
        if points is not None and len(points):
            figure.add_trace(_parallel_trace(points, low, span, name, colour, width, hover=True))
    names = [f"f{index + 1}" for index in range(n_obj)]
    figure.update_layout(
        xaxis={
            "tickmode": "array",
            "tickvals": list(range(1, n_obj + 1)),
            "ticktext": names,
            # A margin on both sides, so that the labels of the first and last axes show.
            "range": [0.7, n_obj + 0.3],
        },
        yaxis={"title": "Scaled value", "zeroline": False},
        legend={"orientation": "h", "y": -0.15},
        margin={"t": 20},
        height=460,
    )
    return figure


def _parallel_trace(
    points: Front,
    low: NDArray[np.float64],
    span: NDArray[np.float64],
    name: str,
    colour: str,
    width: float,
    hover: bool,
) -> go.Scattergl:
    """The lines of `points`, one per row, separated by gaps."""
    rows, n_obj = points.shape
    gap = np.full((rows, 1), np.nan)
    x = np.tile(np.append(np.arange(1.0, n_obj + 1.0), np.nan), rows)
    y = np.hstack([(points - low) / span, gap]).ravel()
    raw = np.hstack([points, gap]).ravel()
    return go.Scattergl(
        x=x,
        y=y,
        mode="lines",
        name=name,
        line={"color": colour, "width": width},
        customdata=raw,
        hovertemplate="f%{x}: %{customdata:.4g}<extra>" + name + "</extra>" if hover else None,
        hoverinfo=None if hover else "skip",
        connectgaps=False,
    )


def _scale(points: Front | None) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """The lower bound and the range of each objective over `points` (a range of 0 counts as 1)."""
    if points is None or not len(points):
        return np.zeros(1), np.ones(1)
    low, high = points.min(axis=0), points.max(axis=0)
    return low, np.where(high > low, high - low, 1.0)


def _sample_rows(points: Front, limit: int) -> Front:
    """At most `limit` rows of `points`, evenly spaced."""
    return points if len(points) <= limit else points[:: -(-len(points) // limit)]


def _stacked(fronts: list[Front]) -> Front | None:
    """The rows of several fronts in one array, or None without any."""
    present = [front for front in fronts if front is not None and len(front)]
    return np.vstack(present) if present else None
