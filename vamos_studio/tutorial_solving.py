"""Tutorial S2, "Solving a problem": its steps.

Adapted from Evolver-Studio's tutorial "Solving a problem with a configurable algorithm"
(evolver_studio/tutorial_solving.py), and paired with VAMOS's tutorial T01, "Your first result":
choose a problem, run NSGA-II with its default configuration, read the result, change the
configuration, try a harder problem, then do it by hand in New run. Every run is a *prepared run*
(vamos_studio/tutorial_runs.py), fixed by a seed; the values the text announces were measured with
VAMOS 1.4.0 (the same as with 1.2.1), and the companion notebook
(vamos_studio/notebooks/s2_solving.ipynb) finds the same.
"""

from __future__ import annotations

import streamlit as st

from vamos_studio import charts, ui
from vamos_studio.backend.catalogue import problem_details
from vamos_studio.tutorial_navigation import open_tutorial
from vamos_studio.tutorial_runs import PreparedRun, render_notebook_step, render_prepared_run
from vamos_studio.tutorials import TutorialStep, tutorial, vamos_tutorial_url

KEY_PREFIX = "tutorial_solving"
# The hypervolume of the reference front of ZDT1 and ZDT4, normalized as the studio does: the
# largest a run can reach.
BEST_HV_ZDT1 = 0.6662

DEFAULT_ON_ZDT1 = PreparedRun(
    "solving_default", "nsgaii", "zdt1", expected={"hv": 0.659335, "igd_plus": 0.003838}
)
OTHER_ON_ZDT1 = PreparedRun(
    "solving_other",
    "nsgaii",
    "zdt1",
    {"pop_size": 50, "crossover": "blx_alpha"},
    expected={"hv": 0.649468, "igd_plus": 0.009053},
)
ZDT4_SHORT = PreparedRun(
    "solving_zdt4_short",
    "nsgaii",
    "zdt4",
    max_evaluations=10000,
    expected={"hv": 0.0, "igd_plus": 0.827036},
)
ZDT4_LONG = PreparedRun(
    "solving_zdt4_long", "nsgaii", "zdt4", expected={"hv": 0.656612, "igd_plus": 0.005448}
)


def _render_introduction() -> None:
    st.markdown(
        "A multi-objective problem asks for solutions that are good in several objectives at "
        "once, objectives that conflict: improving one makes another worse. There is no single "
        "best solution, but a set of **trade-offs** none of which is better than another in "
        "every objective: the **Pareto front**.\n\n"
        "An algorithm such as **NSGA-II** does not compute that front: it searches for a good "
        "*approximation* of it, a set of solutions as close to the front and as spread along it "
        "as it can find within its budget of evaluations. *Solving* a problem means running an "
        "algorithm on it and judging how good that approximation is.\n\n"
        "In this tutorial you will run NSGA-II on a classic problem, read what it found, change "
        "its configuration, try a harder problem, and then do the same yourself in **New run**. "
        "Each run is launched from the tutorial with a button and takes a few seconds. It pairs "
        f"with VAMOS's tutorial [T01. Your first result]({vamos_tutorial_url('T01')}), which does "
        "the same with Python code."
    )


def _render_problem() -> None:
    details = problem_details("zdt1")
    st.markdown(
        f"**ZDT1** has **{details.n_var} variables**, each between {details.lower[0]:g} and "
        f"{details.upper[0]:g}, and **{details.n_obj} objectives** to minimize, f1 and f2. Its "
        "Pareto front is known exactly: the curve f2 = 1 − √f1, for f1 between 0 and 1. The "
        "studio uses a sample of it, the *reference front*, to draw the front and to measure how "
        "close a run gets:"
    )
    st.plotly_chart(
        charts.front_figure(None, details.reference_front),
        width="stretch",
        key=f"{KEY_PREFIX}_zdt1",
    )
    st.caption(
        f"The reference front of ZDT1: {len(details.reference_front):,} points, from "
        f"{details.reference_front_source}."
    )
    st.markdown(
        "ZDT1 is *easy*: its front is convex and continuous, and the search space has no traps. "
        "Explore › Problems shows this and every other problem of the studio."
    )
    st.page_link(
        "pages/explore_problems.py", label="Explore the problems", icon=":material/extension:"
    )


def _render_default_run() -> None:
    st.markdown(
        "NSGA-II keeps a **population** of solutions and improves it generation after generation: "
        "it picks parents by binary tournament, combines them with **SBX crossover** "
        "(probability 0.9) and changes them with **polynomial mutation** (each variable with "
        "probability 1/30 here), and keeps the best of parents and children by Pareto rank and "
        "crowding distance. Those are its defaults in VAMOS, with a population of 100.\n\n"
        "Run it with a budget of **25,000 evaluations** and the **seed 1**, which fixes its "
        "random choices so that the result is always the same:"
    )
    render_prepared_run(DEFAULT_ON_ZDT1, "NSGA-II on ZDT1")


def _render_results() -> None:
    st.markdown(
        "The chart of the previous step is the essence of a result: the **front found**, in "
        "blue, over the reference front, in grey. The blue points lie on the grey curve and "
        "cover all of it: NSGA-II has solved ZDT1. The red star is the **knee**, the solution "
        "closest to the ideal point, a natural candidate when one solution must be chosen.\n\n"
        "Two **quality indicators** turn that picture into numbers (tutorial S3 explains them):\n\n"
        f"- **HV**, the hypervolume, measures the region the front dominates: *higher is "
        f"better*. With the objectives normalized by the reference front, the reference front "
        f"itself reaches {BEST_HV_ZDT1}; NSGA-II's 0.6593 is close to it.\n"
        "- **IGD+** measures how far the reference front is from the points found: *lower is "
        "better*, 0 is perfect; 0.0038 is very small.\n\n"
        "**Results** shows all of a run: the front with its knee and extremes, the indicators "
        "(computed when you ask), the **solutions** with their variables, to download as "
        "`FUN.csv` and `VAR.csv`, and the **details**: the configuration, the evaluations, the "
        "time, and the specification VAMOS resolved. Open the run of the previous step there with "
        "its *Open it in Results* button."
    )


def _render_other_configuration() -> None:
    st.markdown(
        "Every algorithm can be configured: its population, its operators and their "
        "parameters (tutorial S4 shows all of NSGA-II's). Change two things: a **population of "
        "50** instead of 100, and **BLX-α crossover** instead of SBX. Everything else, the "
        "budget and the seed included, stays the same:"
    )
    render_prepared_run(OTHER_ON_ZDT1, "NSGA-II with a population of 50 and BLX-α on ZDT1")
    st.markdown(
        "It still finds the front, with half as many points, but it is a little worse by both "
        "indicators (HV 0.6495 against 0.6593, IGD+ 0.0091 against 0.0038). Careful with the "
        "conclusion: this is **one run** of each, with one seed. Whether one configuration is "
        "really better than another takes several runs of each with different seeds, which New "
        "run launches as a *series of independent runs*."
    )


def _render_harder_problem() -> None:
    st.markdown(
        "**ZDT4** has the same Pareto front as ZDT1, but its search space is full of traps: "
        "about 21⁹ **local fronts**, parallel to the true one, where an algorithm can get stuck. "
        "Run the default NSGA-II on it with **10,000 evaluations**:"
    )
    render_prepared_run(ZDT4_SHORT, "NSGA-II on ZDT4, 10,000 evaluations")
    st.markdown(
        "The front found lies far above the reference front: NSGA-II is still on a local front. "
        "Its HV is 0 (it dominates none of the normalized region) and its IGD+ 0.83. Now give it "
        "the **25,000 evaluations** it had for ZDT1:"
    )
    render_prepared_run(ZDT4_LONG, "NSGA-II on ZDT4, 25,000 evaluations")
    st.markdown(
        "This time it escapes the local fronts and reaches the true one (HV 0.6566, IGD+ "
        "0.0054). The lesson: whether a problem is solved depends on the algorithm, its "
        "configuration **and its budget**, and a picture of the front tells at once whether a run "
        "got there."
    )


def _render_your_turn() -> None:
    st.markdown(
        "Now do it yourself, in **Optimize › New run**:\n\n"
        "1. In **1. Problem**, choose **ZDT4**.\n"
        "2. In **2. Algorithm**, keep **NSGA-II**. **3. Configuration** shows its default "
        "configuration, which you can change.\n"
        "3. In **4. Budget**, set **Evaluations** to 15000 and keep the **Seed**.\n"
        "4. Open **Live view** and tick *Slow the run down to watch the front converge*: the run "
        "pauses now and then so that you can see the front move.\n"
        "5. Press **Launch the run**. The **Monitor** follows it; when it ends, *Open the "
        "results* takes you to **Results**.\n\n"
        "Will 15,000 evaluations be enough to escape the local fronts? Try other budgets, seeds "
        "or algorithms: each run stays in **History**."
    )
    st.page_link(ui.NEW_RUN, label="Open New run", icon=":material/tune:")


def _render_python() -> None:
    render_notebook_step(tutorial("solving"))


def _render_next_steps() -> None:
    st.markdown(
        "- **S3. Reading a front and its quality indicators** explains what HV, IGD+ and the "
        "other indicators measure, and how to read them.\n"
        "- **S4. Exploring a parameter space** shows everything NSGA-II and the other algorithms "
        "can be configured with.\n"
        "- Comparing configurations or algorithms properly, with series of independent runs, is "
        "the subject of an intermediate tutorial."
    )
    st.button(
        "All the tutorials",
        icon=":material/school:",
        on_click=open_tutorial,
        args=(None,),
        key=f"{KEY_PREFIX}_all_tutorials",
    )


STEPS: tuple[TutorialStep, ...] = (
    TutorialStep("What does it mean to solve a problem?", _render_introduction),
    TutorialStep("Step 1: the problem, ZDT1", _render_problem),
    TutorialStep("Step 2: NSGA-II with its default configuration", _render_default_run),
    TutorialStep("Step 3: reading the result", _render_results),
    TutorialStep("Step 4: another configuration", _render_other_configuration),
    TutorialStep("Step 5: a harder problem, ZDT4", _render_harder_problem),
    TutorialStep("Step 6: your turn, in New run", _render_your_turn),
    TutorialStep("Do it in Python", _render_python),
    TutorialStep("Where to go next", _render_next_steps),
)
