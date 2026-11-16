"""Home: a panel of the studio, with the VAMOS logo, a first run in one click, the front of the
latest run, recent activity, news and the way to every page.

What it shows besides the links comes from vamos_studio/home_panel.py.
"""

from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from vamos_studio import charts, ui
from vamos_studio.backend import runs, vamos_version
from vamos_studio.backend.catalogue import (
    algorithm_entries,
    algorithm_label,
    problem_entries,
    problem_entry,
    reference_front,
)
from vamos_studio.backend.indicators import available_indicators, compute_all
from vamos_studio.branding import LOGO_CARD
from vamos_studio.home_panel import (
    Activity,
    RecentRun,
    activity,
    latest_changes,
    quick_start_request,
)
from vamos_studio.sections import SECTIONS, Page, Section
from vamos_studio.theme import is_dark
from vamos_studio.tutorials import TUTORIALS

VAMOS_URL = "https://github.com/vamos-optimization/VAMOS"
CHANGELOG = Path(__file__).resolve().parent.parent / "CHANGELOG.md"
HERO_FRONT = ("dtlz2", 3)
GRADIENT = [[0.0, "#2F87E0"], [1.0, "#1BA89A"]]
# The grid of the front of the home page, light or dark as the theme.
GRID_COLOURS = {False: "#D6E2EE", True: "#24364A"}
SECTIONS_PER_ROW = 2
# The sections that are steps of a study, numbered in this order on the home page, as in Transept.
STEPS = ("Explore", "Optimize", "Analyze")
SECTION_ICONS = {
    "Explore": ":material/travel_explore:",
    "Optimize": ":material/rocket_launch:",
    "Analyze": ":material/insights:",
    "Learn": ":material/school:",
}
RECENT_RUNS = 4
HERO_HEIGHT = 330
HERO_REFRESH_SECONDS = 1.0
# The reference front is drawn with at most this many points, as in the Monitor.
MAX_REFERENCE_POINTS = 2000
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
    """The reference front of DTLZ2 with three objectives, in the logo's colors: before any run."""
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
    axis = {
        "showbackground": False,
        "showticklabels": False,
        "title": "",
        "gridcolor": GRID_COLOURS[is_dark()],
    }
    figure.update_layout(
        height=HERO_HEIGHT,
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


def run_figure(front, run: runs.SolveRun) -> go.Figure:
    """A run's front over its reference front, sized for the home page."""
    reference, _ = runs.reference_front_of(run)
    if reference is not None and len(reference) > MAX_REFERENCE_POINTS:
        reference = reference[:: -(-len(reference) // MAX_REFERENCE_POINTS)]
    figure = charts.front_figure(front, reference)
    figure.update_layout(height=HERO_HEIGHT, margin={"l": 0, "r": 0, "t": 10, "b": 0})
    return figure


def describe_run(run: runs.SolveRun) -> str:
    request = runs.read_request(run)
    if request is None:
        return run.run_id
    return f"{algorithm_label(request.algorithm)} on {_problem_label(request.problem)}"


@st.cache_data(show_spinner=False, max_entries=16)
def result_quality(run_directory: str) -> str:
    """HV and IGD+ of a run's result against its reference front, or "" without one.

    Only with two or three objectives, where they take a moment: with more, Results computes them
    on request.
    """
    run = runs.SolveRun(Path(run_directory))
    reference, _ = runs.reference_front_of(run)
    if reference is None or reference.shape[1] > 3:
        return ""
    values = compute_all(runs.result_front(run)[0], reference)
    return f" · HV {values['hv']:.4f} · IGD+ {values['igd_plus']:.4g}"


@st.fragment(run_every=HERO_REFRESH_SECONDS)
def render_live_run(run: runs.SolveRun) -> None:
    """The front of the run in progress, as the Monitor draws it."""
    if not runs.state(run).active:
        st.rerun(scope="app")  # it has just ended: show its result instead
    status = runs.read_status(run)
    st.plotly_chart(
        run_figure(runs.live_front(run), run), config={"displayModeBar": False}, width="stretch"
    )
    progress = (
        f", {status.evaluations:,} of {status.max_evaluations:,} evaluations"
        if status is not None and status.max_evaluations
        else ""
    )
    st.caption(f"In progress: {describe_run(run)}{progress}.")
    if st.button("Follow it in the Monitor", icon=":material/monitor_heart:"):
        ui.open_run(run)
        st.switch_page(ui.MONITOR)


def render_latest_result(run: runs.SolveRun) -> None:
    """The result of the newest run with one, over its reference front."""
    front = runs.result_front(run)[0]
    st.plotly_chart(run_figure(front, run), config={"displayModeBar": False}, width="stretch")
    st.caption(f"Latest result: {describe_run(run)}{result_quality(str(run.directory))}.")
    if st.button("Open it in Results", icon=":material/insights:"):
        ui.open_run(run)
        st.switch_page(ui.RESULTS)


def render_picture(summary: Activity) -> None:
    """The latest run's front, live while it runs; DTLZ2's front before any run."""
    if summary.active is not None:
        render_live_run(summary.active)
        return
    if summary.latest_result is not None:
        render_latest_result(summary.latest_result)
        return
    figure = hero_figure()
    if figure is not None:
        st.plotly_chart(figure, config={"displayModeBar": False}, width="stretch")
        st.caption("The Pareto front of DTLZ2 with three objectives.")


def launch_quick_start() -> None:
    """Launch NSGA-II on ZDT1 with its defaults, and follow it in the Monitor."""
    ui.select_run(runs.launch(quick_start_request(), runs.runs_directory()))
    st.session_state.pop(ui.SELECTED_SERIES, None)
    st.switch_page(ui.MONITOR)


def render_hero(installed: str | None, summary: Activity) -> None:
    text, picture = st.columns([5, 4], vertical_alignment="center")
    with text:
        st.image(LOGO_CARD, width=400)
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
        render_picture(summary)


def render_recent(summary: Activity) -> None:
    """The newest runs, one line each, with a button to open each one."""
    st.subheader("Recent runs")
    with st.container(border=True):
        if not summary.recent:
            st.markdown(
                ":material/lightbulb: No runs yet. **Try NSGA-II on ZDT1** above for a first run, "
                "or open **New run** to choose a problem and an algorithm."
            )
            return
        for recent in summary.recent:
            render_recent_run(recent)
        st.page_link(ui.HISTORY, label="All runs", icon=":material/history:")


def render_recent_run(recent: RecentRun) -> None:
    label, icon, _ = STATE_BADGES[recent.state]
    when = recent.launched.strftime("%d %b, %H:%M") if recent.launched else recent.run.run_id
    what, action = st.columns([6, 1], vertical_alignment="center")
    what.markdown(
        f"{icon} **{algorithm_label(recent.algorithm)}** on {_problem_label(recent.problem)}  \n"
        f":gray[{label} · {when}" + (" · in a series" if recent.in_series else "") + "]"
    )
    has_results = recent.state.has_results
    if action.button(
        "",
        key=f"home.open.{recent.run.run_id}",
        icon=":material/insights:" if has_results else ":material/monitor_heart:",
        help="Open in Results" if has_results else "Open in the Monitor",
        type="tertiary",
    ):
        ui.open_run(recent.run)
        st.switch_page(ui.RESULTS if has_results else ui.MONITOR)


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


def section_state(name: str, summary: Activity) -> str:
    """What a section has now, in a few words, as Transept's home page says it."""
    if name == "Explore":
        problems = sum(entry.available for entry in problem_entries())
        return (
            f"{plural(len(algorithm_entries()), 'algorithm')} · {plural(problems, 'problem')} · "
            f"{plural(len(available_indicators()), 'quality indicator')}"
        )
    if name == "Optimize":
        return (
            f"{running_now(summary)} running · {plural(summary.total, 'run')} · "
            f"{plural(summary.series_count, 'series', 'series')}"
        )
    if name == "Analyze":
        return f"{plural(summary.finished, 'run')} with results"
    written = sum(item.available for item in TUTORIALS)
    return f"{plural(written, 'tutorial')}, with notebooks"


def plural(count: int, noun: str, many: str | None = None) -> str:
    return f"{count:,} {noun if count == 1 else many or noun + 's'}"


def running_now(summary: Activity) -> int:
    return summary.by_state.get(runs.RunState.RUNNING, 0) + summary.by_state.get(
        runs.RunState.STARTING, 0
    )


def render_section(number: int, section: Section, summary: Activity) -> None:
    """A section of the studio: its pages, each a link with what it offers."""
    with st.container(border=True, height="stretch"):
        heading = f"{number} · {section.name}" if section.name in STEPS else section.name
        st.markdown(f"#### {SECTION_ICONS[section.name]} {heading}")
        st.caption(section_state(section.name, summary))
        for page in section.pages:
            render_page(page)


def render_page(page: Page) -> None:
    st.markdown(f"##### {page.icon} {page.title}")
    if not page.available:
        st.badge("Coming soon", icon=":material/construction:", color="gray")
    st.markdown(f":gray[{page.description}]")
    st.page_link(page.path, label=f"Open {page.title}", icon=":material/arrow_forward:")


def render_sections(summary: Activity) -> None:
    """The sections of the studio in a grid: the steps of a study in order, then Learn."""
    st.subheader("Everything in the studio")
    for start in range(0, len(SECTIONS), SECTIONS_PER_ROW):
        row = SECTIONS[start : start + SECTIONS_PER_ROW]
        for column, (number, section) in zip(
            st.columns(SECTIONS_PER_ROW), enumerate(row, start=start + 1)
        ):
            with column:
                render_section(number, section, summary)


def _problem_label(key: str) -> str:
    try:
        return problem_entry(key).label
    except KeyError:
        return key


summary = activity(runs.runs_directory(), limit=RECENT_RUNS)
render_hero(vamos_version(), summary)
pages, side = st.columns([3, 2], gap="large")
with pages:
    render_sections(summary)
with side:
    render_getting_started()
    render_news()
    render_recent(summary)
