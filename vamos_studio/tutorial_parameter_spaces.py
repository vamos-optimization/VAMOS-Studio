"""Tutorial S4, "Exploring a parameter space": its steps.

Adapted from Evolver-Studio's tutorial of the same name
(evolver_studio/tutorial_parameter_spaces.py), the interactive counterpart of Evolver's tutorial
E1: the same concepts, on the studio's grammar of
NSGA-II for real-coded problems (docs/design/parameter-spaces.md), read as Explore › Algorithms
shows it. It runs nothing; the companion notebook builds the same configurations with VAMOS's
configuration builders and runs them.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from vamos_studio.backend.catalogue import algorithm_label
from vamos_studio.backend.upstream.vamos_bridge import BUILTIN_SPACES, builtin_space
from vamos_studio.configuration_form import active_fields, changes, configuration_of
from vamos_studio.parameter_tree import format_value, summarize, tree_markdown
from vamos_studio.tutorial_navigation import open_tutorial
from vamos_studio.tutorial_runs import render_notebook_step
from vamos_studio.tutorials import TutorialStep, tutorial

KEY_PREFIX = "tutorial_parameter_spaces"


def _space():
    space = builtin_space("nsgaii", "real")
    if space is None:  # pragma: no cover - the grammar ships with the studio
        raise LookupError("The NSGA-II grammar for real-coded problems is missing.")
    return space


def _render_introduction() -> None:
    st.markdown(
        "An algorithm such as NSGA-II is not one fixed procedure: it is a template with "
        "choices. Which crossover and which mutation, how parents are selected, how many "
        "children each generation, whether an external archive keeps the best solutions found… "
        "and each choice has its own settings.\n\n"
        "A **parameter space** describes all those choices: every parameter, its type and range, "
        "its default value, and **which parameters depend on which**. Choosing a value for every "
        "parameter that applies gives a **configuration**, a concrete variant of the algorithm "
        "that can be run. The studio's spaces follow the model of Evolver, a framework of the "
        "same authors: a *grammar*, in which a categorical parameter chooses a value and each "
        "value brings its own parameters.\n\n"
        "In this tutorial you will read the parameter space of NSGA-II, see which parameters "
        "each choice activates, write a configuration as a command line, and compare the spaces "
        "of the other algorithms."
    )


def _render_tree() -> None:
    space = _space()
    summary = summarize(space)
    columns = st.columns(4)
    columns[0].metric("Parameters", summary.parameters)
    columns[1].metric("Top level", summary.top_level)
    columns[2].metric("Active by default", summary.default_active)
    columns[3].metric("Depth", summary.depth)
    st.markdown(
        f"The space of NSGA-II for real-coded problems has **{summary.parameters} parameters**, "
        f"but only **{summary.top_level}** at the top level: the rest hang from a choice. Its "
        f"default configuration uses **{summary.default_active}** of them. Here is the tree, "
        "each parameter with its domain and default value:"
    )
    with st.container(border=True, height=420):
        st.markdown(tree_markdown(space))
    st.markdown(
        "For instance, **crossover** chooses one of several operators, and each one has its own "
        "settings: `crossover_eta` belongs to SBX, `crossover_alpha` to BLX-α. A parameter such "
        "as `crossover_prob`, shared by every crossover, is a *global* sub-parameter of "
        "crossover. Explore › Algorithms shows this tree for every algorithm and encoding, with "
        "a table of the parameters and the grammar as YAML."
    )
    st.page_link(
        "pages/explore_algorithms.py",
        label="Explore the algorithms",
        icon=":material/account_tree:",
    )


def _render_choices() -> None:
    space = _space()
    defaults = space.default_values()
    st.markdown(
        "Choose a crossover and a mutation, and see which parameters become active. The count "
        "tells how many parameters the configuration uses in all."
    )
    left, right = st.columns(2)
    crossover = left.selectbox(
        "Crossover",
        space.parameter("crossover").values,
        index=space.parameter("crossover").values.index(defaults["crossover"]),
        key=f"{KEY_PREFIX}_crossover",
    )
    mutation = right.selectbox(
        "Mutation",
        space.parameter("mutation").values,
        index=space.parameter("mutation").values.index(defaults["mutation"]),
        key=f"{KEY_PREFIX}_mutation",
    )
    values = defaults | {"crossover": crossover, "mutation": mutation}
    values = configuration_of(space, values).values
    for column, (name, choice) in zip(
        (left, right), (("crossover", crossover), ("mutation", mutation))
    ):
        children = space.parameter(name).active_children(choice)
        lines = [
            f"- `{child.name}` = {format_value(values[child.name])}"
            for child in children
            if child.name in values
        ]
        column.markdown(
            f"**{choice}** activates:\n\n" + ("\n".join(lines) if lines else "- nothing else")
        )
    st.metric(
        "Active parameters", f"{len(active_fields(space, values))} of {len(space.all_parameters())}"
    )
    st.markdown(
        "This is what **New run** does in its section *3. Configuration*: it shows only the "
        "parameters the current choices activate, and changing a choice brings in its own."
    )


def _render_command_line() -> None:
    space = _space()
    st.markdown(
        "A configuration can be written as a **command line**: one `--parameter value` per "
        "active parameter. It is how Evolver and irace write configurations, and the studio shows "
        "it for every run, in New run and in the details of Results. Change a few values:"
    )
    left, middle, right = st.columns(3)
    pop_size = left.number_input(
        "Population size", 20, 200, 100, step=10, key=f"{KEY_PREFIX}_pop_size"
    )
    crossover = middle.selectbox(
        "Crossover", space.parameter("crossover").values, key=f"{KEY_PREFIX}_cli_crossover"
    )
    archive = right.selectbox(
        "External archive",
        space.parameter("external_archive").values,
        key=f"{KEY_PREFIX}_cli_archive",
    )
    configuration = configuration_of(
        space,
        space.default_values()
        | {"pop_size": int(pop_size), "crossover": crossover, "external_archive": archive},
    )
    st.code(configuration.to_cli(), language="bash", wrap_lines=True)
    changed = changes(configuration)
    st.markdown(
        "**Changed from the default:** "
        + (
            ", ".join(f"`{item.name}` = {format_value(item.value)}" for item in changed)
            if changed
            else "nothing: this is the default configuration, which runs exactly as VAMOS's own "
            "default NSGA-II."
        )
    )


def _render_other_spaces() -> None:
    rows = []
    for algorithm, encoding in BUILTIN_SPACES:
        space = builtin_space(algorithm, encoding)
        summary = summarize(space)
        rows.append(
            {
                "Algorithm": algorithm_label(algorithm),
                "Encoding": encoding,
                "Parameters": summary.parameters,
                "Top level": summary.top_level,
                "Active by default": summary.default_active,
                "Depth": summary.depth,
            }
        )
    st.markdown("Every algorithm the studio offers has a space of its own, for each encoding:")
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.markdown(
        "They share most operators, but each one has its own parameters: **MOEA/D** its "
        "neighborhood and aggregation function, **SMS-EMOA** the reference point of its "
        "hypervolume, **RVEA** the divisions of its reference vectors instead of a population "
        "size, **SPEA2** its archive and density estimator. A **binary** space has other "
        "operators altogether (bit-flip mutation, HUX or uniform crossover). The default "
        "configuration of each one runs exactly as VAMOS's default, which tests check for every "
        "space."
    )


def _render_python() -> None:
    render_notebook_step(tutorial("parameter_spaces"))


def _render_next_steps() -> None:
    st.markdown(
        "- **S2. Solving a problem** runs NSGA-II with its default configuration and with "
        "another one.\n"
        "- Finding good configurations automatically, by searching a parameter space, is the "
        "subject of an advanced tutorial still to be written."
    )
    st.button(
        "All the tutorials",
        icon=":material/school:",
        on_click=open_tutorial,
        args=(None,),
        key=f"{KEY_PREFIX}_all_tutorials",
    )


STEPS: tuple[TutorialStep, ...] = (
    TutorialStep("What is a parameter space?", _render_introduction),
    TutorialStep("Step 1: the parameter tree of NSGA-II", _render_tree),
    TutorialStep("Step 2: choices activate parameters", _render_choices),
    TutorialStep("Step 3: a configuration as a command line", _render_command_line),
    TutorialStep("Step 4: the spaces of the other algorithms", _render_other_spaces),
    TutorialStep("Do it in Python", _render_python),
    TutorialStep("Where to go next", _render_next_steps),
)
