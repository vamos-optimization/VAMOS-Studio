"""New run: choose a problem, an algorithm and its configuration, set the budget, and launch it.

The structure follows Transept's New run page (pages/new_run.py); the configuration form is built
from the algorithm's grammar (vamos_studio/configuration_form.py).
"""

import os

import streamlit as st

from vamos_studio import ui
from vamos_studio.backend import approximate_fronts, runs, series
from vamos_studio.backend.catalogue import (
    algorithm_entries,
    default_algorithm_index,
    default_arguments,
    problem_details,
    problem_entries,
    reference_front,
    reference_front_source,
)
from vamos_studio.backend.upstream.parameter_space import Parameter, ParameterSpace
from vamos_studio.backend.upstream.vamos_bridge import (
    builtin_space,
    weight_file,
    weight_population,
    weight_populations,
)
from vamos_studio.configuration_form import active_fields, changes, configuration_of
from vamos_studio.live_view import estimated_generations, pause_overhead
from vamos_studio.parameter_tree import format_value
from vamos_studio.problem_form import render_problem_arguments

DEFAULT_EVALUATIONS = 25000
DEFAULT_SEED = 1
DEFAULT_PARALLEL = max(1, (os.cpu_count() or 2) // 2)
DEFAULT_PAUSE_SECONDS = 0.2
DEFAULT_PAUSE_EVERY = 5

st.title("New run")
st.info(
    "Prototype: NSGA-II, MOEA/D and SMS-EMOA on the ZDT and DTLZ problems and on binary ones. "
    "The run goes on in the background: follow it in the Monitor, and analyze it in Results.",
    icon=":material/construction:",
)


def widget_key(space: ParameterSpace, name: str) -> str:
    return f"new_run.{space.name}.{name}"


def current_values(space: ParameterSpace) -> dict[str, object]:
    """The form's value of every parameter: what the user set, or the default."""
    return {
        parameter.name: st.session_state.get(widget_key(space, parameter.name), parameter.default)
        for parameter in space.all_parameters()
    }


def reset_to_default(space: ParameterSpace) -> None:
    for parameter in space.all_parameters():
        st.session_state[widget_key(space, parameter.name)] = parameter.default


def render_parameter(space: ParameterSpace, parameter: Parameter, depth: int) -> None:
    key = widget_key(space, parameter.name)
    st.session_state.setdefault(key, parameter.default)
    label = ("↳ " * depth) + parameter.display_name
    help_text = f"`{parameter.name}`. {parameter.description}"
    if parameter.type == "categorical":
        st.selectbox(label, parameter.values, key=key, format_func=format_value, help=help_text)
    elif parameter.type == "boolean":
        st.checkbox(label, key=key, help=help_text)
    elif parameter.type == "int":
        st.number_input(
            label,
            min_value=int(parameter.low),
            max_value=int(parameter.high),
            step=1,
            key=key,
            help=help_text,
        )
    else:
        st.number_input(
            label,
            min_value=float(parameter.low),
            max_value=float(parameter.high),
            step=(parameter.high - parameter.low) / 100,
            format="%g",
            key=key,
            help=help_text,
        )


def render_configuration(space: ParameterSpace):
    """The configuration form; returns the configuration it describes."""
    st.button(
        "Reset to the default configuration",
        on_click=reset_to_default,
        args=(space,),
        icon=":material/restart_alt:",
    )
    fields = active_fields(space, current_values(space))
    columns = st.columns(2)
    for index, field in enumerate(fields):
        with columns[index % 2]:
            render_parameter(space, field.parameter, field.depth)
    configuration = configuration_of(space, current_values(space))
    changed = changes(configuration)
    if changed:
        st.caption(
            "Changed from the default: "
            + ", ".join(
                f"`{c.name}` {format_value(c.default)} → {format_value(c.value)}" for c in changed
            )
        )
    else:
        st.caption("This is the default configuration.")
    st.code(configuration.to_cli(), language="bash", wrap_lines=True)
    return configuration


def render_reference_front(problem, n_var: int, n_obj: int, problem_kwargs: dict):
    """The front the run is measured against, and whether it adds to the approximate front."""
    exact = reference_front(problem.key, n_obj) is not None
    arguments = approximate_fronts.front_arguments(problem.key, n_var, n_obj, problem_kwargs)
    approximate = approximate_fronts.load(runs.runs_directory(), problem.key, arguments)
    options = {}
    if exact:
        options["exact"] = f"Exact ({reference_front_source(problem.key, n_obj)})"
    if approximate is not None:
        options["approximate"] = approximate.label.capitalize()
    options["none"] = "None (no indicators)"
    choice = st.radio(
        "Reference front",
        list(options),
        format_func=options.get,
        horizontal=True,
        key=f"new_run.reference_front.{problem.key}.{n_var}.{n_obj}",
        help="What the run's quality indicators are measured against. The run keeps a copy of "
        "the approximate front as it is now, so its values do not change when the front grows.",
    )
    contribute = st.checkbox(
        "Add this run's solutions to the approximate reference front of this problem",
        value=not exact,
        key=f"new_run.contribute.{problem.key}.{n_var}.{n_obj}",
        help="The approximate front of a problem, for these arguments, is the non-dominated union "
        "of the runs added to it. Manage it in Explore › Problems.",
    )
    return choice, contribute


problems = [entry for entry in problem_entries() if entry.available]
st.subheader("1. Problem")
problem = st.selectbox("Problem", problems, format_func=lambda item: item.label)
arguments = render_problem_arguments(problem, "new_run")
valid_problem = arguments is not None
arguments = arguments if valid_problem else default_arguments(problem.key)
details = problem_details(problem.key, arguments.get("n_obj"), arguments.get("n_var"))
st.caption(f"{problem.description} {details.n_var} variables, {details.n_obj} objectives.")
problem_kwargs = {
    name: value
    for name, value in arguments.items()
    if name not in ("n_var", "n_obj") and value != default_arguments(problem.key)[name]
}
reference_choice, contribute = render_reference_front(
    problem, details.n_var, details.n_obj, problem_kwargs
)

st.subheader("2. Algorithm")
algorithms = [entry for entry in algorithm_entries() if problem.encoding in entry.encodings]
algorithm = st.selectbox(
    "Algorithm",
    algorithms,
    index=default_algorithm_index(algorithms),
    format_func=lambda item: item.label,
)
space = builtin_space(algorithm.key, problem.encoding)

st.subheader("3. Configuration")
configuration = render_configuration(space)

launchable = True
if algorithm.key == "moead" and details.n_obj >= 3 and not weight_populations(details.n_obj):
    launchable = False
    st.error(
        f"MOEA/D cannot run with {details.n_obj} objectives: neither jMetal nor VAMOS has a weight "
        f"vector file for them. Choose another number of objectives or another algorithm."
    )
elif algorithm.key == "moead" and details.n_obj >= 3:
    asked = int(configuration.values["pop_size"])
    population = weight_population(asked, details.n_obj)
    sizes = ", ".join(str(size) for size in weight_populations(details.n_obj))
    st.caption(
        f"MOEA/D reads its {population} weight vectors from {weight_file(asked, details.n_obj)}, "
        f"jMetal's file shipped with VAMOS, as jMetal and Evolver do"
        + ("." if population == asked else f": there is none for {asked}.")
        + f" Populations with a file for {details.n_obj} objectives: {sizes}."
    )

st.subheader("4. Budget")
left, right = st.columns(2)
max_evaluations = left.number_input(
    "Evaluations", min_value=100, max_value=10_000_000, value=DEFAULT_EVALUATIONS, step=1000
)
seed = right.number_input("Seed", min_value=0, max_value=2**31 - 1, value=DEFAULT_SEED, step=1)
left, right = st.columns(2)
count = int(
    left.number_input(
        "Independent runs",
        min_value=1,
        max_value=100,
        value=1,
        step=1,
        help="Runs of the same configuration with consecutive seeds, from the seed above: a "
        "series, analyzed together in Analyze › Results.",
    )
)
parallel = int(
    right.number_input(
        "Runs in parallel",
        min_value=1,
        max_value=max(1, os.cpu_count() or 1),
        value=min(max(count, 1), DEFAULT_PARALLEL),
        step=1,
        disabled=count == 1,
        help="How many runs of the series go on at a time.",
    )
)
if count > 1:
    st.caption(f"Seeds {int(seed)} to {int(seed) + count - 1}, {parallel} at a time.")


def render_live_view(max_evaluations: int, values: dict) -> tuple[float, int]:
    """The pauses that let the Monitor show the front converge; (0, 1) runs at full speed."""
    with st.expander("Live view"):
        slow = st.checkbox(
            "Slow the run down to watch the front converge",
            help="The run pauses now and then, after reporting its front, so that the Monitor "
            "can show how it evolves. Only the runtime changes: the results are the same.",
        )
        left, right = st.columns(2)
        pause_seconds = left.number_input(
            "Pause (seconds)",
            min_value=0.05,
            max_value=5.0,
            value=DEFAULT_PAUSE_SECONDS,
            step=0.05,
            format="%g",
            disabled=not slow,
        )
        pause_every = right.number_input(
            "Every (generations)",
            min_value=1,
            max_value=1000,
            value=DEFAULT_PAUSE_EVERY,
            step=1,
            disabled=not slow,
        )
        if not slow:
            return 0.0, 1
        generations = estimated_generations(
            max_evaluations, int(values["pop_size"]), float(values["offspring_ratio"])
        )
        added = pause_overhead(generations, float(pause_seconds), int(pause_every))
        st.caption(f"About {generations:,} generations: the pauses add about {added:.0f} s.")
        return float(pause_seconds), int(pause_every)


pause_seconds, pause_every = render_live_view(int(max_evaluations), dict(configuration.values))

if st.button(
    "Launch the run",
    type="primary",
    icon=":material/play_arrow:",
    disabled=not (valid_problem and launchable),
    help=None if valid_problem else "Fix the problem's arguments first.",
):
    request = runs.SolveRequest(
        problem=problem.key,
        algorithm=algorithm.key,
        encoding=problem.encoding,
        space=space.name,
        space_hash=space.content_hash(),
        configuration=dict(configuration.values),
        max_evaluations=int(max_evaluations),
        seed=int(seed),
        pause_seconds=pause_seconds,
        pause_every=pause_every,
        n_obj=details.n_obj if len(problem.n_obj_options) > 1 else None,
        n_var=details.n_var,
        problem_kwargs=problem_kwargs,
        reference_front=reference_choice,
        contribute=contribute,
    )
    if count > 1:
        ui.select_series(series.launch(request, count, parallel, runs.runs_directory()))
    else:
        ui.select_run(runs.launch(request, runs.runs_directory()))
        st.session_state.pop(ui.SELECTED_SERIES, None)  # the Monitor then follows the run
    st.switch_page(ui.MONITOR)
