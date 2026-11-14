"""History: every run with its state; open runs, delete them (to the trash) or restore them.

Adapted from Transept's History page (pages/history.py), by the same authors.
"""

import pandas as pd
import streamlit as st

from vamos_studio import ui
from vamos_studio.backend import runs, series

CONFIRM_DELETE = "history.confirm_delete"
CONFIRM_EMPTY = "history.confirm_empty"
CONFIRM_DELETE_SERIES = "history.confirm_delete_series"

st.title("History")


def summary_table(candidates: list[runs.SolveRun]) -> pd.DataFrame:
    rows = []
    series_of_runs = series.series_of_runs(runs.runs_directory())
    for run in candidates:
        request = runs.read_request(run)
        status = runs.read_status(run)
        rows.append(
            {
                "Run": run.run_id,
                "Series": series_of_runs.get(run.run_id, ""),
                "State": runs.state(run).value,
                "Problem": request.problem if request else "",
                "Variables": ui.variables_of(request) if request else None,
                "Objectives": ui.objectives_of(request) if request else None,
                "Algorithm": request.algorithm if request else "",
                "Budget": request.max_evaluations if request else None,
                "Evaluations": status.evaluations if status else None,
                "Seed": request.seed if request else None,
                "Elapsed (s)": round(status.elapsed_seconds, 1) if status else None,
            }
        )
    return pd.DataFrame(rows)


def open_actions(found: list[runs.SolveRun]) -> None:
    """Open a run in the results or in the monitor."""
    run = ui.choose_run("Run", found)
    if runs.state(run).has_results:
        if st.button("Open the results", type="primary", icon=":material/insights:"):
            st.switch_page(ui.RESULTS)
    if st.button("Open in the monitor", icon=":material/monitoring:"):
        st.switch_page(ui.MONITOR)


def delete(chosen: list[runs.SolveRun]) -> None:
    remembered = ui.selected_run()
    for run in chosen:
        runs.move_to_trash(run)
        if remembered and remembered.run_id == run.run_id:
            st.session_state.pop(ui.SELECTED_RUN, None)
    st.session_state[CONFIRM_DELETE] = None


def delete_actions(found: list[runs.SolveRun]) -> None:
    """Choose runs and move them to the trash, after confirmation."""
    deletable = [run for run in found if not runs.state(run).active]
    active = [run.run_id for run in found if runs.state(run).active]
    by_id = {run.run_id: run for run in deletable}
    chosen = st.multiselect("Runs to delete", list(by_id), placeholder="Choose runs")
    if active:
        st.caption(
            "Active runs cannot be deleted: cancel them in the monitor first ("
            + ", ".join(active)
            + ")."
        )
    if chosen and st.button(f"Delete {len(chosen)} run(s)…", key="ask_delete"):
        st.session_state[CONFIRM_DELETE] = chosen
    pending = st.session_state.get(CONFIRM_DELETE)
    if pending:
        st.warning("Move to the trash: " + ", ".join(pending) + "? They can be restored below.")
        yes, no = st.columns(2)
        if yes.button("Yes, move to the trash", type="primary", key="confirm_delete_yes"):
            delete([by_id[run_id] for run_id in pending if run_id in by_id])
            st.rerun()
        if no.button("Cancel", key="confirm_delete_no"):
            st.session_state[CONFIRM_DELETE] = None
            st.rerun()


def delete_series_actions() -> None:
    """Move every run of a series to the trash, after confirmation."""
    finished = [
        item for item in series.list_series(runs.runs_directory()) if not series.state(item).active
    ]
    if not finished:
        return
    ids = [item.series_id for item in finished]
    chosen_id = st.selectbox("Or every run of a series", [""] + ids, format_func=lambda v: v or "—")
    if not chosen_id:
        return
    chosen = finished[ids.index(chosen_id)]
    if st.button(f"Delete the {chosen.count} runs of {chosen_id}…", key="ask_delete_series"):
        st.session_state[CONFIRM_DELETE_SERIES] = chosen_id
    if st.session_state.get(CONFIRM_DELETE_SERIES) == chosen_id:
        st.warning(f"Move every run of {chosen_id} to the trash? They can be restored below.")
        yes, no = st.columns(2)
        if yes.button("Yes, move them to the trash", type="primary", key="confirm_series_yes"):
            series.move_to_trash(chosen)
            st.session_state[CONFIRM_DELETE_SERIES] = None
            st.rerun()
        if no.button("Cancel", key="confirm_series_no"):
            st.session_state[CONFIRM_DELETE_SERIES] = None
            st.rerun()


def restore(parent, item: runs.TrashedRun) -> None:
    try:
        runs.restore(parent, item)
    except FileExistsError as error:
        st.error(str(error))
    else:
        st.rerun()


def trash_section(parent) -> None:
    """The runs in the trash: restore them, or delete them for good."""
    trashed = runs.list_trash(parent)
    with st.expander(f"Trash ({len(trashed)})"):
        if not trashed:
            st.caption("The trash is empty.")
            return
        for item in trashed:
            left, right = st.columns([4, 1])
            left.write(f"{item.run_id} (deleted {item.deleted_at})")
            if right.button("Restore", key=f"restore:{item.path.name}"):
                restore(parent, item)
        if st.button("Empty the trash…", key="ask_empty"):
            st.session_state[CONFIRM_EMPTY] = True
        if st.session_state.get(CONFIRM_EMPTY):
            st.warning(f"Delete {len(trashed)} run(s) for good? This cannot be undone.")
            yes, no = st.columns(2)
            if yes.button("Yes, empty the trash", type="primary", key="confirm_empty_yes"):
                runs.empty_trash(parent)
                st.session_state[CONFIRM_EMPTY] = False
                st.rerun()
            if no.button("Cancel", key="confirm_empty_no"):
                st.session_state[CONFIRM_EMPTY] = False
                st.rerun()


parent = runs.runs_directory()
found = runs.list_runs(parent)
if found:
    st.dataframe(summary_table(found), hide_index=True, width="stretch")
    st.caption(f"{len(found)} run(s), newest first, in `{parent}`.")
    open_actions(found)
    st.subheader("Delete runs")
    delete_actions(found)
    delete_series_actions()
else:
    st.info("There are no runs yet.")
    st.page_link(ui.NEW_RUN, label="Launch a run", icon=":material/play_arrow:")
trash_section(parent)
