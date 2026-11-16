"""Explore › Quality indicators: VAMOS's indicators, what each one measures, and a sandbox."""

import pandas as pd
import streamlit as st

from vamos_studio import charts
from vamos_studio.backend.catalogue import (
    problem_entries,
    reference_front,
    reference_front_source,
)
from vamos_studio.backend.indicators import INDICATORS, available_indicators, compute_all
from vamos_studio.front_sample import sample_front

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
    "Prototype: the indicators that compare whole fronts are available, on the ZDT and DTLZ "
    "problems (two or three objectives). The others are listed with the reason they are not "
    "active yet.",
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
# Only problems with a reference front: the indicators measure fronts against it.
problems = [
    entry
    for entry in problem_entries()
    if entry.available and reference_front(entry.key, entry.n_obj) is not None
]
controls = st.columns([3, 1, 2, 2])
problem = controls[0].selectbox("Problem", problems, format_func=lambda item: item.label)
# Only numbers of objectives with a reference front.
n_obj_options = [n for n in problem.n_obj_options if reference_front(problem.key, n) is not None]
n_obj = controls[1].selectbox(
    "Objectives",
    n_obj_options,
    index=n_obj_options.index(problem.n_obj),
    disabled=len(n_obj_options) == 1,
)
n_points = controls[2].slider("Points", min_value=2, max_value=200, value=20)
shift = controls[3].slider(
    "Shift (fraction of each objective's range)",
    min_value=0.0,
    max_value=0.2,
    value=0.02,
    step=0.005,
    format="%.3f",
)

front = reference_front(problem.key, n_obj)
approximation = sample_front(front, n_points, shift)
values = compute_all(approximation, front)

metrics = st.columns(len(values))
for column, entry in zip(metrics, available_indicators()):
    arrow = "↑" if entry.maximized else "↓"
    column.metric(f"{entry.short_name} {arrow}", f"{values[entry.key]:.4f}")

st.plotly_chart(
    charts.front_figure(approximation, front, front_label="Approximation"), width="stretch"
)
st.caption(
    f"Reference front: {len(front)} points from {reference_front_source(problem.key, n_obj)}, "
    "the same file Evolver-Studio uses, so the values match its."
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
