"""Plotly figures of fronts.

The palette is Transept's (transept/charts.py): the reference front in grey, the front in blue,
the selected solution in red.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
from numpy.typing import NDArray

REFERENCE_COLOUR = "#b7bcc5"
FRONT_COLOUR = "#1769aa"
SELECTED_COLOUR = "#d62728"


def front_figure(
    front: NDArray[np.float64] | None,
    reference_front: NDArray[np.float64] | None = None,
    highlighted: int | None = None,
    highlighted_label: str = "Knee",
) -> go.Figure:
    """A two-objective front over its problem's reference front.

    Args:
        front: The objective values of the solutions, or None while there are none.
        reference_front: The problem's reference front, drawn behind, if known.
        highlighted: A row of `front` to mark, such as the knee.
        highlighted_label: The legend entry of the marked solution.
    """
    figure = go.Figure()
    if reference_front is not None:
        figure.add_trace(_scatter(reference_front, "Reference front", REFERENCE_COLOUR, 3))
    if front is not None and len(front):
        figure.add_trace(_scatter(front, "Front", FRONT_COLOUR, 7))
        if highlighted is not None:
            point = front[highlighted : highlighted + 1]
            trace = _scatter(point, highlighted_label, SELECTED_COLOUR, 14)
            trace.marker.symbol = "star"
            figure.add_trace(trace)
    figure.update_layout(
        xaxis_title="f1",
        yaxis_title="f2",
        legend={"orientation": "h", "y": -0.2},
        margin={"t": 20},
    )
    return figure


def _scatter(points: NDArray[np.float64], name: str, colour: str, size: int) -> go.Scatter:
    return go.Scatter(
        x=points[:, 0],
        y=points[:, 1],
        mode="markers",
        name=name,
        marker={"size": size, "color": colour},
    )
