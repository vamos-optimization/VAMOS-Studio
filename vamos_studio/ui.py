"""Helpers shared by the pages: the page paths, and the run remembered between pages.

Adapted from Transept (transept/ui.py), by the same authors.
"""

from __future__ import annotations

import streamlit as st

from vamos_studio.backend import runs

NEW_RUN = "pages/new_run.py"
MONITOR = "pages/monitor.py"
HISTORY = "pages/history.py"
RESULTS = "pages/results.py"

SELECTED_RUN = "selected_run"


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
    what = f"{request.algorithm} on {request.problem}" if request else "no request"
    return f"{run.run_id} · {what} · {runs.state(run).value}"
