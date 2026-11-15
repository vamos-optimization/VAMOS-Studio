"""Monitor: follow a run while it is active, stop or cancel it, or see why it did not finish.

Adapted from Transept's Monitor page (pages/monitor.py), by the same authors.
"""

import pandas as pd
import streamlit as st

from vamos_studio import charts, series_view, ui
from vamos_studio.backend import runs, series
from vamos_studio.backend.runs import RunState

REFRESH_SECONDS = 0.5
# The reference front is drawn with at most this many points, so the live view refreshes quickly.
MAX_REFERENCE_POINTS = 2000

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
            ui.open_run(run)
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


def live_front_caption(
    status: runs.RunStatus | None, state: RunState, request: runs.SolveRequest
) -> str:
    """What the live front is: the population's front, the archive, or a subset of it."""
    source = status.live_source if status is not None else "population"
    if source == "archive":
        return "The current external archive (what the run returns)"
    if source != "archive_subset":
        return "The current non-dominated front of the population"
    size = f"{status.archive_size:,}" if status.archive_size is not None else "?"
    method = request.configuration.get("archive_subset_selection", "")
    if state.active and method != "farthest":
        return (
            f"A preview of the result: {request.configuration['pop_size']} of the {size} "
            f"solutions of the unbounded archive, chosen by farthest-point selection (the "
            f"result will use `{method}`)"
        )
    return (
        f"The result: {request.configuration['pop_size']} of the {size} solutions of the "
        f"unbounded archive, chosen by `{method}`"
    )


def show_run(run: runs.SolveRun) -> None:
    state = runs.state(run)
    request = runs.read_request(run)
    status = runs.read_status(run)
    st.subheader(f"{run.run_id}: {state.value}")
    st.caption(
        f"{request.algorithm} on {request.problem} with {ui.variables_of(request)} variables and "
        f"{ui.objectives_of(request)} objectives, seed {request.seed}"
    )
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
    reference, _ = runs.reference_front_of(run)
    if reference is not None and len(reference) > MAX_REFERENCE_POINTS:
        reference = reference[:: -(-len(reference) // MAX_REFERENCE_POINTS)]
    st.plotly_chart(charts.front_figure(front, reference), width="stretch")
    st.caption(f"{live_front_caption(status, state, request)}, in blue, over the reference front.")
    if state.active:
        run_controls(run)
    else:
        show_outcome(run, state)


@st.fragment(run_every=REFRESH_SECONDS)
def live_run(run: runs.SolveRun) -> None:
    show_run(run)
    if not runs.state(run).active:
        st.rerun(scope="app")  # it has just ended: rerun the page, so that it stops refreshing


def member_table(members: list[series.Member]) -> pd.DataFrame:
    """One row per run of a series, with its progress."""
    rows = []
    for member in members:
        status = runs.read_status(member.run) if member.run.directory.is_dir() else None
        rows.append(
            {
                "Seed": member.seed,
                "Run": member.run.run_id,
                "State": member.state,
                "Evaluations": status.evaluations if status else None,
                "Elapsed (s)": round(status.elapsed_seconds, 1) if status else None,
            }
        )
    return pd.DataFrame(rows)


def series_controls(chosen: series.Series) -> None:
    """Stop or cancel a running series."""
    stopping = (chosen.directory / series.STOP_FILE).is_file()
    buttons = st.columns(2)
    if buttons[0].button(
        "Stop and keep the results",
        disabled=stopping,
        key="stop_series",
        help="The runs in progress end at their next generation and keep their results; the "
        "runs not started yet are not launched.",
    ):
        series.stop(chosen)
        st.rerun(scope="app")
    if buttons[1].button(
        "Cancel the runs", key="cancel_series", help="Stops every run and keeps nothing of them."
    ):
        series.cancel(chosen)
        st.rerun(scope="app")
    if stopping:
        st.info("Stopping: the runs in progress are saving their results.")


def show_series_fronts(chosen: series.Series, members: list[series.Member]) -> None:
    """The current front of each run in progress, over the fronts of the finished runs."""
    in_progress = (RunState.STARTING.value, RunState.RUNNING.value)
    active = [runs.live_front(m.run) for m in members if m.state in in_progress]
    active = [front for front in active if front is not None]
    finished = [front for _, front in series.member_fronts(chosen)]
    if not active and not finished:
        st.caption("The fronts appear here as soon as the first runs report them.")
        return
    started = [m.run for m in members if (m.run.directory / runs.REQUEST_FILE).is_file()]
    reference, _ = runs.reference_front_of(started[0])
    if reference is not None and len(reference) > MAX_REFERENCE_POINTS:
        reference = reference[:: -(-len(reference) // MAX_REFERENCE_POINTS)]
    st.plotly_chart(charts.series_live_figure(active, finished, reference), width="stretch")
    st.caption(
        "In blue, the current fronts of the runs in progress; in grey, the results of the runs "
        "already finished; over the reference front."
    )


def show_series(chosen: series.Series) -> None:
    current = series.state(chosen)
    members = series.members(chosen)
    finished = series.finished_members(chosen)
    request = chosen.request
    st.subheader(f"{chosen.series_id}: {current.value}")
    st.caption(
        f"{chosen.count} runs of {request.algorithm} on {request.problem}, seeds "
        f"{chosen.seeds.start} to {chosen.seeds.stop - 1}, {chosen.parallel} at a time"
    )
    st.progress(
        len(finished) / chosen.count, text=f"{len(finished)} of {chosen.count} runs with results"
    )
    show_series_fronts(chosen, members)
    st.dataframe(member_table(members), hide_index=True, width="stretch")
    if current.active:
        series_controls(chosen)
    elif finished:
        if current == series.SeriesState.FINISHED:
            st.success("Every run has finished.")
        else:
            st.warning(f"The series ended {current.value}: {len(finished)} runs have results.")
        if st.button("Open the results of the series", type="primary", icon=":material/insights:"):
            ui.select_series(chosen)
            series_view.show_next(chosen, None)
            st.switch_page(ui.RESULTS)
    else:
        st.warning(f"The series ended {current.value}, with no results.")


@st.fragment(run_every=REFRESH_SECONDS)
def live_series(chosen: series.Series) -> None:
    show_series(chosen)
    if not series.state(chosen).active:
        st.rerun(scope="app")


all_series = series.list_series(runs.runs_directory())
following_series = False
if all_series:
    following_series = (
        st.radio(
            "Follow",
            ["A run", "A series"],
            index=1 if st.session_state.get(ui.SELECTED_SERIES) else 0,
            horizontal=True,
        )
        == "A series"
    )
if following_series:
    chosen = ui.choose_series("Series", all_series)
    if series.state(chosen).active:
        live_series(chosen)
    else:
        show_series(chosen)
    st.stop()

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
