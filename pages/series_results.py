"""Independent runs: the fronts of the runs of a series, their union and their indicators.

As Transept's Results of independent runs: the fronts of the runs in grey, their union in blue,
and the indicators of each run with their summary.
"""

import streamlit as st

from vamos_studio import charts, ui
from vamos_studio.backend import runs, series
from vamos_studio.backend.indicators import available_indicators, compute_all
from vamos_studio.series_summary import best_run, indicator_table, summarize

st.title("Independent runs")

with_results = [
    item for item in series.list_series(runs.runs_directory()) if series.finished_members(item)
]
chosen = ui.choose_series("Series", with_results)
if chosen is None:
    st.info("No series has results yet: launch several independent runs in New run.")
    st.page_link(ui.NEW_RUN, label="Launch a series", icon=":material/play_arrow:")
    st.stop()

pairs = series.member_fronts(chosen)
members = [member for member, _ in pairs]
fronts = [front for _, front in pairs]
aggregate = series.aggregate_front(fronts)
reference, reference_label = runs.reference_front_of(members[0].run)
request = chosen.request
st.caption(
    f"{len(members)} of {chosen.count} runs of {request.algorithm} on {request.problem} with "
    f"results; measured against {reference_label}."
)

front_tab, indicators_tab = st.tabs(["Fronts", "Indicators"])
with front_tab:
    st.plotly_chart(charts.series_figure(fronts, aggregate, reference), width="stretch")
    st.caption(
        f"The fronts of the runs in grey, and their non-dominated union ({len(aggregate):,} "
        "solutions) in blue."
    )
with indicators_tab:
    if reference is None:
        st.info("The series has no reference front, so no indicator is computed.")
        st.stop()
    entries = available_indicators()
    table = indicator_table(
        [(member.seed, member.run.run_id, compute_all(front, reference)) for member, front in pairs]
    )
    keys = [entry.key for entry in entries]
    st.markdown("**Summary**")
    st.dataframe(summarize(table, keys), hide_index=True)
    st.markdown("**Each run**")
    st.dataframe(table, hide_index=True, width="stretch")
    st.download_button(
        "Download the indicators (CSV)",
        table.to_csv(index=False),
        file_name=f"{chosen.series_id}-indicators.csv",
        mime="text/csv",
        icon=":material/download:",
    )
    labels = {entry.key: entry.short_name for entry in entries}
    indicator = st.selectbox("Best run by", keys, format_func=labels.get)
    maximized = next(entry.maximized for entry in entries if entry.key == indicator)
    best = best_run(table, indicator, maximized)
    if st.button(f"Open the best run by {labels[indicator]} ({best}) in Results"):
        ui.select_run(runs.SolveRun(runs.runs_directory() / best))
        st.switch_page(ui.RESULTS)
