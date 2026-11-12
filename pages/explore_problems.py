"""Explore problems: VAMOS's problems, by family, with the bounds and reference front of each."""

from collections import defaultdict

import pandas as pd
import streamlit as st

from vamos_studio import charts
from vamos_studio.backend.catalogue import (
    ENCODING_LABELS,
    family_label,
    problem_details,
    problem_entries,
)

st.title("Problems")
st.markdown("The problems of VAMOS, grouped by family.")
st.info(
    "Prototype: the **ZDT** and **DTLZ** families, for real-coded problems, are available (DTLZ "
    "with two or three objectives). ZDT5 is binary-coded, and the other families are listed but "
    "not active yet.",
    icon=":material/construction:",
)

families: dict[str, list] = defaultdict(list)
for entry in problem_entries():
    families[entry.family].append(entry)

overview = pd.DataFrame(
    [
        {
            "Family": family_label(family),
            "Problems": len(members),
            "Encodings": ", ".join(
                sorted({ENCODING_LABELS.get(m.encoding, m.encoding) for m in members})
            ),
            "Status": "✅ available" if any(m.available for m in members) else "⏳ coming soon",
        }
        for family, members in families.items()
    ]
)
with st.expander(f"All families ({len(families)})", expanded=False):
    st.dataframe(overview, hide_index=True, width="stretch")

active_families = [
    family for family, members in families.items() if any(m.available for m in members)
]
family = st.selectbox("Family", active_families, format_func=family_label)
members = families[family]
st.dataframe(
    pd.DataFrame(
        [
            {
                "Problem": m.label,
                "Encoding": ENCODING_LABELS.get(m.encoding, m.encoding),
                "Variables": m.n_var,
                "Objectives": m.n_obj,
                "Status": "✅ available" if m.available else "⏳ coming soon",
                "Description": m.description,
            }
            for m in members
        ]
    ),
    hide_index=True,
    width="stretch",
)

problem = st.selectbox(
    "Problem", [m for m in members if m.available], format_func=lambda item: item.label
)
n_obj = problem.n_obj
if len(problem.n_obj_options) > 1:
    n_obj = st.radio(
        "Objectives",
        problem.n_obj_options,
        index=problem.n_obj_options.index(problem.n_obj),
        horizontal=True,
        help="VAMOS lets you choose the number of objectives of this problem; the studio offers "
        "those it has reference fronts and charts for.",
    )
details = problem_details(problem.key, n_obj)
st.subheader(problem.label)
st.markdown(problem.description)
facts = st.columns(3)
facts[0].metric("Variables", details.n_var)
facts[1].metric("Objectives", details.n_obj)
facts[2].metric("Encoding", ENCODING_LABELS.get(problem.encoding, problem.encoding))

bounds_tab, front_tab = st.tabs(["Bounds", "Reference front"])
with bounds_tab:
    st.dataframe(
        pd.DataFrame(
            {
                "Variable": [f"x{i + 1}" for i in range(details.n_var)],
                "Lower": details.lower,
                "Upper": details.upper,
            }
        ),
        hide_index=True,
    )
with front_tab:
    front = details.reference_front
    if front is None:
        st.info("There is no reference front for this problem.")
    else:
        st.caption(
            f"{len(front)} points, from {details.reference_front_source}: the same file Evolver "
            "and Evolver-Studio use. The studio measures fronts against it."
        )
        st.plotly_chart(charts.front_figure(None, front), width="stretch")
        if details.n_obj == 3:
            st.plotly_chart(charts.projections_figure(None, front), width="stretch")
