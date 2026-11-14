"""Helpers shared by the pages: the page paths, and the run remembered between pages.

Adapted from Transept (transept/ui.py), by the same authors.
"""

from __future__ import annotations

import streamlit as st

from vamos_studio.backend import runs, series
from vamos_studio.backend.catalogue import problem_details, problem_entry

NEW_RUN = "pages/new_run.py"
MONITOR = "pages/monitor.py"
HISTORY = "pages/history.py"
RESULTS = "pages/results.py"
SERIES_RESULTS = "pages/series_results.py"

SELECTED_RUN = "selected_run"
SELECTED_SERIES = "selected_series"


def select_run(run: runs.SolveRun) -> None:
    """Remember a run, so that the next page opens it."""
    st.session_state[SELECTED_RUN] = run.run_id


def selected_run() -> runs.SolveRun | None:
    """The remembered run, if it still exists."""
    run_id = st.session_state.get(SELECTED_RUN)
    if not run_id:
        return None
    run = runs.SolveRun(runs.runs_directory() / run_id)
    return run if run.directory.is_dir() else None


def choose_run(label: str, candidates: list[runs.SolveRun]) -> runs.SolveRun | None:
    """A selector of runs, starting at the remembered one; remembers the choice."""
    if not candidates:
        return None
    remembered = selected_run()
    ids = [run.run_id for run in candidates]
    index = ids.index(remembered.run_id) if remembered and remembered.run_id in ids else 0
    chosen = candidates[
        st.selectbox(
            label,
            range(len(candidates)),
            index=index,
            format_func=lambda i: describe(candidates[i]),
        )
    ]
    select_run(chosen)
    return chosen


def describe(run: runs.SolveRun) -> str:
    """A run in one line: its id, problem, algorithm and state."""
    request = runs.read_request(run)
    what = (
        f"{request.algorithm} on {request.problem} ({objectives_of(request)} obj.)"
        if request
        else "no request"
    )
    return f"{run.run_id} · {what} · {runs.state(run).value}"


def objectives_of(request: runs.SolveRequest) -> int:
    """The number of objectives of a run: the one it asked for, or its problem's default."""
    return request.n_obj or problem_entry(request.problem).n_obj


def variables_of(request: runs.SolveRequest) -> int:
    """The number of variables of a run: the one it asked for, or its problem's."""
    if request.n_var is not None:
        return request.n_var
    return problem_details(request.problem, objectives_of(request)).n_var


def select_series(chosen: series.Series) -> None:
    """Remember a series, so that the next page opens it."""
    st.session_state[SELECTED_SERIES] = chosen.series_id


def choose_series(label: str, candidates: list[series.Series]) -> series.Series | None:
    """A selector of series, starting at the remembered one; remembers the choice."""
    if not candidates:
        return None
    remembered = st.session_state.get(SELECTED_SERIES)
    ids = [item.series_id for item in candidates]
    index = ids.index(remembered) if remembered in ids else 0
    chosen = candidates[
        st.selectbox(
            label,
            range(len(candidates)),
            index=index,
            format_func=lambda i: describe_series(candidates[i]),
        )
    ]
    select_series(chosen)
    return chosen


def describe_series(chosen: series.Series) -> str:
    """A series in one line: its id, runs, problem, algorithm and state."""
    request = chosen.request
    return (
        f"{chosen.series_id} · {chosen.count} runs of {request.algorithm} on {request.problem} · "
        f"{series.state(chosen).value}"
    )
