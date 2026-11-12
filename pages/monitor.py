"""Monitor: follow a run while it is active, stop or cancel it, or see why it did not finish.

Adapted from Transept's Monitor page (pages/monitor.py), by the same authors.
"""

import streamlit as st

from vamos_studio import charts, ui
from vamos_studio.backend import runs
from vamos_studio.backend.catalogue import problem_entry, reference_front
from vamos_studio.backend.runs import RunState

REFRESH_SECONDS = 0.5

st.title("Monitor")


def run_controls(run: runs.SolveRun) -> None:
    """Stop or cancel an active run."""
    stopping = runs.stop_requested(run)
    buttons = st.columns(2)
    if buttons[0].button(
        "Stop and keep the results",
        disabled=stopping,
        help="The run ends at its next generation and keeps the solutions found so far.",
    ):
        runs.request_stop(run)
        st.rerun(scope="app")
    if buttons[1].button("Cancel the run", help="Ends the run now and keeps nothing of it."):
        runs.cancel(run)
        st.rerun(scope="app")
    if stopping:
        st.info("Stopping: the run is saving its results.")


def show_outcome(run: runs.SolveRun, state: RunState) -> None:
    """What happened to a run that is no longer active."""
    if state.has_results:
        if state == RunState.FINISHED:
            st.success("The run has finished.")
        else:
            st.info("Stopped at your request: the results are what it found until then.")
        if st.button("Open the results", type="primary", icon=":material/insights:"):
            ui.select_run(run)
            st.switch_page(ui.RESULTS)
        return
    status = runs.read_status(run)
    if state == RunState.FAILED:
        st.error(f"The run failed: {status.error if status else 'no details'}")
    elif state == RunState.CANCELLED:
        st.warning("The run was cancelled.")
    elif state == RunState.INTERRUPTED:
        st.warning("The run's process ended without saving its results.")
    log = runs.log_tail(run)
    if log:
        with st.expander("Worker log"):
            st.code(log, language=None)


def show_run(run: runs.SolveRun) -> None:
    state = runs.state(run)
    request = runs.read_request(run)
    status = runs.read_status(run)
    st.subheader(f"{run.run_id}: {state.value}")
    st.caption(f"{request.algorithm} on {request.problem}, seed {request.seed}")
    if request.pause_seconds > 0:
        st.caption(
            f"Slowed down for the live view: a pause of {request.pause_seconds:g} s every "
            f"{request.pause_every} generation(s)."
        )
    if status is not None:
        st.progress(
            status.fraction_done,
            text=f"{status.evaluations:,} of {status.max_evaluations:,} evaluations",
        )
        metrics = st.columns(3)
        metrics[0].metric("Generation", status.generation)
        metrics[1].metric("Evaluations", f"{status.evaluations:,}")
        metrics[2].metric("Elapsed", f"{status.elapsed_seconds:.1f} s")
    front = runs.live_front(run)
    reference = reference_front(request.problem, problem_entry(request.problem).n_obj)
    st.plotly_chart(charts.front_figure(front, reference), width="stretch")
    st.caption("The current non-dominated front, in blue, over the reference front, in grey.")
    if state.active:
        run_controls(run)
    else:
        show_outcome(run, state)


@st.fragment(run_every=REFRESH_SECONDS)
def live_run(run: runs.SolveRun) -> None:
    show_run(run)
    if not runs.state(run).active:
        st.rerun(scope="app")  # it has just ended: rerun the page, so that it stops refreshing


candidates = runs.list_runs(runs.runs_directory())
run = ui.choose_run("Run", candidates)
if run is None:
    st.info("There are no runs yet.")
    st.page_link(ui.NEW_RUN, label="Launch a run", icon=":material/play_arrow:")
    st.stop()
if runs.state(run).active:
    live_run(run)
else:
    show_run(run)
