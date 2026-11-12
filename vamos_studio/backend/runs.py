"""Solve runs: their request, their directory, and launching, following and stopping them.

A run is a detached worker process (`python -m vamos_studio.backend.worker <run-dir>`) that
outlives the browser and the app. Everything about it lives in its directory under
`solve-runs/`: the request, the worker's PID and log, the status and live front the worker keeps
up to date, the marks that ask it to stop or record that it was cancelled, and `run/`, the run
artifact VAMOS writes (`manifest.json`, `result.npz`, `environment.json`).

Adapted from Transept (transept/runner.py and transept/runs.py), by the same authors.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Final

import numpy as np
import vamos
from numpy.typing import NDArray

from . import approximate_fronts
from .catalogue import (
    problem_details,
    problem_entry,
    reference_front,
    reference_front_source,
)

RUNS_DIRECTORY_ENV: Final = "VAMOS_STUDIO_RUNS"
REQUEST_FILE: Final = "request.json"
STATUS_FILE: Final = "status.json"
PID_FILE: Final = "pid.txt"
LOG_FILE: Final = "worker.log"
STOP_FILE: Final = "stop"
CANCELLED_FILE: Final = "cancelled"
LIVE_FRONT_FILE: Final = "live_front.csv"
ARTIFACT_DIRECTORY: Final = "run"
SELECTION_FILE: Final = "selection.json"
WORKER_MODULE: Final = "vamos_studio.backend.worker"
TRASH_DIRECTORY: Final = "trash"
TRASH_MANIFEST: Final = "trash.json"


class RunState(Enum):
    """The state of a run."""

    STARTING = "starting"
    RUNNING = "running"
    FINISHED = "finished"
    STOPPED = "stopped"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"

    @property
    def active(self) -> bool:
        """Whether the run may still change."""
        return self in (RunState.STARTING, RunState.RUNNING)

    @property
    def has_results(self) -> bool:
        """Whether the run left a VAMOS run artifact."""
        return self in (RunState.FINISHED, RunState.STOPPED)


@dataclass(slots=True, frozen=True)
class SolveRequest:
    """What a run solves, and with what.

    Attributes:
        problem: The VAMOS problem id (e.g. "zdt1").
        algorithm: The VAMOS algorithm id (e.g. "nsgaii").
        encoding: The problem encoding the configuration is for.
        space: The name of the grammar the configuration derives from.
        space_hash: That grammar's content hash.
        configuration: The value of every active parameter, in depth-first order.
        max_evaluations: The evaluation budget.
        seed: The random seed.
        pause_seconds: How long the worker pauses, to let the live view show the front
            converge; 0 runs at full speed. Pausing changes the runtime, never the results.
        pause_every: Every how many generations it pauses.
        n_obj: The number of objectives, for a problem that lets you choose; None for its
            default. VAMOS derives the number of variables from it, unless `n_var` is set.
        n_var: The number of variables; None for the problem's default.
        problem_kwargs: The problem's other arguments (such as ZCAT's `level`), by name.
        reference_front: What the run is measured against: "exact" (the problem's known front),
            "approximate" (a copy of its approximate front at launch) or "none".
        contribute: Whether the run's solutions are added to the approximate front of its
            problem when it ends.
    """

    problem: str
    algorithm: str
    encoding: str
    space: str
    space_hash: str
    configuration: dict[str, Any] = field(default_factory=dict)
    max_evaluations: int = 25000
    seed: int = 1
    pause_seconds: float = 0.0
    pause_every: int = 1
    n_obj: int | None = None
    n_var: int | None = None
    problem_kwargs: dict[str, Any] = field(default_factory=dict)
    reference_front: str = "exact"
    contribute: bool = False

    def to_dict(self) -> dict[str, Any]:
        """The request as a JSON-ready mapping."""
        return asdict(self)

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> SolveRequest:
        """The request stored as `values`."""
        return cls(**values)


@dataclass(slots=True, frozen=True)
class RunStatus:
    """What the worker last reported about a run.

    Attributes:
        state: "running", "finished", "stopped" or "failed".
        generation: The last generation reported.
        evaluations: The evaluations done so far.
        max_evaluations: The evaluation budget.
        elapsed_seconds: The time since the run started.
        paused_seconds: How much of that time the worker spent pausing for the live view.
        ended_by: What ended a run that is over: "evaluations" or "user".
        live_source: What the live front shows: the population's non-dominated front
            ("population"), the external archive ("archive"), or a subset of an unbounded
            archive as large as the population ("archive_subset").
        archive_size: How many solutions the external archive holds, if the run keeps one.
        error: Why the run failed, if it did.
    """

    state: str
    generation: int = 0
    evaluations: int = 0
    max_evaluations: int = 0
    elapsed_seconds: float = 0.0
    paused_seconds: float = 0.0
    ended_by: str | None = None
    live_source: str = "population"
    archive_size: int | None = None
    error: str | None = None

    @property
    def fraction_done(self) -> float:
        """The share of the budget used, in [0, 1]."""
        if self.max_evaluations <= 0:
            return 0.0
        return min(1.0, self.evaluations / self.max_evaluations)


@dataclass(slots=True, frozen=True)
class SolveRun:
    """A run, by its directory.

    Attributes:
        directory: Its directory, named after the time it was launched.
    """

    directory: Path

    @property
    def run_id(self) -> str:
        """Its identifier: the name of its directory."""
        return self.directory.name

    @property
    def artifact(self) -> Path:
        """The run artifact VAMOS writes when the run ends with results."""
        return self.directory / ARTIFACT_DIRECTORY


def runs_directory() -> Path:
    """Where runs are kept: $VAMOS_STUDIO_RUNS, or solve-runs/ in the working directory."""
    return Path(os.environ.get(RUNS_DIRECTORY_ENV, "solve-runs")).resolve()


def new_run_directory(parent: Path, now: datetime | None = None) -> Path:
    """A directory for a new run under `parent`, named after `now`, that does not exist yet."""
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    candidate, suffix = parent / stamp, 1
    while candidate.exists():
        suffix += 1
        candidate = parent / f"{stamp}-{suffix}"
    return candidate


def launch(request: SolveRequest, parent: Path) -> SolveRun:
    """Start a run in the background and return it.

    The worker gets its own session, so that it survives the browser and the app; its output goes
    to a log file, which tells why a run that never reported did not start.
    """
    directory = new_run_directory(parent)
    directory.mkdir(parents=True)
    if request.reference_front == "approximate":
        front = approximate_fronts.load(parent, request.problem, run_arguments(request))
        if front is None:
            raise ValueError(f"There is no approximate front of {request.problem} to measure with.")
        approximate_fronts.snapshot(front, directory)
    write_json(directory / REQUEST_FILE, request.to_dict())
    with (directory / LOG_FILE).open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", WORKER_MODULE, str(directory)],
            cwd=directory,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    (directory / PID_FILE).write_text(f"{process.pid}\n", encoding="utf-8")
    # Reap the process when it ends, so that it is not mistaken for a live one.
    threading.Thread(target=process.wait, daemon=True).start()
    return SolveRun(directory)


def write_json(path: Path, values: dict[str, Any]) -> None:
    """Write `values` as JSON atomically, so a reader never sees a half-written file."""
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def read_json(path: Path) -> dict[str, Any] | None:
    """The JSON object in `path`, or None if it is missing or unreadable."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def read_request(run: SolveRun) -> SolveRequest | None:
    """The request of a run, or None if it has none."""
    values = read_json(run.directory / REQUEST_FILE)
    return SolveRequest.from_dict(values) if values else None


def read_status(run: SolveRun) -> RunStatus | None:
    """What the worker last reported, or None if it has reported nothing yet."""
    values = read_json(run.directory / STATUS_FILE)
    return RunStatus(**values) if values else None


def read_pid(run: SolveRun) -> int | None:
    """The PID of a run's worker, or None if it has none."""
    try:
        return int((run.directory / PID_FILE).read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def is_alive(pid: int | None) -> bool:
    """Whether a process is running."""
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def state(run: SolveRun) -> RunState:
    """The state of a run.

    The worker reports "running" while it works and its final state when it ends. A run whose
    worker is gone without a final state was cancelled (if the app marked it) or interrupted.
    """
    if (run.directory / CANCELLED_FILE).is_file():
        return RunState.CANCELLED
    status = read_status(run)
    if status is not None and status.state != "running":
        return RunState(status.state)
    if is_alive(read_pid(run)):
        return RunState.RUNNING if status is not None else RunState.STARTING
    return RunState.INTERRUPTED


def request_stop(run: SolveRun) -> None:
    """Ask a run to end at its next generation, keeping what it found so far."""
    (run.directory / STOP_FILE).write_text("stopped by the user\n", encoding="utf-8")


def stop_requested(run: SolveRun) -> bool:
    """Whether a stop was requested."""
    return (run.directory / STOP_FILE).is_file()


def cancel(run: SolveRun) -> None:
    """End a run now, without results, and mark it as cancelled."""
    (run.directory / CANCELLED_FILE).write_text("cancelled by the user\n", encoding="utf-8")
    pid = read_pid(run)
    if is_alive(pid):
        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass


def list_runs(parent: Path) -> list[SolveRun]:
    """The runs under `parent`, newest first."""
    if not parent.is_dir():
        return []
    found = [SolveRun(path) for path in parent.iterdir() if (path / REQUEST_FILE).is_file()]
    return sorted(found, key=lambda run: run.run_id, reverse=True)


def find_active_run(parent: Path) -> SolveRun | None:
    """The newest run under `parent` that is still starting or running, if any."""
    return next((run for run in list_runs(parent) if state(run).active), None)


def live_front(run: SolveRun) -> NDArray[np.float64] | None:
    """The non-dominated front the worker last reported, or None."""
    path = run.directory / LIVE_FRONT_FILE
    try:
        return np.loadtxt(path, delimiter=",", ndmin=2)
    except (OSError, ValueError):
        return None


@dataclass(slots=True, frozen=True)
class Selection:
    """The subset of an unbounded archive a run returns (see vamos_studio/backend/subset.py).

    Attributes:
        method: The subset selection used.
        size: How many solutions it keeps: the population size.
        archive_size: How many non-dominated solutions the archive had.
        indices: The rows of the archive's non-dominated front it keeps.
    """

    method: str
    size: int
    archive_size: int
    indices: tuple[int, ...]


def read_selection(run: SolveRun) -> Selection | None:
    """The subset a run returns from its unbounded archive, or None if it returns everything."""
    values = read_json(run.directory / SELECTION_FILE)
    if not values:
        return None
    return Selection(
        values["method"], values["size"], values["archive_size"], tuple(values["indices"])
    )


def result_front(
    run: SolveRun, whole: bool = False
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """The solutions a run returns: their objectives and their variables.

    They are the non-dominated solutions it found, or, when it selected a subset of an unbounded
    archive, that subset; `whole` gives the whole archive instead.

    Raises:
        FileNotFoundError: If the run left no run artifact.
    """
    if not (run.artifact / "manifest.json").is_file():
        raise FileNotFoundError(f"Run {run.run_id} has no results.")
    result = vamos.load_result(run.artifact)
    front, indices = result.front(return_indices=True)
    front, variables = np.asarray(front, dtype=float), np.asarray(result.X)[indices]
    selection = None if whole else read_selection(run)
    if selection is not None:
        kept = np.asarray(selection.indices, dtype=int)
        front, variables = front[kept], variables[kept]
    return front, variables


def manifest(run: SolveRun) -> dict[str, Any] | None:
    """The VAMOS run manifest of a run, or None if it has none."""
    return read_json(run.artifact / "manifest.json")


def log_tail(run: SolveRun, lines: int = 20) -> str:
    """The last lines of a run's worker log."""
    try:
        text = (run.directory / LOG_FILE).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return "\n".join(text.splitlines()[-lines:])


@dataclass(slots=True, frozen=True)
class Verification:
    """What VAMOS's `verify_run` says about a run's artifact.

    Attributes:
        status: "succeeded" when the artifact is intact and its run can be replayed exactly.
        integrity: Whether the files are intact and match their hashes.
        replayability: Whether VAMOS can replay the run exactly in this environment.
        reasons: Why a check did not pass.
    """

    status: str
    integrity: str
    replayability: str
    reasons: tuple[str, ...]


def verify(run: SolveRun) -> Verification:
    """Check a run's artifact with VAMOS (`vamos.verify_run`): data only, nothing is executed."""
    report = vamos.verify_run(run.artifact)
    return Verification(
        status=str(report.status),
        integrity=str(report.artifact_integrity),
        replayability=str(report.effective_replayability),
        reasons=tuple(str(reason) for reason in report.reasons),
    )


@dataclass(slots=True, frozen=True)
class TrashedRun:
    """A run moved to the trash.

    Attributes:
        run_id: Its identifier.
        deleted_at: When it was moved to the trash (ISO 8601, UTC).
        path: The directory of the trash that holds it.
    """

    run_id: str
    deleted_at: str
    path: Path


def trash_directory(parent: Path) -> Path:
    """The trash of the runs under `parent`."""
    return parent / TRASH_DIRECTORY


def move_to_trash(run: SolveRun) -> Path:
    """Move a run to the trash, from where it can be restored.

    Adapted from Transept (transept/runs.py, move_to_trash).

    Raises:
        ValueError: If the run is still active; cancel it first.
    """
    if state(run).active:
        raise ValueError(f"Run {run.run_id} is still running: cancel it first.")
    deleted_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    target = trash_directory(run.directory.parent) / f"{stamp}_{run.run_id}"
    target.mkdir(parents=True)
    shutil.move(str(run.directory), str(target / run.run_id))
    write_json(target / TRASH_MANIFEST, {"run_id": run.run_id, "deleted_at": deleted_at})
    return target


def list_trash(parent: Path) -> list[TrashedRun]:
    """The runs in the trash of `parent`, most recently deleted first."""
    root = trash_directory(parent)
    if not root.is_dir():
        return []
    found = []
    for directory in root.iterdir():
        manifest = read_json(directory / TRASH_MANIFEST)
        if manifest:
            found.append(TrashedRun(manifest["run_id"], manifest["deleted_at"], directory))
    return sorted(found, key=lambda item: item.path.name, reverse=True)


def restore(parent: Path, trashed: TrashedRun) -> SolveRun:
    """Move a run back from the trash.

    Raises:
        FileExistsError: If a run with the same identifier exists again.
    """
    run = SolveRun(parent / trashed.run_id)
    if run.directory.exists():
        raise FileExistsError(f"Run {trashed.run_id} exists again: delete it first.")
    shutil.move(str(trashed.path / trashed.run_id), str(run.directory))
    shutil.rmtree(trashed.path)
    return run


def empty_trash(parent: Path) -> int:
    """Delete every run in the trash for good; return how many there were."""
    trashed = list_trash(parent)
    shutil.rmtree(trash_directory(parent), ignore_errors=True)
    return len(trashed)


def run_arguments(request: SolveRequest) -> dict[str, Any]:
    """Every argument of the problem a request solves, as approximate fronts are keyed."""
    n_obj = request.n_obj or problem_entry(request.problem).n_obj
    n_var = request.n_var or problem_details(request.problem, n_obj).n_var
    return approximate_fronts.front_arguments(request.problem, n_var, n_obj, request.problem_kwargs)


def reference_front_of(run: SolveRun) -> tuple[NDArray[np.float64] | None, str]:
    """The front a run is measured against, and where it comes from, in a few words."""
    request = read_request(run)
    if request is None or request.reference_front == "none":
        return None, "no reference front"
    if request.reference_front == "approximate":
        metadata = read_json(run.directory / approximate_fronts.SNAPSHOT_METADATA_FILE) or {}
        try:
            points = np.loadtxt(
                run.directory / approximate_fronts.SNAPSHOT_FRONT_FILE, delimiter=",", ndmin=2
            )
        except (OSError, ValueError):
            return None, "its approximate front is missing"
        return points, (
            f"the approximate front v{metadata.get('version', '?')} at launch "
            f"({len(points):,} points, {metadata.get('runs', '?')} runs)"
        )
    n_obj = request.n_obj or problem_entry(request.problem).n_obj
    front = reference_front(request.problem, n_obj)
    if front is None:
        return None, "no reference front"
    return front, f"the exact front ({reference_front_source(request.problem, n_obj)})"


def contribute(run: SolveRun) -> approximate_fronts.ApproximateFront:
    """Add a run's non-dominated solutions (its whole archive) to its problem's approximate front.

    Raises:
        FileNotFoundError: If the run left no results.
    """
    request = read_request(run)
    front, _ = result_front(run, whole=True)
    status = read_status(run)
    return approximate_fronts.add(
        run.directory.parent,
        request.problem,
        run_arguments(request),
        front,
        run_id=run.run_id,
        algorithm=request.algorithm,
        evaluations=status.evaluations if status else 0,
    )


def contributed(run: SolveRun) -> approximate_fronts.ApproximateFront | None:
    """The approximate front a run was added to, or None if it was not."""
    request = read_request(run)
    if request is None:
        return None
    front = approximate_fronts.load(run.directory.parent, request.problem, run_arguments(request))
    if front is None or run.run_id not in {c.run_id for c in front.contributions}:
        return None
    return front
