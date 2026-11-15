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

SELECTED_RUN = "selected_run"
SELECTED_SERIES = "selected_series"


def select_run(run: runs.SolveRun) -> None:
    """Remember a run, so that the next page opens it."""
    st.session_state[SELECTED_RUN] = run.run_id


def open_run(run: runs.SolveRun) -> None:
    """Remember a run to open by itself: the next page forgets the remembered series."""
    select_run(run)
    st.session_state.pop(SELECTED_SERIES, None)


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


def runs_and_series(
    candidates: list[runs.SolveRun], all_series: list[series.Series]
) -> list[runs.SolveRun | series.Series]:
    """One entry per run that is not in a series, and one per series, in the order of `candidates`.

    A series takes the place of its first run among `candidates`; a series with none of its runs
    among them is left out.
    """
    owner = {item.run_id(seed): item for item in all_series for seed in item.seeds}
    entries: list[runs.SolveRun | series.Series] = []
    added: set[str] = set()
    for run in candidates:
        item = owner.get(run.run_id)
        if item is None:
            entries.append(run)
        elif item.series_id not in added:
            added.add(item.series_id)
            entries.append(item)
    return entries


def choose_run_or_series(
    label: str, candidates: list[runs.SolveRun], all_series: list[series.Series]
) -> runs.SolveRun | series.Series | None:
    """A selector with one entry per single run or series (see `runs_and_series`).

    It starts at the remembered series, or else at the remembered run or its series, and
    remembers the choice.
    """
    entries = runs_and_series(candidates, all_series)
    if not entries:
        return None
    owner = {item.run_id(seed): item.series_id for item in all_series for seed in item.seeds}
    wanted = st.session_state.get(SELECTED_SERIES)
    remembered = selected_run()
    if not wanted and remembered is not None:
        wanted = owner.get(remembered.run_id, remembered.run_id)
    keys = [_key(entry) for entry in entries]
    chosen = entries[
        st.selectbox(
            label,
            range(len(entries)),
            index=keys.index(wanted) if wanted in keys else 0,
            format_func=lambda i: _describe_entry(entries[i]),
        )
    ]
    if isinstance(chosen, series.Series):
        select_series(chosen)
    else:
        open_run(chosen)
    return chosen


def _key(entry: runs.SolveRun | series.Series) -> str:
    return entry.series_id if isinstance(entry, series.Series) else entry.run_id


def _describe_entry(entry: runs.SolveRun | series.Series) -> str:
    return describe_series(entry) if isinstance(entry, series.Series) else describe(entry)
