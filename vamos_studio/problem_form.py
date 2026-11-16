"""The form of a problem's arguments, shared by the pages that choose a problem.

A checkbox sets the problem's arguments; without it, the problem is built with its defaults.
With it, there is one input per argument, by its type, in up to four columns; the number of
objectives offers only those the studio has reference fronts and charts for.

Adapted from Evolver-Studio (evolver_studio/problem_form.py: defaults_help,
render_argument_inputs, _render_arguments), by the same authors.
"""

from __future__ import annotations

import streamlit as st

from vamos_studio.backend.catalogue import (
    ProblemArgument,
    ProblemEntry,
    argument_problems,
    default_arguments,
    problem_arguments,
    standard_variables,
)


def defaults_help(entry: ProblemEntry) -> str:
    """What a problem is built with when its arguments are not set."""
    return (
        f"Without them, {entry.label} is built with its defaults ({entry.n_obj} objectives, "
        f"{entry.n_var} variables)."
    )


def render_problem_arguments(entry: ProblemEntry, key_prefix: str) -> dict[str, object] | None:
    """The arguments of a problem, set by the user or its defaults.

    Returns:
        The value of every argument, or None when the values set are not valid (the form then
        says why).
    """
    arguments = problem_arguments(entry.key)
    if not arguments:
        return {}
    custom = st.checkbox(
        "Set its arguments",
        key=f"{key_prefix}.set_arguments.{entry.key}",
        help=defaults_help(entry),
    )
    if not custom:
        return default_arguments(entry.key)
    columns = st.columns(min(len(arguments), 4))
    values = {
        argument.name: _render_argument(
            entry, argument, columns[index % len(columns)], f"{key_prefix}.{entry.key}"
        )
        for index, argument in enumerate(arguments)
    }
    n_obj = int(values.get("n_obj", entry.n_obj))
    standard = standard_variables(entry.key, n_obj)
    if "n_var" in values and values["n_var"] != standard:
        st.caption(f"The standard {entry.label} with {n_obj} objectives has {standard} variables.")
    problems = argument_problems(entry.key, values)
    for problem in problems:
        st.error(problem, icon=":material/error:")
    return None if problems else values


def _render_argument(entry: ProblemEntry, argument: ProblemArgument, column, prefix: str):
    key = f"{prefix}.{argument.name}"
    help_text = f"`{argument.name}`, {argument.default} by default."
    if argument.name == "n_obj":
        options = list(entry.n_obj_options)
        return column.selectbox(
            argument.label,
            options,
            index=options.index(argument.default),
            key=key,
            on_change=_follow_objectives,
            args=(entry.key, key, f"{prefix}.n_var"),
            help=help_text + " Changing it sets the variables to the standard number for it. "
            "With four or more, fronts are drawn in parallel coordinates; without an exact "
            "reference front, runs can build an approximate one.",
        )
    if argument.type == "boolean":
        return column.checkbox(
            argument.label, value=bool(argument.default), key=key, help=help_text
        )
    if argument.type == "integer":
        return int(
            column.number_input(
                argument.label,
                step=1,
                min_value=1,
                key=key,
                help=help_text,
                # A callback may have set it already (see _follow_objectives): set it only once.
                **({} if key in st.session_state else {"value": int(argument.default)}),
            )
        )
    return float(column.number_input(argument.label, value=float(argument.default), key=key))


def _follow_objectives(problem: str, objectives_key: str, variables_key: str) -> None:
    """Set the variables to the standard number for the objectives just chosen."""
    st.session_state[variables_key] = standard_variables(
        problem, int(st.session_state[objectives_key])
    )
