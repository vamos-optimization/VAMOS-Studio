"""Explore problems: VAMOS's problems, by family, with the bounds and reference front of each."""

from collections import defaultdict

import pandas as pd
import streamlit as st

from vamos_studio import charts
from vamos_studio.backend import approximate_fronts, runs
from vamos_studio.backend.catalogue import (
    ENCODING_LABELS,
    family_label,
    format_arguments,
    problem_details,
    problem_entries,
)
from vamos_studio.problem_form import render_problem_arguments

CONFIRM_DELETE = "explore_problems.confirm_delete"


def arguments_text(arguments: dict) -> str:
    return ", ".join(f"{name} = {value}" for name, value in arguments.items())


def show_approximate_fronts(problem) -> None:
    """The approximate fronts of a problem: view them, see their runs, download or delete them."""
    st.markdown(
        "An approximate reference front is the non-dominated union of the runs added to it, kept "
        "for each set of arguments of the problem. Add runs in New run or in Results."
    )
    fronts = approximate_fronts.list_fronts(runs.runs_directory(), problem.key)
    if not fronts:
        st.info(f"{problem.label} has no approximate front yet.")
        return
    labels = {
        index: f"{arguments_text(front.arguments)} · {front.label}"
        for index, front in enumerate(fronts)
    }
    front = fronts[st.selectbox("Approximate front", list(labels), format_func=labels.get)]
    st.plotly_chart(charts.front_figure(None, front.points), width="stretch")
    if front.points.shape[1] == 3:
        st.plotly_chart(charts.projections_figure(None, front.points), width="stretch")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Run": c.run_id,
                    "Algorithm": c.algorithm,
                    "Evaluations": c.evaluations,
                    "Points": c.points,
                    "Version": c.version,
                    "Added": c.added_at,
                }
                for c in front.contributions
            ]
        ),
        hide_index=True,
    )
    st.download_button(
        "Download the front (CSV)",
        "\n".join(",".join(f"{v:.10g}" for v in row) for row in front.points) + "\n",
        file_name=f"{problem.key}-approximate-v{front.version}.csv",
        mime="text/csv",
        icon=":material/download:",
    )
    if st.button("Delete this approximate front…", key="ask_delete_front"):
        st.session_state[CONFIRM_DELETE] = str(front.directory)
    if st.session_state.get(CONFIRM_DELETE) == str(front.directory):
        st.warning(
            "Delete it for good? Runs measured against it keep their copy, but no new run can "
            "use it."
        )
        yes, no = st.columns(2)
        if yes.button("Yes, delete it", type="primary", key="confirm_delete_front"):
            approximate_fronts.delete(front)
            st.session_state[CONFIRM_DELETE] = None
            st.rerun()
        if no.button("Cancel", key="cancel_delete_front"):
            st.session_state[CONFIRM_DELETE] = None
            st.rerun()


st.title("Problems")
st.markdown("The problems of VAMOS, grouped by family.")
st.info(
    "Prototype: the **ZDT** and **DTLZ** families and the binary **knapsack**, **QUBO** and "
    "**feature selection** problems are available, with their arguments (DTLZ with two or three "
    "objectives). The other families are listed but not active yet.",
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
                "Arguments": format_arguments(m.key) if m.available else "",
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
arguments = render_problem_arguments(problem, "explore_problems")
if arguments is None:
    st.stop()
details = problem_details(problem.key, arguments.get("n_obj"), arguments.get("n_var"))
st.subheader(problem.label)
st.markdown(problem.description)
facts = st.columns(3)
facts[0].metric("Variables", details.n_var)
facts[1].metric("Objectives", details.n_obj)
facts[2].metric("Encoding", ENCODING_LABELS.get(problem.encoding, problem.encoding))

bounds_tab, front_tab, approximate_tab = st.tabs(
    ["Bounds", "Reference front", "Approximate fronts"]
)
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
        st.info(
            "There is no reference front for this problem. Runs added to its approximate front "
            "make one: see the Approximate fronts tab."
        )
    else:
        same_as_evolver = (
            ": the same file Evolver and Evolver-Studio use"
            if str(details.reference_front_source).startswith("jMetal")
            else ""
        )
        st.caption(
            f"{len(front)} points, from {details.reference_front_source}{same_as_evolver}. The "
            "studio measures fronts against it."
        )
        st.plotly_chart(charts.front_figure(None, front), width="stretch")
        if details.n_obj == 3:
            st.plotly_chart(charts.projections_figure(None, front), width="stretch")
with approximate_tab:
    show_approximate_fronts(problem)
