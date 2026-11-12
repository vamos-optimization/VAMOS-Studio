"""Explore problems: VAMOS's problems, by family, with the bounds and reference front of each."""

from collections import defaultdict

import pandas as pd
import plotly.express as px
import streamlit as st

from vamos_studio.backend.catalogue import (
    ENCODING_LABELS,
    family_label,
    problem_details,
    problem_entries,
)

st.title("Problems")
st.markdown("The problems of VAMOS, grouped by family.")
st.info(
    "Prototype: only the **ZDT** family, for real-coded problems, is available. ZDT5 is "
    "binary-coded, and the other families are listed but not active yet.",
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
details = problem_details(problem.key)
st.subheader(problem.label)
st.markdown(problem.description)
facts = st.columns(3)
facts[0].metric("Variables", problem.n_var)
facts[1].metric("Objectives", problem.n_obj)
facts[2].metric("Encoding", ENCODING_LABELS.get(problem.encoding, problem.encoding))

bounds_tab, front_tab = st.tabs(["Bounds", "Reference front"])
with bounds_tab:
    st.dataframe(
        pd.DataFrame(
            {
                "Variable": [f"x{i + 1}" for i in range(problem.n_var)],
                "Lower": details.lower,
                "Upper": details.upper,
            }
        ),
        hide_index=True,
    )
with front_tab:
    front = details.reference_front
    if front is None:
        st.info("VAMOS ships no reference front for this problem.")
    else:
        st.caption(f"{len(front)} points, shipped with VAMOS.")
        figure = px.scatter(x=front[:, 0], y=front[:, 1], labels={"x": "f1", "y": "f2"})
        figure.update_traces(marker={"size": 3})
        st.plotly_chart(figure, width="stretch")
