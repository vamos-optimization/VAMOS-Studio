"""History: every run with its state; open one in the monitor or in the results.

Adapted from Transept's History page (pages/history.py), by the same authors.
"""

import pandas as pd
import streamlit as st

from vamos_studio import ui
from vamos_studio.backend import runs

st.title("History")


def summary_table(candidates: list[runs.SolveRun]) -> pd.DataFrame:
    rows = []
    for run in candidates:
        request = runs.read_request(run)
        status = runs.read_status(run)
        rows.append(
            {
                "Run": run.run_id,
                "State": runs.state(run).value,
                "Problem": request.problem if request else "",
                "Algorithm": request.algorithm if request else "",
                "Budget": request.max_evaluations if request else None,
                "Evaluations": status.evaluations if status else None,
                "Seed": request.seed if request else None,
                "Elapsed (s)": round(status.elapsed_seconds, 1) if status else None,
            }
        )
    return pd.DataFrame(rows)


found = runs.list_runs(runs.runs_directory())
if not found:
    st.info("There are no runs yet.")
    st.page_link(ui.NEW_RUN, label="Launch a run", icon=":material/play_arrow:")
    st.stop()

st.dataframe(summary_table(found), hide_index=True, width="stretch")
st.caption(f"{len(found)} run(s), newest first, in `{runs.runs_directory()}`.")

run = ui.choose_run("Run", found)
state = runs.state(run)
if state.has_results:
    if st.button("Open the results", type="primary", icon=":material/insights:"):
        st.switch_page(ui.RESULTS)
if st.button("Open in the monitor", icon=":material/monitoring:"):
    st.switch_page(ui.MONITOR)
