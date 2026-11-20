"""Tutorial S3, "Reading a front and its quality indicators": its steps.

Paired with VAMOS's tutorial T07, "Quality and budget": what Pareto fronts look like (on the
reference fronts the studio copies from jMetal), how quality indicators measure an approximation of
one (on approximations built from the reference front itself, as in Explore › Quality indicators),
and how to read them in a run (a prepared run of NSGA-II on DTLZ2 with three objectives). The
values of the interactive steps are computed as you move the sliders; those of the run were
measured with VAMOS 1.5.0 (the same as with 1.2.1 and 1.4.0), and the companion notebook finds the
same.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from vamos_studio import charts
from vamos_studio.backend.catalogue import problem_details
from vamos_studio.backend.indicators import available_indicators, compute_all
from vamos_studio.front_sample import sample_front
from vamos_studio.tutorial_navigation import open_tutorial
from vamos_studio.tutorial_runs import PreparedRun, render_notebook_step, render_prepared_run
from vamos_studio.tutorials import TutorialStep, tutorial, vamos_tutorial_url

KEY_PREFIX = "tutorial_reading_fronts"
# The fronts the first step shows, with what each one illustrates.
SHAPES = {
    "ZDT1": ("zdt1", 2, "convex: it bulges towards the ideal point (0, 0)."),
    "ZDT2": ("zdt2", 2, "concave: it bulges away from the ideal point."),
    "ZDT3": ("zdt3", 2, "disconnected: five separate pieces, and the gaps hold no "
             "Pareto-optimal solution."),
    "DTLZ2": ("dtlz2", 3, "three objectives: the positive eighth of a sphere of radius 1, "
              "which you can rotate."),
}  # fmt: skip
NSGAII_ON_DTLZ2 = PreparedRun(
    "reading_dtlz2", "nsgaii", "dtlz2", n_obj=3, expected={"hv": 0.374549, "igd_plus": 0.039041}
)
BEST_HV_DTLZ2 = 0.4707


def _render_introduction() -> None:
    st.markdown(
        "A solution **dominates** another when it is at least as good in every objective and "
        "better in one. The **Pareto front** is made of the solutions no other dominates: moving "
        "along it, improving one objective always costs another.\n\n"
        "An algorithm returns an **approximation** of that front, and two questions decide how "
        "good it is: **convergence** (how close its points are to the front) and **spread** (how "
        "much of the front they cover, and how evenly). A picture answers both at a glance with "
        "two or three objectives; **quality indicators** answer them with numbers, which is what "
        "you need to compare runs.\n\n"
        "In this tutorial you will look at fronts of different shapes, see how the indicators "
        "respond to approximations you build yourself, and read them in a real run. It pairs "
        f"with VAMOS's tutorial [T07. Quality and budget]({vamos_tutorial_url('T07')})."
    )


def _render_shapes() -> None:
    name = st.radio("Front", list(SHAPES), horizontal=True, key=f"{KEY_PREFIX}_shape")
    key, n_obj, what = SHAPES[name]
    details = problem_details(key, n_obj)
    st.plotly_chart(
        charts.front_figure(None, details.reference_front),
        width="stretch",
        key=f"{KEY_PREFIX}_shape_chart",
    )
    st.markdown(f"The Pareto front of **{name}** is {what}")
    st.caption(
        f"{len(details.reference_front):,} points, from {details.reference_front_source}: the "
        "reference front the studio measures runs against."
    )
    st.markdown(
        "The shape matters: on a concave front some indicators favor different points than on a "
        "convex one, and a disconnected front is easy to cover only in part. With four or more "
        "objectives a front can no longer be drawn as points in space, and the studio draws it in "
        "parallel coordinates instead."
    )


def _render_measuring() -> None:
    st.markdown(
        "Build an approximation of the front of ZDT1 yourself: take some of its points, evenly "
        "spread, and move them away from it by a fraction of each objective's range. Then see how "
        "each indicator responds."
    )
    left, right = st.columns(2)
    n_points = left.slider("Points", 2, 100, 20, key=f"{KEY_PREFIX}_points")
    shift = right.slider(
        "Shift (fraction of each objective's range)",
        0.0,
        0.2,
        0.0,
        step=0.005,
        format="%.3f",
        key=f"{KEY_PREFIX}_shift",
    )
    reference = problem_details("zdt1").reference_front
    approximation = sample_front(reference, n_points, shift)
    values = compute_all(approximation, reference)
    entries = available_indicators()
    columns = st.columns(len(entries))
    for column, entry in zip(columns, entries):
        arrow = "↑" if entry.maximized else "↓"
        column.metric(f"{entry.short_name} {arrow}", f"{values[entry.key]:.4f}")
    st.plotly_chart(
        charts.front_figure(approximation, reference, front_label="Approximation"),
        width="stretch",
        key=f"{KEY_PREFIX}_measuring_chart",
    )
    st.markdown(
        "Try these, one at a time:\n\n"
        "- **Many points, no shift**: the approximation lies on the front. The distance "
        "indicators (IGD, IGD+, EP, Δp) are close to 0 and HV close to its maximum.\n"
        "- **Few points, no shift**: every point is optimal, yet the front is poorly covered. HV "
        "drops and IGD grows: they reward **spread**, not only convergence.\n"
        "- **Many points, shifted**: the front is well covered but every point is worse. All the "
        "indicators get worse: they reward **convergence**.\n\n"
        "↑ marks the indicators where higher is better (HV), ↓ those where lower is."
    )


def _render_indicators() -> None:
    st.markdown(
        "What each indicator measures. All of them compare the front with the **reference "
        "front**, after normalizing the objectives so that the reference front spans [0, 1] in "
        "each one, so that an objective with larger values does not weigh more:"
    )
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Indicator": f"{entry.short_name} ({entry.full_name})",
                    "Better": "higher" if entry.maximized else "lower",
                    "What it measures": entry.measures,
                }
                for entry in available_indicators()
            ]
        ),
        hide_index=True,
        width="stretch",
    )
    st.markdown(
        "In practice, **HV** and **IGD+** are the usual pair: HV needs no reference front, only "
        "a reference point, and is *Pareto compliant* (a front that dominates another always "
        "scores better); IGD+ is cheap and *weakly* compliant. **IGD** is popular but can prefer "
        "a worse front. Explore › Quality indicators has this table, with the works that "
        "introduced each indicator, and the sandbox of the previous step for every problem with "
        "a reference front."
    )
    st.page_link(
        "pages/explore_indicators.py",
        label="Explore the quality indicators",
        icon=":material/straighten:",
    )


def _render_in_a_run() -> None:
    st.markdown(
        "Now read them in a real run: the default **NSGA-II on DTLZ2 with three objectives**, "
        "25,000 evaluations, seed 1. With three objectives the front is drawn in 3D: rotate it "
        "with the mouse."
    )
    render_prepared_run(NSGAII_ON_DTLZ2, "NSGA-II on DTLZ2 with three objectives")
    st.markdown(
        f"The points lie on the sphere, but NSGA-II covers it unevenly: its HV is 0.3745, "
        f"against {BEST_HV_DTLZ2} for the reference front, and its IGD+ 0.0390, ten times its "
        "value on ZDT1. NSGA-II spreads its solutions with the *crowding distance*, which works "
        "well with two objectives and worse with three or more; algorithms built on reference "
        "directions, such as NSGA-III, spread them more evenly.\n\n"
        "In **Results**, the *Indicators* tab computes them when you press *Compute the quality "
        "indicators*: with many objectives the hypervolume can take long, so the studio does not "
        "compute it on every visit. It says what the run is measured against: the exact front "
        "copied from jMetal, an approximate front built from runs, or none."
    )


def _render_python() -> None:
    render_notebook_step(tutorial("reading_fronts"))


def _render_next_steps() -> None:
    st.markdown(
        "- **S4. Exploring a parameter space** shows what each algorithm can be configured "
        "with.\n"
        "- Comparing algorithms with these indicators over many runs, with medians and spreads, "
        "and fronts with many objectives, are the subjects of intermediate tutorials."
    )
    st.button(
        "All the tutorials",
        icon=":material/school:",
        on_click=open_tutorial,
        args=(None,),
        key=f"{KEY_PREFIX}_all_tutorials",
    )


STEPS: tuple[TutorialStep, ...] = (
    TutorialStep("What makes a front good?", _render_introduction),
    TutorialStep("Step 1: shapes of fronts", _render_shapes),
    TutorialStep("Step 2: measuring an approximation", _render_measuring),
    TutorialStep("Step 3: what each indicator measures", _render_indicators),
    TutorialStep("Step 4: the indicators of a run", _render_in_a_run),
    TutorialStep("Do it in Python", _render_python),
    TutorialStep("Where to go next", _render_next_steps),
)
