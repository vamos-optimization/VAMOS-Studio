"""A series of independent runs in Results: their aggregate, or any of its runs.

As Transept's Results (transept/series_view.py): a series is one entry of the Results selector,
and a second selector shows either the aggregate of its runs (their fronts in grey, their union in
blue, and the indicators of each run with their summary) or one of its runs in detail.
"""

from __future__ import annotations

import streamlit as st

from vamos_studio import charts, on_demand
from vamos_studio.backend import runs, series
from vamos_studio.backend.indicators import available_indicators, compute_all
from vamos_studio.series_summary import best_run, indicator_table, summarize

AGGREGATE = "All runs (aggregate)"


def seed_label(seed: int) -> str:
    """The entry of the run with this seed in the selector of a series."""
    return f"Run with seed {seed}"


def _widget(chosen: series.Series) -> str:
    return f"show:{chosen.series_id}"


def _pending(chosen: series.Series) -> str:
    return f"show_pending:{chosen.series_id}"


def show_next(chosen: series.Series, seed: int | None) -> None:
    """Make the next Results page show the run with `seed`, or the aggregate when it is None."""
    st.session_state[_pending(chosen)] = AGGREGATE if seed is None else seed_label(seed)


def choose_view(chosen: series.Series, remembered: runs.SolveRun | None) -> runs.SolveRun | None:
    """Shows what to see of a series, and the aggregate if that is the choice.

    Args:
        chosen: The series.
        remembered: A run of the series to open at once, if any.

    Returns:
        The run to show in detail; None if the aggregate was shown.
    """
    finished = series.finished_members(chosen)
    if len(finished) < chosen.count:
        st.warning(
            f"{len(finished)} of {chosen.count} runs have results: the others are not shown."
        )
    labels = [AGGREGATE, *[seed_label(member.seed) for member in finished]]
    widget = _widget(chosen)
    pending = st.session_state.pop(_pending(chosen), None)
    if remembered is not None:
        for member in finished:
            if member.run.run_id == remembered.run_id:
                pending = seed_label(member.seed)
    if pending in labels:
        st.session_state[widget] = pending
    if st.session_state.get(widget) not in labels:
        st.session_state[widget] = AGGREGATE
    selected = st.selectbox("Show", labels, key=widget)
    if selected == AGGREGATE:
        _show_aggregate(chosen)
        return None
    return finished[labels.index(selected) - 1].run


def _show_aggregate(chosen: series.Series) -> None:
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
            return
        _show_indicators(chosen, pairs, reference)


def _show_indicators(chosen: series.Series, pairs, reference) -> None:
    entries = available_indicators()
    computed = on_demand.computed(
        f"series:{chosen.series_id}:{len(pairs)}",
        reference.shape[1],
        lambda hv: indicator_table(
            [(m.seed, m.run.run_id, compute_all(front, reference, hv)) for m, front in pairs]
        ),
    )
    if computed is None:
        return
    table, hv = computed
    if (note := on_demand.method_note(hv)) is not None:
        st.caption(note)
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
    seed = next(member.seed for member, _ in pairs if member.run.run_id == best)
    if st.button(f"Open the best run by {labels[indicator]} (seed {seed})"):
        show_next(chosen, seed)
        st.rerun()
