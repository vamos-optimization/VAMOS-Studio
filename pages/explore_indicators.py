"""Explore › Quality indicators: VAMOS's indicators, what each one measures, and a sandbox."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from vamos_studio.backend.catalogue import (
    problem_entries,
    reference_front,
    reference_front_source,
)
from vamos_studio.backend.indicators import INDICATORS, available_indicators, compute_all
from vamos_studio.front_sample import sample_front

# Transept's palette (transept/charts.py): the background points in grey, the front in blue.
REFERENCE_COLOUR = "#b7bcc5"
APPROXIMATION_COLOUR = "#1769aa"

st.title("Quality indicators")
st.markdown(
    "The quality indicators of VAMOS, and how the studio uses them. Following Evolver's "
    "convention, a front is first **normalized** with the minimum and maximum of each objective "
    "of its problem's reference front, so values are comparable across problems and with "
    "Evolver-Studio. The hypervolume clips the normalized front to [0, 1] and is measured up to "
    "the point (1, ..., 1); the other indicators measure it against the normalized reference "
    "front. VAMOS computes them all, with moocore."
)
st.info(
    "Prototype: the indicators that compare whole fronts on two-objective problems are "
    "available. The others are listed with the reason they are not active yet.",
    icon=":material/construction:",
)

# A markdown table, not st.dataframe (as in Evolver-Studio): the descriptions are the point, and
# it wraps them instead of truncating them.
rows = "\n".join(
    f"| {entry.short_name} | {entry.full_name} | `{entry.key}` | "
    f"{'higher' if entry.maximized else 'lower'} | {entry.needs} | "
    f"{'✅' if entry.available else '⏳'} | {entry.measures}"
    f"{' *Computed by the studio from VAMOS’s hypervolume.*' if entry.computed_by_studio else ''}"
    f"{' *Not active: ' + entry.note + '*' if entry.note else ''} |"
    for entry in INDICATORS
)
st.markdown(
    "| Abbreviation | Indicator | Name in VAMOS | Better | Measured against | Status | "
    "What it measures |\n|---|---|---|---|---|---|---|\n" + rows
)
with st.expander("References"):
    st.markdown("\n".join(f"- **{entry.short_name}**: {entry.citation}" for entry in INDICATORS))

st.header("Try it")
st.markdown(
    "Take evenly spread points of a reference front, move them away from it, and see how each "
    "indicator responds. With all the points and no shift, every distance indicator is 0."
)
problems = [entry for entry in problem_entries() if entry.available]
controls = st.columns(3)
problem = controls[0].selectbox("Problem", problems, format_func=lambda item: item.label)
n_points = controls[1].slider("Points", min_value=2, max_value=200, value=20)
shift = controls[2].slider(
    "Shift (fraction of each objective's range)",
    min_value=0.0,
    max_value=0.2,
    value=0.02,
    step=0.005,
    format="%.3f",
)

front = reference_front(problem.key, problem.n_obj)
approximation = sample_front(front, n_points, shift)
values = compute_all(approximation, front)

metrics = st.columns(len(values))
for column, entry in zip(metrics, available_indicators()):
    arrow = "↑" if entry.maximized else "↓"
    column.metric(f"{entry.short_name} {arrow}", f"{values[entry.key]:.4f}")

figure = go.Figure()
figure.add_trace(
    go.Scatter(
        x=front[:, 0],
        y=front[:, 1],
        mode="markers",
        name="Reference front",
        marker={"size": 3, "color": REFERENCE_COLOUR},
    )
)
figure.add_trace(
    go.Scatter(
        x=approximation[:, 0],
        y=approximation[:, 1],
        mode="markers",
        name="Approximation",
        marker={"size": 8, "color": APPROXIMATION_COLOUR},
    )
)
figure.update_layout(xaxis_title="f1", yaxis_title="f2", legend={"orientation": "h"})
st.plotly_chart(figure, width="stretch")

st.caption(
    f"Reference front: {len(front)} points from {reference_front_source(problem.key)}, the same "
    "file Evolver-Studio uses, so the values match its."
)

with st.expander("Values as a table"):
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Indicator": entry.full_name,
                    "Value": values[entry.key],
                    "Better": "higher" if entry.maximized else "lower",
                }
                for entry in available_indicators()
            ]
        ),
        hide_index=True,
    )
