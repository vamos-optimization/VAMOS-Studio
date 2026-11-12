"""Results: the front a run found, its quality indicators, its solutions, and how VAMOS ran it.

The structure follows Transept's Results page (pages/results.py): the front with its extremes and
knee, and the details of the run.
"""

import json

import numpy as np
import pandas as pd
import streamlit as st

from vamos_studio import charts, ui
from vamos_studio.backend import runs
from vamos_studio.backend.catalogue import problem_entry, reference_front, reference_front_source
from vamos_studio.backend.indicators import available_indicators, compute_all
from vamos_studio.backend.upstream.vamos_bridge import builtin_space
from vamos_studio.configuration_form import changes
from vamos_studio.front_summary import knee, objective_names, summarize
from vamos_studio.parameter_tree import format_value

st.title("Results")


def csv_of(values: np.ndarray) -> str:
    """Values as comma-separated rows without a header, as jMetal's FUN.csv and VAR.csv."""
    return "\n".join(",".join(f"{value:.10g}" for value in row) for row in values) + "\n"


def show_front(front: np.ndarray, reference: np.ndarray | None, problem: str) -> None:
    table = summarize(front)
    chosen = knee(table)
    st.plotly_chart(charts.front_figure(front, reference, chosen), width="stretch")
    if front.shape[1] == 3:
        st.plotly_chart(charts.projections_figure(front, reference, chosen), width="stretch")
    st.caption(
        f"{len(front)} non-dominated solutions, in blue, over the reference front of {problem}, "
        "in grey; the knee (closest to the ideal point, with each objective scaled over the "
        "front) is the red star."
    )
    marked = table[table["note"] != ""].drop(columns=["distance"])
    st.dataframe(marked, hide_index=True)


def show_indicators(
    front: np.ndarray, reference: np.ndarray | None, problem: str, n_obj: int
) -> None:
    if reference is None:
        st.info("There is no reference front for this problem, so no indicator is computed.")
        return
    values = compute_all(front, reference)
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Indicator": f"{entry.short_name} ({entry.full_name})",
                    "Value": values[entry.key],
                    "Better": "higher" if entry.maximized else "lower",
                }
                for entry in available_indicators()
            ]
        ),
        hide_index=True,
    )
    st.caption(
        f"Measured on the front normalized with the reference front of {problem} "
        f"({reference_front_source(problem, n_obj)}), as in Explore › Quality indicators."
    )


def show_solutions(front: np.ndarray, variables: np.ndarray, run_id: str) -> None:
    names = objective_names(front.shape[1])
    table = pd.DataFrame(front, columns=names)
    is_binary = np.isin(variables, (0, 1)).all()
    for index in range(variables.shape[1]):
        column = variables[:, index]
        table[f"x{index + 1}"] = column.astype(int) if is_binary else column
    st.dataframe(table.sort_values(names[0]), hide_index=True, width="stretch")
    left, right = st.columns(2)
    left.download_button(
        "Download FUN.csv", csv_of(front), file_name=f"FUN-{run_id}.csv", mime="text/csv"
    )
    right.download_button(
        "Download VAR.csv", csv_of(variables), file_name=f"VAR-{run_id}.csv", mime="text/csv"
    )


def show_details(run: runs.SolveRun, request: runs.SolveRequest) -> None:
    manifest = runs.manifest(run) or {}
    outcome = manifest.get("outcome", {})
    facts = st.columns(4)
    facts[0].metric("Evaluations", f"{outcome.get('evaluations', 0):,}")
    facts[1].metric("Generations", outcome.get("generations", "?"))
    facts[2].metric("Runtime", f"{outcome.get('runtime_ms', 0) / 1000:.2f} s")
    facts[3].metric("Seed", request.seed)
    status = runs.read_status(run)
    if request.pause_seconds > 0 and status is not None:
        st.caption(
            f"The runtime includes {status.paused_seconds:.1f} s of pauses for the live view "
            f"({request.pause_seconds:g} s every {request.pause_every} generation(s)); they do not "
            "change the results."
        )
    if runs.state(run) == runs.RunState.STOPPED:
        st.info(f"Stopped at your request, before its budget of {request.max_evaluations:,}.")
    space = builtin_space(request.algorithm, request.encoding)
    configuration = space.configuration(request.configuration)
    changed = changes(configuration)
    st.markdown(
        "**Configuration** — "
        + (
            "the default one."
            if not changed
            else "changed from the default: "
            + ", ".join(f"`{c.name}` = {format_value(c.value)}" for c in changed)
        )
    )
    st.code(configuration.to_cli(), language="bash", wrap_lines=True)
    if st.button("Verify the run artifact", icon=":material/verified:"):
        verification = runs.verify(run)
        message = (
            f"VAMOS verification: {verification.status} (integrity {verification.integrity}, "
            f"replay {verification.replayability})."
        )
        (st.success if verification.status == "succeeded" else st.warning)(message)
        for reason in verification.reasons:
            st.caption(reason)
    with st.expander("How VAMOS ran it (resolved specification)"):
        st.code(json.dumps(manifest.get("resolved_spec", {}), indent=2), language="json")
    st.caption(f"Run artifact: `{run.artifact}`")


candidates = [run for run in runs.list_runs(runs.runs_directory()) if runs.state(run).has_results]
run = ui.choose_run("Run", candidates)
if run is None:
    st.info("No run has results yet.")
    st.page_link(ui.NEW_RUN, label="Launch a run", icon=":material/play_arrow:")
    st.stop()

request = runs.read_request(run)
selection = runs.read_selection(run)
whole = False
if selection is not None:
    st.info(
        f"The run kept every non-dominated solution in an unbounded archive "
        f"({selection.archive_size:,}); its result is the {len(selection.indices)} of them chosen "
        f"by `{selection.method}` subset selection.",
        icon=":material/filter_alt:",
    )
    whole = st.toggle(f"Show the whole archive ({selection.archive_size:,} solutions)")
front, variables = runs.result_front(run, whole=whole)
problem = problem_entry(request.problem)
n_obj = ui.objectives_of(request)
reference = reference_front(problem.key, n_obj)
st.caption(
    f"{request.algorithm} on {problem.label} with {ui.variables_of(request)} variables and "
    f"{n_obj} objectives, seed {request.seed}"
)

front_tab, indicators_tab, solutions_tab, details_tab = st.tabs(
    ["Front", "Indicators", "Solutions", "Details"]
)
with front_tab:
    show_front(front, reference, problem.label)
with indicators_tab:
    show_indicators(front, reference, problem.key, n_obj)
with solutions_tab:
    show_solutions(front, variables, run.run_id)
with details_tab:
    show_details(run, request)
