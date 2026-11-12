"""Approximate reference fronts, built from the runs made on a problem.

Many problems have no known reference front (the binary knapsack or QUBO), and a problem whose
arguments differ from the standard ones has none either. The user can choose to add a run's
solutions to an approximate front of its problem: the non-dominated union of the fronts of every
run added, kept for each problem and set of arguments (a front of DTLZ2 with two objectives is
not one with three, nor one of the knapsack with 50 bits one with 100). A run can then be
measured against it instead of, or for want of, an exact front.

An approximate front changes as runs are added, and with it the bounds that normalize the
indicators; so a run measured against one keeps a copy of the version it was measured with (see
`runs.launch`), and its values do not change afterwards.

Fronts live under `<runs directory>/reference-fronts/<problem>/<arguments digest>/`, as
`front.csv` and `front.json` (the problem, its arguments, the version and the runs added).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

import moocore
import numpy as np
from numpy.typing import NDArray

from . import subset
from .catalogue import default_arguments

DIRECTORY: Final = "reference-fronts"
FRONT_FILE: Final = "front.csv"
METADATA_FILE: Final = "front.json"
LOCK_FILE: Final = ".lock"
# An approximate front keeps at most this many points; beyond, farthest-point selection keeps
# its extremes and its spread.
MAX_POINTS: Final = 10_000
LOCK_TIMEOUT_SECONDS: Final = 30.0


@dataclass(slots=True, frozen=True)
class Contribution:
    """A run added to an approximate front.

    Attributes:
        run_id: The run.
        algorithm: Its algorithm.
        evaluations: The evaluations it made.
        points: How many non-dominated solutions it brought.
        version: The version of the front after it was added.
        added_at: When (ISO 8601, UTC).
    """

    run_id: str
    algorithm: str
    evaluations: int
    points: int
    version: int
    added_at: str


@dataclass(slots=True, frozen=True)
class ApproximateFront:
    """An approximate reference front of a problem with a set of arguments.

    Attributes:
        problem: The VAMOS problem id.
        arguments: Every argument of the problem, defaults included.
        points: The front, one row per non-dominated solution.
        version: How many times runs changed it.
        contributions: The runs added, oldest first.
        directory: Where it is stored.
    """

    problem: str
    arguments: dict[str, Any]
    points: NDArray[np.float64]
    version: int
    contributions: tuple[Contribution, ...] = ()
    directory: Path = field(default=Path())

    @property
    def label(self) -> str:
        """The front in a few words, e.g. "approximate front v3 (512 points, 3 runs)"."""
        runs = len(self.contributions)
        return (
            f"approximate front v{self.version} ({len(self.points):,} points, "
            f"{runs} run{'s' if runs != 1 else ''})"
        )


def front_arguments(
    problem: str, n_var: int, n_obj: int, problem_kwargs: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Every argument of a problem as a run builds it: its defaults with the run's values."""
    return (
        default_arguments(problem) | dict(problem_kwargs or {}) | {"n_var": n_var, "n_obj": n_obj}
    )


def front_directory(parent: Path, problem: str, arguments: Mapping[str, Any]) -> Path:
    """Where the approximate front of `problem` with `arguments` lives, under runs dir `parent`."""
    canonical = json.dumps(dict(sorted(arguments.items())), separators=(",", ":"), default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]
    return parent / DIRECTORY / problem / digest


def load(parent: Path, problem: str, arguments: Mapping[str, Any]) -> ApproximateFront | None:
    """The approximate front of `problem` with `arguments`, or None if there is none."""
    return read_front(front_directory(parent, problem, arguments))


def read_front(directory: Path) -> ApproximateFront | None:
    """The approximate front stored in `directory`, or None if there is none."""
    try:
        metadata = json.loads((directory / METADATA_FILE).read_text(encoding="utf-8"))
        points = np.loadtxt(directory / FRONT_FILE, delimiter=",", ndmin=2)
    except (OSError, ValueError):
        return None
    return ApproximateFront(
        problem=metadata["problem"],
        arguments=metadata["arguments"],
        points=points,
        version=int(metadata["version"]),
        contributions=tuple(Contribution(**item) for item in metadata["contributions"]),
        directory=directory,
    )


def list_fronts(parent: Path, problem: str | None = None) -> list[ApproximateFront]:
    """The approximate fronts under runs dir `parent` (of `problem` only, if given)."""
    root = parent / DIRECTORY
    pattern = f"{problem}/*" if problem else "*/*"
    found = [read_front(directory) for directory in sorted(root.glob(pattern))]
    return [front for front in found if front is not None]


def merge(
    current: NDArray[np.float64] | None, added: NDArray[np.float64], cap: int = MAX_POINTS
) -> NDArray[np.float64]:
    """The non-dominated union of two fronts, without duplicates, at most `cap` points."""
    points = added if current is None else np.vstack([current, added])
    points = points[moocore.is_nondominated(points, keep_weakly=False)]
    if len(points) > cap:
        points = points[subset.select("farthest", points, cap)]
    return points


def add(
    parent: Path,
    problem: str,
    arguments: Mapping[str, Any],
    points: NDArray[np.float64],
    *,
    run_id: str,
    algorithm: str,
    evaluations: int,
) -> ApproximateFront:
    """Add a run's front to the approximate front of its problem, creating it if needed.

    Adding a run already added changes nothing.
    """
    directory = front_directory(parent, problem, arguments)
    directory.mkdir(parents=True, exist_ok=True)
    with _locked(directory):
        current = read_front(directory)
        if current is not None and run_id in {c.run_id for c in current.contributions}:
            return current
        version = (current.version if current else 0) + 1
        merged = merge(None if current is None else current.points, np.asarray(points, float))
        contribution = Contribution(
            run_id, algorithm, int(evaluations), len(points), version, _now()
        )
        contributions = (current.contributions if current else ()) + (contribution,)
        _write(directory, problem, dict(arguments), merged, version, contributions)
    return read_front(directory)


def delete(front: ApproximateFront) -> None:
    """Delete an approximate front for good. Runs measured against it keep their copy."""
    shutil.rmtree(front.directory, ignore_errors=True)


def snapshot(front: ApproximateFront, directory: Path) -> None:
    """Copy the current version of a front into a run's `directory`, which it is measured with."""
    np.savetxt(directory / SNAPSHOT_FRONT_FILE, front.points, delimiter=",", fmt="%.17g")
    (directory / SNAPSHOT_METADATA_FILE).write_text(
        json.dumps(
            {
                "problem": front.problem,
                "arguments": front.arguments,
                "version": front.version,
                "runs": len(front.contributions),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


SNAPSHOT_FRONT_FILE: Final = "reference_front.csv"
SNAPSHOT_METADATA_FILE: Final = "reference_front.json"


def _write(
    directory: Path,
    problem: str,
    arguments: dict[str, Any],
    points: NDArray[np.float64],
    version: int,
    contributions: tuple[Contribution, ...],
) -> None:
    temporary = directory / f".{FRONT_FILE}.tmp"
    np.savetxt(temporary, points, delimiter=",", fmt="%.17g")
    os.replace(temporary, directory / FRONT_FILE)
    metadata = {
        "problem": problem,
        "arguments": arguments,
        "version": version,
        "contributions": [
            {
                "run_id": c.run_id,
                "algorithm": c.algorithm,
                "evaluations": c.evaluations,
                "points": c.points,
                "version": c.version,
                "added_at": c.added_at,
            }
            for c in contributions
        ],
    }
    temporary = directory / f".{METADATA_FILE}.tmp"
    temporary.write_text(json.dumps(metadata, indent=2, default=str) + "\n", encoding="utf-8")
    os.replace(temporary, directory / METADATA_FILE)


@contextmanager
def _locked(directory: Path) -> Iterator[None]:
    """Hold the front's lock: two runs ending at once must not both rewrite it."""
    lock = directory / LOCK_FILE
    deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
    while True:
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            if _is_stale(lock):
                lock.unlink(missing_ok=True)
                continue
            if time.monotonic() > deadline:
                raise TimeoutError(f"The approximate front in {directory} stays locked.") from None
            time.sleep(0.05)
    try:
        yield
    finally:
        os.close(descriptor)
        lock.unlink(missing_ok=True)


def _is_stale(lock: Path) -> bool:
    """Whether a lock was left by a process that died holding it (older than the timeout)."""
    try:
        return time.time() - lock.stat().st_mtime > 2 * LOCK_TIMEOUT_SECONDS
    except OSError:
        return False


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
