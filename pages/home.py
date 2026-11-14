"""Home: a panel of the studio, with the VAMOS logo, a first run in one click, recent activity,
news and the way to every page.

What it shows besides the links comes from vamos_studio/home_panel.py.
"""

from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from vamos_studio import ui
from vamos_studio.backend import runs, vamos_version
from vamos_studio.backend.catalogue import (
    algorithm_entries,
    algorithm_label,
    problem_entries,
    problem_entry,
    reference_front,
)
from vamos_studio.branding import LOGO
from vamos_studio.home_panel import (
    Activity,
    RecentRun,
    activity,
    latest_changes,
    quick_start_request,
)
from vamos_studio.sections import SECTIONS, Page, Section

VAMOS_URL = "https://github.com/vamos-optimization/VAMOS"
CHANGELOG = Path(__file__).resolve().parent.parent / "CHANGELOG.md"
HERO_FRONT = ("dtlz2", 3)
GRADIENT = [[0.0, "#2F87E0"], [1.0, "#1BA89A"]]
CARDS_PER_ROW = 3
STATE_BADGES = {
    runs.RunState.STARTING: ("Starting", ":material/hourglass_top:", "blue"),
    runs.RunState.RUNNING: ("Running", ":material/sync:", "blue"),
    runs.RunState.FINISHED: ("Finished", ":material/check_circle:", "green"),
    runs.RunState.STOPPED: ("Stopped", ":material/stop_circle:", "orange"),
    runs.RunState.FAILED: ("Failed", ":material/error:", "red"),
    runs.RunState.CANCELLED: ("Cancelled", ":material/cancel:", "gray"),
    runs.RunState.INTERRUPTED: ("Interrupted", ":material/pause_circle:", "gray"),
}


def hero_figure() -> go.Figure | None:
    """The reference front of DTLZ2 with three objectives, in the logo's colors."""
    front = reference_front(*HERO_FRONT)
    if front is None:
        return None
    front = front[np.argsort(front[:, 2])]
    figure = go.Figure(
        go.Scatter3d(
            x=front[:, 0],
            y=front[:, 1],
            z=front[:, 2],
            mode="markers",
            marker={"size": 2.6, "color": front[:, 2], "colorscale": GRADIENT, "opacity": 0.9},
            hoverinfo="skip",
        )
    )
    axis = {"showbackground": False, "showticklabels": False, "title": "", "gridcolor": "#D6E2EE"}
    figure.update_layout(
        height=330,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        scene={
            "xaxis": axis,
            "yaxis": axis,
            "zaxis": axis,
            "camera": {"eye": {"x": 1.45, "y": 1.45, "z": 0.9}},
        },
        showlegend=False,
    )
    return figure


def launch_quick_start() -> None:
    """Launch NSGA-II on ZDT1 with its defaults, and follow it in the Monitor."""
    ui.select_run(runs.launch(quick_start_request(), runs.runs_directory()))
    st.session_state.pop(ui.SELECTED_SERIES, None)
    st.switch_page(ui.MONITOR)


def render_hero(installed: str | None) -> None:
    text, picture = st.columns([5, 4], vertical_alignment="center")
    with text:
        st.image(LOGO, width=400)
        st.title("Explore, run and analyze")
        st.markdown(
            f"A workbench for [VAMOS]({VAMOS_URL}): explore its algorithms and problems, run them "
            "with a live view of the front, and analyze what they found."
        )
        if installed is None:
            st.error("VAMOS is not installed: install `vamos-optimization` in this environment.")
        else:
            st.caption(
                f"Backend: VAMOS {installed} · {len(algorithm_entries())} algorithms · "
                f"{sum(entry.available for entry in problem_entries())} problems"
            )
        first, second, third = st.columns(3)
        if first.button(
            "Try NSGA-II on ZDT1",
            type="primary",
            icon=":material/rocket_launch:",
            width="stretch",
            help="25,000 evaluations with the default configuration, followed live.",
        ):
            launch_quick_start()
        second.page_link(ui.NEW_RUN, label="New run", icon=":material/tune:", width="stretch")
        third.page_link(
            "pages/explore_problems.py",
            label="Browse problems",
            icon=":material/extension:",
            width="stretch",
        )
    with picture:
        figure = hero_figure()
        if figure is not None:
            st.plotly_chart(figure, config={"displayModeBar": False}, width="stretch")
            st.caption("The Pareto front of DTLZ2 with three objectives (jMetal's reference).")


def render_metrics(summary: Activity) -> None:
    running = summary.by_state.get(runs.RunState.RUNNING, 0) + summary.by_state.get(
        runs.RunState.STARTING, 0
    )
    for column, (label, value) in zip(
        st.columns(4),
        [
            ("Runs", summary.total),
            ("With results", summary.finished),
            ("Running now", running),
            ("Series", summary.series_count),
        ],
    ):
        with column.container(border=True):
            st.metric(label, value)


def render_active(run: runs.SolveRun) -> None:
    request = runs.read_request(run)
    status = runs.read_status(run)
    with st.container(border=True):
        st.markdown("**:material/sync: In progress**")
        if request is not None:
            algorithm = algorithm_label(request.algorithm)
            st.markdown(f"{algorithm} on {_problem_label(request.problem)}")
        if status is not None and status.max_evaluations:
            st.progress(
                min(1.0, status.evaluations / status.max_evaluations),
                text=f"{status.evaluations:,} of {status.max_evaluations:,} evaluations",
            )
        if st.button("Follow it in the Monitor", icon=":material/monitor_heart:"):
            ui.select_run(run)
            st.switch_page(ui.MONITOR)


def render_recent(summary: Activity) -> None:
    st.subheader("Recent runs")
    if summary.active is not None:
        render_active(summary.active)
    if not summary.recent:
        with st.container(border=True):
            st.markdown(
                ":material/lightbulb: No runs yet. **Try NSGA-II on ZDT1** above for a first run, "
                "or open **New run** to choose a problem and an algorithm."
            )
        return
    for recent in summary.recent:
        if summary.active is None or recent.run != summary.active:
            render_recent_run(recent)
    st.page_link(ui.HISTORY, label="All runs", icon=":material/history:")


def render_recent_run(recent: RecentRun) -> None:
    label, icon, color = STATE_BADGES[recent.state]
    with st.container(border=True):
        what, when, action = st.columns([4, 4, 2], vertical_alignment="center")
        with what:
            st.markdown(
                f"**{algorithm_label(recent.algorithm)}** on {_problem_label(recent.problem)}"
            )
            st.badge(label, icon=icon, color=color)
        when.caption(
            (recent.launched.strftime("%d %b %Y, %H:%M") if recent.launched else recent.run.run_id)
            + f" · {recent.evaluations:,} evaluations"
            + (" · in a series" if recent.in_series else "")
        )
        target = ui.RESULTS if recent.state.has_results else ui.MONITOR
        if action.button(
            "Results" if recent.state.has_results else "Monitor",
            key=f"home.open.{recent.run.run_id}",
            icon=":material/insights:" if recent.state.has_results else ":material/monitor_heart:",
            width="stretch",
        ):
            ui.select_run(recent.run)
            st.switch_page(target)


def render_getting_started() -> None:
    st.subheader("Getting started")
    with st.container(border=True):
        steps = [
            ("pages/explore_problems.py", "1 · Pick a problem", ":material/extension:"),
            ("pages/explore_algorithms.py", "2 · Look at an algorithm", ":material/account_tree:"),
            (ui.NEW_RUN, "3 · Launch a run", ":material/play_circle:"),
            (ui.RESULTS, "4 · Analyze its front", ":material/insights:"),
        ]
        for path, label, icon in steps:
            st.page_link(path, label=label, icon=icon)


def render_news() -> None:
    if not CHANGELOG.is_file():
        return
    version, items = latest_changes(CHANGELOG.read_text(encoding="utf-8"), limit=4)
    if not items:
        return
    st.subheader("What's new")
    with st.container(border=True):
        st.caption(f"VAMOS-Studio {version}")
        for lead, _ in items:
            st.markdown(f"- {lead}")


def render_card(section: Section, page: Page) -> None:
    with st.container(border=True, height="stretch"):
        st.caption(section.name.upper())
        st.markdown(f"#### {page.icon} {page.title}")
        if not page.available:
            st.badge("Coming soon", icon=":material/construction:", color="gray")
        st.markdown(page.description)
        st.page_link(page.path, label=f"Open {page.title}", icon=":material/arrow_forward:")


def render_pages() -> None:
    st.subheader("Everything in the studio")
    cards = [(section, page) for section in SECTIONS for page in section.pages]
    for start in range(0, len(cards), CARDS_PER_ROW):
        for column, (section, page) in zip(
            st.columns(CARDS_PER_ROW), cards[start : start + CARDS_PER_ROW]
        ):
            with column:
                render_card(section, page)


def _problem_label(key: str) -> str:
    try:
        return problem_entry(key).label
    except KeyError:
        return key


render_hero(vamos_version())
summary = activity(runs.runs_directory())
render_metrics(summary)
recent, side = st.columns([3, 2], gap="large")
with recent:
    render_recent(summary)
with side:
    render_getting_started()
    render_news()
st.divider()
render_pages()
