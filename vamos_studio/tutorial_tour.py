"""Tutorial S1, "A tour of VAMOS-Studio": its steps.

Adapted from Evolver-Studio's tour (evolver_studio/tutorial_tour.py): what the studio does for you,
how it runs VAMOS, what each page is for and where it keeps the runs. It runs nothing: what it says
about VAMOS (its version, its algorithms and problems) is asked to the installed VAMOS, not written
down.
"""

from __future__ import annotations

import streamlit as st

from vamos_studio.backend import runs, vamos_version
from vamos_studio.backend.catalogue import algorithm_entries, problem_entries
from vamos_studio.sections import SECTIONS
from vamos_studio.tutorial_navigation import open_tutorial
from vamos_studio.tutorials import TUTORIALS, VAMOS_TUTORIALS_URL, TutorialStep

VAMOS_URL = "https://vamos-optimization.org/"
KEY_PREFIX = "tutorial_tour"


def _render_introduction() -> None:
    st.markdown(
        "VAMOS-Studio is a graphical workbench for **VAMOS**, a Python framework for "
        "multi-objective optimization: problems with several objectives in conflict, such as cost "
        "and quality, whose answer is not one solution but a set of trade-offs, the *Pareto "
        "front*.\n\n"
        "VAMOS is a library: you use it from Python code. The studio lets you do the usual work "
        "without writing any:\n\n"
        "- **Explore** what VAMOS offers: its algorithms and how each one can be configured, its "
        "problems with their reference fronts, and the quality indicators that measure a front.\n"
        "- **Optimize**: choose a problem and an algorithm, adjust its configuration, launch one "
        "run or a series of independent runs, and follow them live.\n"
        "- **Analyze** what they found: the front, its knee and extremes, its quality, the "
        "solutions, and how VAMOS ran it.\n\n"
        "This tour shows how the studio runs VAMOS, what each page is for and where it keeps "
        "what it produces. The other tutorials go through each use step by step."
    )


def _render_vamos() -> None:
    entries = algorithm_entries()
    problems = problem_entries()
    st.markdown(
        "The studio does not implement any algorithm or problem: it asks the **installed VAMOS** "
        "what it has, and every page offers exactly that. Yours:"
    )
    columns = st.columns(4)
    columns[0].metric("VAMOS", vamos_version() or "not installed")
    columns[1].metric("Algorithms", len(entries))
    columns[2].metric("Problems", len(problems))
    columns[3].metric("In the studio", f"{sum(e.available for e in entries)} algorithms")
    st.markdown(
        "Not every algorithm or problem of VAMOS is available in the studio yet: an algorithm "
        "needs its *parameter space* (tutorial S4) and a problem family needs to be checked with "
        "the studio's pages. The ones that are not are listed as coming soon in Explore.\n\n"
        f"VAMOS has its own [documentation]({VAMOS_URL}), with "
        f"[tutorials]({VAMOS_TUTORIALS_URL}) that do with Python code what these do with the "
        "studio; each tutorial here says which one it pairs with."
    )


def _render_pages() -> None:
    st.markdown(
        "The menu at the top groups the pages by purpose. A typical session goes through them "
        "from left to right: explore, optimize, analyze."
    )
    for section in SECTIONS:
        with st.container(border=True):
            st.markdown(f"**{section.name}**")
            for page in section.pages:
                st.page_link(page.path, label=f"{page.title} — {page.description}", icon=page.icon)
    st.markdown(
        "Pages hand their result to the next one: **New run** opens the **Monitor** on the run "
        "it launches, the Monitor opens it in **Results** when it ends, and **History** opens any "
        "run in either."
    )


def _render_runs() -> None:
    st.markdown(
        "The studio never runs an algorithm inside the page you are looking at. **New run** "
        "writes a *request* (the problem, the algorithm, its configuration, the budget and the "
        "seed) and starts a **separate process** that runs VAMOS with it. That process keeps a "
        "*status* up to date (how many evaluations, the current front), which the Monitor reads, "
        "and when it ends it saves VAMOS's *run artifact*.\n\n"
        "That is why a run keeps going when you leave its page or close the tab, and why you find "
        "it again in History when you come back. To end one before its budget, the Monitor can "
        "**stop** it, keeping what it found, or **cancel** it.\n\n"
        f"Everything stays in `{runs.runs_directory()}`, one folder per run, readable with any "
        "tool: the request, the status, the log, the front, and VAMOS's artifact, which VAMOS "
        "itself can verify and load."
    )


def _render_python() -> None:
    st.markdown(
        "VAMOS-Studio is written in Python, as VAMOS is. Each tutorial that runs something "
        "ends with a **Jupyter notebook** that does the same with VAMOS's Python API: the step "
        "*Do it in Python* lets you download it and shows its code. The runs are fixed by a "
        "seed, so the notebook finds the same front and the same values as the tutorial.\n\n"
        "That makes the studio a way into VAMOS as a library: try something here, then take the "
        "notebook as the starting point of your own scripts or experiments."
    )


def _render_next_steps() -> None:
    following = "\n".join(
        f"- **{t.label}**: {t.summary}" for t in TUTORIALS if t.available and t.slug != "tour"
    )
    st.markdown(
        "**Where to go next**, in the order the tutorials build on each other:\n\n"
        + following
        + "\n\nThe tutorials still to be written are listed in the catalogue without a number."
    )
    st.button(
        "All the tutorials",
        icon=":material/school:",
        on_click=open_tutorial,
        args=(None,),
        key=f"{KEY_PREFIX}_all_tutorials",
    )


STEPS: tuple[TutorialStep, ...] = (
    TutorialStep("What is VAMOS-Studio?", _render_introduction),
    TutorialStep("Step 1: VAMOS behind the studio", _render_vamos),
    TutorialStep("Step 2: the pages", _render_pages),
    TutorialStep("Step 3: how a run works", _render_runs),
    TutorialStep("Step 4: Python and notebooks", _render_python),
    TutorialStep("Where to go next", _render_next_steps),
)
