"""Series of independent runs: one request with consecutive seeds, a few runs at a time.

A detached process (`python -m vamos_studio.backend.series <series-dir>`) launches the runs, so
that a series survives the browser and the app, like a single run. Everything about a series is
in `<runs directory>/series/<series-id>/`: what it asks for, the PID and log of that process, and
the marks that stop or cancel it. Each run is an ordinary run, called `<series-id>_seed_<seed>`.

A series measured against an approximate front copies it once, when it is created, so that all
its runs are measured against the same version, even if some of them add to the front.

Adapted from Transept (transept/series.py), by the same authors.
"""

from __future__ import annotations

import dataclasses
import json
import subprocess
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Final

import numpy as np
from numpy.typing import NDArray

from . import approximate_fronts, runs
from .runs import RunState, SolveRequest

SERIES_DIRECTORY: Final = "series"
SERIES_FILE: Final = "series.json"
PID_FILE: Final = "pid.txt"
LOG_FILE: Final = "log.txt"
CANCELLED_FILE: Final = "cancelled"
STOP_FILE: Final = "stop_requested"
MAX_SEED: Final = 2**31 - 1
POLL_SECONDS: Final = 0.5
QUEUED: Final = "queued"
NOT_STARTED: Final = "not started"
DELETED: Final = "deleted"


class SeriesState(Enum):
    """The state of a series."""

    RUNNING = "running"
    FINISHED = "finished"
    FINISHED_WITH_PROBLEMS = "finished, with problems"
    CANCELLED = "cancelled"
    STOPPED = "stopped before finishing"
    STOPPED_BY_USER = "stopped at your request"

    @property
    def active(self) -> bool:
        return self is SeriesState.RUNNING


@dataclass(slots=True, frozen=True)
class Series:
    """A series of independent runs.

    Attributes:
        directory: Where its files are; its name is the series' identifier.
        request: The request of its first run; run i uses `request.seed + i`.
        count: How many runs.
        parallel: How many runs may be active at a time.
    """

    directory: Path
    request: SolveRequest
    count: int
    parallel: int

    @property
    def series_id(self) -> str:
        return self.directory.name

    @property
    def runs_directory(self) -> Path:
        return self.directory.parent.parent

    @property
    def seeds(self) -> range:
        return range(self.request.seed, self.request.seed + self.count)

    def run_id(self, seed: int) -> str:
        return f"{self.series_id}_seed_{seed}"

    def run(self, seed: int) -> runs.SolveRun:
        return runs.SolveRun(self.runs_directory / self.run_id(seed))


@dataclass(slots=True, frozen=True)
class Member:
    """A run of a series, which may not have started.

    Attributes:
        seed: Its random seed.
        run: The run.
        state: The value of its state, or "queued", "not started" or "deleted".
    """

    seed: int
    run: runs.SolveRun
    state: str


def validate(request: SolveRequest, count: int, parallel: int) -> list[str]:
    """What is wrong with a series, besides its request; empty when it is fine."""
    found = []
    if count < 2:
        found.append("A series needs at least two runs.")
    if parallel < 1:
        found.append("At least one run must be active at a time.")
    if request.seed + count - 1 > MAX_SEED:
        found.append(f"The seeds of the series must not exceed {MAX_SEED}.")
    return found


def launch(request: SolveRequest, count: int, parallel: int, parent: Path) -> Series:
    """Start a series in the background: `count` runs of `request`, seeds from `request.seed`.

    Raises:
        ValueError: If the series is not valid, or is measured against an approximate front that
            does not exist.
    """
    problems = validate(request, count, parallel)
    if problems:
        raise ValueError(" ".join(problems))
    directory = runs.new_run_directory(parent / SERIES_DIRECTORY)
    directory.mkdir(parents=True)
    if request.reference_front == "approximate":
        front = approximate_fronts.load(parent, request.problem, runs.run_arguments(request))
        if front is None:
            raise ValueError(f"There is no approximate front of {request.problem} to measure with.")
        approximate_fronts.snapshot(front, directory)
    runs.write_json(
        directory / SERIES_FILE,
        {"request": request.to_dict(), "count": count, "parallel": parallel},
    )
    with (directory / LOG_FILE).open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "vamos_studio.backend.series", str(directory)],
            cwd=directory,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    (directory / PID_FILE).write_text(f"{process.pid}\n", encoding="utf-8")
    threading.Thread(target=process.wait, daemon=True).start()
    return load(directory)


def load(directory: Path) -> Series:
    """The series in `directory`."""
    saved = json.loads((directory / SERIES_FILE).read_text(encoding="utf-8"))
    return Series(
        directory=directory,
        request=SolveRequest.from_dict(saved["request"]),
        count=int(saved["count"]),
        parallel=int(saved["parallel"]),
    )


def list_series(parent: Path) -> list[Series]:
    """The series under runs dir `parent` with at least one run left, newest first."""
    root = parent / SERIES_DIRECTORY
    if not root.is_dir():
        return []
    found = []
    for path in sorted(root.glob(f"*/{SERIES_FILE}"), reverse=True):
        series = load(path.parent)
        if _is_active(series) or any(
            m.state not in (DELETED, NOT_STARTED) for m in members(series)
        ):
            found.append(series)
    return found


def series_of_runs(parent: Path) -> dict[str, str]:
    """The series of each run that belongs to one, by run identifier."""
    return {
        series.run_id(seed): series.series_id
        for series in list_series(parent)
        for seed in series.seeds
    }


def members(series: Series) -> list[Member]:
    """The runs of a series with their states."""
    launching = _is_active(series) and not _is_cancelled(series) and not _is_stop_requested(series)
    found = []
    for seed in series.seeds:
        run = series.run(seed)
        if (run.directory / runs.REQUEST_FILE).is_file():
            value = runs.state(run).value
        elif (series.directory / f"started_{seed}").is_file():
            value = DELETED
        else:
            value = QUEUED if launching else NOT_STARTED
        found.append(Member(seed, run, value))
    return found


def state(series: Series) -> SeriesState:
    """The state of a series: its process, or else what became of its runs."""
    values = [member.state for member in members(series)]
    if _is_active(series) or any(
        v in (RunState.RUNNING.value, RunState.STARTING.value) for v in values
    ):
        return SeriesState.RUNNING
    if _is_cancelled(series):
        return SeriesState.CANCELLED
    if _is_stop_requested(series):
        return SeriesState.STOPPED_BY_USER
    if NOT_STARTED in values:
        return SeriesState.STOPPED
    if all(v == RunState.FINISHED.value for v in values):
        return SeriesState.FINISHED
    return SeriesState.FINISHED_WITH_PROBLEMS


def finished_members(series: Series) -> list[Member]:
    """The runs of a series that left results: finished, or stopped keeping them."""
    with_results = (RunState.FINISHED.value, RunState.STOPPED.value)
    return [member for member in members(series) if member.state in with_results]


def member_fronts(series: Series) -> list[tuple[Member, NDArray[np.float64]]]:
    """The result of each run of a series that has one, with the run."""
    return [(member, runs.result_front(member.run)[0]) for member in finished_members(series)]


def aggregate_front(fronts: list[NDArray[np.float64]]) -> NDArray[np.float64]:
    """The non-dominated union of the fronts of a series' runs."""
    merged = None
    for front in fronts:
        merged = approximate_fronts.merge(merged, front)
    return merged if merged is not None else np.empty((0, 0))


def cancel(series: Series) -> None:
    """Launch no more runs, and cancel the active ones."""
    (series.directory / CANCELLED_FILE).write_text("cancelled by the user\n", encoding="utf-8")
    for member in members(series):
        if member.state in (RunState.RUNNING.value, RunState.STARTING.value):
            runs.cancel(member.run)


def stop(series: Series) -> None:
    """Launch no more runs, and ask the active ones to end now keeping their results."""
    (series.directory / STOP_FILE).write_text("stopped by the user\n", encoding="utf-8")
    for member in members(series):
        if member.state in (RunState.RUNNING.value, RunState.STARTING.value):
            runs.request_stop(member.run)


def move_to_trash(series: Series) -> int:
    """Move the runs of a series to the trash; return how many there were.

    Raises:
        ValueError: If the series is still running; cancel it first.
    """
    if state(series).active:
        raise ValueError(f"Series {series.series_id} is still running: cancel it first.")
    existing = [m.run for m in members(series) if (m.run.directory / runs.REQUEST_FILE).is_file()]
    for run in existing:
        runs.move_to_trash(run)
    return len(existing)


def drive(series: Series, poll_seconds: float = POLL_SECONDS) -> None:
    """Launch the runs of a series, keeping at most `parallel` active, until none is left."""
    pending = deque(series.seeds)
    active: list[runs.SolveRun] = []
    snapshot = series.directory if series.request.reference_front == "approximate" else None
    while True:
        active = [run for run in active if runs.state(run).active]
        if _is_cancelled(series) or _is_stop_requested(series):
            return
        while pending and len(active) < series.parallel:
            seed = pending.popleft()
            request = dataclasses.replace(series.request, seed=seed)
            try:
                run = runs.launch(
                    request, series.runs_directory, name=series.run_id(seed), snapshot_from=snapshot
                )
            except FileExistsError as error:  # someone used the identifier in the meantime
                print(error, flush=True)
                continue
            (series.directory / f"started_{seed}").touch()
            active.append(run)
        if not pending and not active:
            return
        time.sleep(poll_seconds)


def _is_active(series: Series) -> bool:
    try:
        pid = int((series.directory / PID_FILE).read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return False
    return runs.is_alive(pid)


def _is_cancelled(series: Series) -> bool:
    return (series.directory / CANCELLED_FILE).is_file()


def _is_stop_requested(series: Series) -> bool:
    return (series.directory / STOP_FILE).is_file()


def main(arguments: list[str]) -> int:
    """Entry point: `python -m vamos_studio.backend.series <series-dir>`."""
    if len(arguments) != 1:
        print("usage: python -m vamos_studio.backend.series <series-dir>", file=sys.stderr)
        return 2
    drive(load(Path(arguments[0])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
