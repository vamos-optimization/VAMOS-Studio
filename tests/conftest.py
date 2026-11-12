"""Shared fixtures: real solve runs, launched in temporary directories."""

import time
from pathlib import Path

import pytest

from vamos_studio.backend import runs
from vamos_studio.backend.upstream.vamos_bridge import builtin_space

WAIT_SECONDS = 120


def make_request(
    problem: str = "zdt1", max_evaluations: int = 2000, **changes: object
) -> runs.SolveRequest:
    """A request of the default NSGA-II configuration, with `changes` to its parameters."""
    space = builtin_space("nsgaii", "real")
    values = dict(space.default_configuration().values) | changes
    configuration = space.configuration(values, complete=True)
    return runs.SolveRequest(
        problem=problem,
        algorithm="nsgaii",
        encoding="real",
        space=space.name,
        space_hash=space.content_hash(),
        configuration=dict(configuration.values),
        max_evaluations=max_evaluations,
        seed=1,
    )


def wait_until(condition, timeout: float = WAIT_SECONDS) -> None:
    """Poll `condition` until it holds, or fail the test after `timeout` seconds."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.1)
    pytest.fail(f"Timed out after {timeout} s")


def wait_for_end(run: runs.SolveRun) -> runs.RunState:
    """Wait until a run is no longer active; return its state."""
    wait_until(lambda: not runs.state(run).active)
    return runs.state(run)


@pytest.fixture(scope="session")
def finished_run(tmp_path_factory) -> runs.SolveRun:
    """A run of NSGA-II on ZDT1 with 2000 evaluations, finished."""
    parent: Path = tmp_path_factory.mktemp("runs")
    run = runs.launch(make_request(), parent)
    wait_for_end(run)
    return run
