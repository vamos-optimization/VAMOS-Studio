"""Runs that a tutorial launches itself, and the companion notebooks of the tutorials.

Adapted from Evolver-Studio's prepared runs (evolver_studio/tutorial_solving.py): a step that runs
something has a *prepared run*, a request the tutorial launches right there ("Run it here"), with
the indicator values the text announces. The runs are fixed by a seed, so they give the same values
every time with the same VAMOS version; the tutorial says whether yours match. A run launched from
a tutorial is an ordinary run: it is kept in solve-runs/ and opens in Results.

The last step of a tutorial can offer its notebook, which does the same with VAMOS's Python API.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from importlib.resources import files
from typing import Any, Final

import numpy as np
import streamlit as st

from vamos_studio import charts, ui
from vamos_studio.backend import runs, vamos_version
from vamos_studio.backend.catalogue import problem_details
from vamos_studio.backend.indicators import compute_all
from vamos_studio.backend.upstream.vamos_bridge import builtin_space
from vamos_studio.front_summary import knee, summarize
from vamos_studio.tutorials import Tutorial

NOTEBOOKS_PACKAGE: Final = "vamos_studio.notebooks"
# The VAMOS version the announced values were measured with.
MEASURED_WITH: Final = "1.2.1"
# The values the text announces are written with four significant digits.
EXPECTED_TOLERANCE: Final = 5e-4
RUN_TIMEOUT_SECONDS: Final = 180
POLL_SECONDS: Final = 0.2
INDICATOR_NAMES: Final = {"hv": "HV", "igd_plus": "IGD+"}


@dataclass(slots=True, frozen=True)
class PreparedRun:
    """A run a tutorial can launch, and the values it announces for it.

    Attributes:
        key: Its name in the tutorial, which keys the widgets and the run it remembers.
        algorithm: The algorithm's key (e.g. "nsgaii").
        problem: The problem's key (e.g. "zdt1").
        changes: The values that differ from the algorithm's default configuration.
        max_evaluations: The evaluations of the run.
        seed: Its random seed.
        n_obj: Its number of objectives, when the problem lets you choose it.
        expected: The indicator values the text announces, by key ("hv", "igd_plus").
    """

    key: str
    algorithm: str
    problem: str
    changes: dict[str, Any] = field(default_factory=dict)
    max_evaluations: int = 25000
    seed: int = 1
    n_obj: int | None = None
    expected: dict[str, float] = field(default_factory=dict)


def prepared_request(prepared: PreparedRun) -> runs.SolveRequest:
    """The request of a prepared run: the default configuration with its changes."""
    space = builtin_space(prepared.algorithm, "real")
    if space is None:  # pragma: no cover - the tutorials use shipped grammars
        raise LookupError(f"No grammar for {prepared.algorithm}.")
    configuration = space.configuration(space.default_values() | prepared.changes, complete=True)
    details = problem_details(prepared.problem, prepared.n_obj)
    return runs.SolveRequest(
        problem=prepared.problem,
        algorithm=prepared.algorithm,
        encoding="real",
        space=space.name,
        space_hash=space.content_hash(),
        configuration=dict(configuration.values),
        max_evaluations=prepared.max_evaluations,
        seed=prepared.seed,
        n_obj=prepared.n_obj,
        n_var=details.n_var,
    )


def measured(run: runs.SolveRun) -> dict[str, float]:
    """HV and IGD+ of a finished run against its reference front."""
    reference, _ = runs.reference_front_of(run)
    values = compute_all(runs.result_front(run)[0], reference)
    return {key: values[key] for key in INDICATOR_NAMES}


def run_and_wait(prepared: PreparedRun) -> runs.SolveRun:
    """Launch a prepared run and wait until it ends (or the timeout)."""
    run = runs.launch(prepared_request(prepared), runs.runs_directory())
    deadline = time.monotonic() + RUN_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        state = runs.state(run)
        if state.has_results or state in (runs.RunState.FAILED, runs.RunState.CANCELLED):
            break
        time.sleep(POLL_SECONDS)
    return run


def render_prepared_run(prepared: PreparedRun, description: str) -> runs.SolveRun | None:
    """A button that launches the run, and its outcome once it has one.

    Args:
        prepared: The run.
        description: What it is, in a few words, for the button and the outcome.

    Returns:
        The run, once it has ended with results; None before.
    """
    key = f"tutorial_run:{prepared.key}"
    run = _remembered(key)
    if st.button(
        f"Run it here: {description}",
        key=f"{key}:launch",
        icon=":material/play_arrow:",
        type="primary" if run is None else "secondary",
    ):
        with st.spinner(f"Running {description}…"):
            run = run_and_wait(prepared)
        st.session_state[key] = run.run_id
    if run is None:
        return None
    if not runs.state(run).has_results:
        st.warning(f"The run did not finish: see it in the Monitor ({run.run_id}).")
        return None
    _render_outcome(prepared, run)
    return run


def render_notebook_step(item: Tutorial) -> None:
    """The last step of a tutorial: its companion notebook, to download, and its code."""
    if item.notebook is None:
        return
    notebook = json.loads(notebook_text(item.notebook))
    code = ["".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code"]
    st.markdown(
        "VAMOS-Studio drives **VAMOS**, a Python library, so everything this tutorial did can be "
        "done in a few lines of Python. The notebook below does it with VAMOS's own API, the one "
        "you would use in your scripts or experiments: download it and open it in Jupyter, "
        "JupyterLab or VS Code, in an environment with `vamos-optimization` and `plotly` "
        "installed (this studio's environment has both)."
    )
    st.download_button(
        f"Download {item.notebook}",
        notebook_text(item.notebook),
        file_name=item.notebook,
        mime="application/x-ipynb+json",
        icon=":material/download:",
    )
    with st.expander("The notebook's code", expanded=False):
        st.code("\n\n".join(code), language="python")


def notebook_text(name: str) -> str:
    """The content of a companion notebook shipped with the studio."""
    return files(NOTEBOOKS_PACKAGE).joinpath(name).read_text(encoding="utf-8")


def _remembered(key: str) -> runs.SolveRun | None:
    run_id = st.session_state.get(key)
    if not run_id:
        return None
    run = runs.SolveRun(runs.runs_directory() / run_id)
    return run if run.directory.is_dir() else None


def _render_outcome(prepared: PreparedRun, run: runs.SolveRun) -> None:
    front = runs.result_front(run)[0]
    reference, _ = runs.reference_front_of(run)
    st.plotly_chart(
        charts.front_figure(front, reference, knee(summarize(front))),
        width="stretch",
        key=f"tutorial_run:{prepared.key}:front",
    )
    values = measured(run)
    columns = st.columns(len(values) + 1)
    columns[0].metric("Solutions", len(front))
    for column, (name, value) in zip(columns[1:], values.items()):
        column.metric(INDICATOR_NAMES[name], f"{value:.4f}")
    _check_expected(prepared, values)
    if st.button("Open it in Results", key=f"tutorial_run:{prepared.key}:results"):
        ui.open_run(run)
        st.switch_page(ui.RESULTS)


def _check_expected(prepared: PreparedRun, values: dict[str, float]) -> None:
    """Say whether the indicator values are the ones the text announces (if it announces any)."""
    if not prepared.expected:
        return
    announced = ", ".join(
        f"{INDICATOR_NAMES[name]} = {value:.4f}" for name, value in prepared.expected.items()
    )
    if all(
        bool(np.isclose(values[name], value, rtol=0, atol=EXPECTED_TOLERANCE))
        for name, value in prepared.expected.items()
    ):
        st.success(f"The values announced ({announced}) are the ones you got.")
        return
    st.info(
        f"The text announces {announced}, measured with VAMOS {MEASURED_WITH}; you got other "
        f"values with VAMOS {vamos_version() or '(unknown)'}. Another VAMOS version can give other "
        "values: the conclusions of the step do not depend on the exact numbers."
    )
