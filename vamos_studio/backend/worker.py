"""The worker process of a solve run: `python -m vamos_studio.backend.worker <run-dir>`.

It reads the run's request, builds the VAMOS configuration from the grammar, runs
`vamos.optimize` with a live-visualization callback that reports progress to files, and saves
VAMOS's run artifact. The callback also stops the run, at its next generation, when the app
writes the stop mark; the run then ends with the solutions found so far.
"""

from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path
from typing import Any, Final

import numpy as np
import vamos

from .runs import (
    LIVE_FRONT_FILE,
    STATUS_FILE,
    STOP_FILE,
    SolveRequest,
    SolveRun,
    read_request,
    write_json,
)
from .upstream.vamos_bridge import builtin_space, to_algorithm_config

# The live front and status are rewritten at most this often, plus once at the end.
MIN_WRITE_INTERVAL_SECONDS: Final = 0.5
# A pause is slept in slices this long, so that a stop or a cancellation is noticed quickly.
PAUSE_SLICE_SECONDS: Final = 0.05


class FileProgress:
    """A VAMOS live-visualization callback that reports to a run's directory.

    It writes the status (generation, evaluations, elapsed time) and the current non-dominated
    front, at most every `min_interval` seconds, and asks VAMOS to stop once the stop mark exists.
    With `pause_seconds`, it also pauses every `pause_every` generations, after writing the front,
    so that the live view shows the front converge; sleeping uses no random numbers, so the
    results are the same as without pauses.
    """

    def __init__(
        self,
        directory: Path,
        max_evaluations: int,
        min_interval: float,
        pause_seconds: float = 0.0,
        pause_every: int = 1,
    ) -> None:
        self.directory = directory
        self.max_evaluations = max_evaluations
        self.min_interval = min_interval
        self.pause_seconds = max(0.0, pause_seconds)
        self.pause_every = max(1, pause_every)
        self.generation = 0
        self.evaluations = 0
        self.stopped = False
        self.paused_seconds = 0.0
        self._started = time.monotonic()
        self._last_write = float("-inf")
        self._front: np.ndarray | None = None

    def on_start(self, ctx: Any = None) -> None:
        self._started = time.monotonic()
        self.write_status("running")

    def on_generation(
        self,
        generation: int,
        F: np.ndarray | None = None,
        X: np.ndarray | None = None,
        stats: dict[str, Any] | None = None,
    ) -> None:
        self.generation = int(generation)
        evaluations = (stats or {}).get("evals")
        if evaluations is not None:
            self.evaluations = int(evaluations)
        if F is not None:
            self._front = np.asarray(F, dtype=float)
        if self._pauses_now():
            self.flush("running")
            self._pause()
        elif time.monotonic() - self._last_write >= self.min_interval:
            self.flush("running")

    def on_end(self, final_F: Any = None, final_stats: dict[str, Any] | None = None) -> None:
        return None

    def should_stop(self) -> bool:
        if (self.directory / STOP_FILE).is_file():
            self.stopped = True
        return self.stopped

    def ended_by(self) -> str:
        """What ended the run: "user" (a stop request) or "evaluations" (its budget)."""
        return "user" if self.stopped else "evaluations"

    def _pauses_now(self) -> bool:
        return self.pause_seconds > 0 and self.generation % self.pause_every == 0

    def _pause(self) -> None:
        """Sleep `pause_seconds`, in slices, ending early once a stop is requested."""
        started = time.monotonic()
        deadline = started + self.pause_seconds
        while time.monotonic() < deadline and not self.should_stop():
            time.sleep(min(PAUSE_SLICE_SECONDS, deadline - time.monotonic()))
        self.paused_seconds += time.monotonic() - started

    def flush(self, state: str, ended_by: str | None = None) -> None:
        """Write the live front and the status now."""
        if self._front is not None and self._front.size:
            path = self.directory / LIVE_FRONT_FILE
            temporary = path.with_name(f".{path.name}.tmp")
            np.savetxt(temporary, self._front, delimiter=",", fmt="%.10g")
            temporary.replace(path)
        self.write_status(state, ended_by=ended_by)

    def write_status(
        self, state: str, error: str | None = None, ended_by: str | None = None
    ) -> None:
        """Write the status file."""
        self._last_write = time.monotonic()
        write_json(
            self.directory / STATUS_FILE,
            {
                "state": state,
                "generation": self.generation,
                "evaluations": self.evaluations,
                "max_evaluations": self.max_evaluations,
                "elapsed_seconds": round(self._last_write - self._started, 3),
                "paused_seconds": round(self.paused_seconds, 3),
                "ended_by": ended_by,
                "error": error,
            },
        )


def solve(request: SolveRequest, progress: FileProgress) -> Any:
    """Run the request with VAMOS, reporting through `progress`; return VAMOS's result."""
    space = builtin_space(request.algorithm, request.encoding)
    if space is None:
        raise ValueError(f"No grammar for {request.algorithm} with {request.encoding} encoding.")
    if space.content_hash() != request.space_hash:
        raise ValueError(f"The grammar {space.name} changed since the run was requested.")
    config = to_algorithm_config(space.configuration(request.configuration))
    return vamos.optimize(
        request.problem,
        algorithm=request.algorithm,
        algorithm_config=config,
        max_evaluations=request.max_evaluations,
        seed=request.seed,
        live_viz=progress,
    )


def run(directory: Path, min_interval: float = MIN_WRITE_INTERVAL_SECONDS) -> int:
    """Run the request in `directory`; return the process exit code (0 when it has results)."""
    run_ = SolveRun(directory)
    request = read_request(run_)
    progress = FileProgress(
        directory,
        request.max_evaluations if request else 0,
        min_interval,
        pause_seconds=request.pause_seconds if request else 0.0,
        pause_every=request.pause_every if request else 1,
    )
    try:
        if request is None:
            raise ValueError(f"No request in {directory}.")
        result = solve(request, progress)
        vamos.save_result(result, run_.artifact)
    except Exception as error:  # noqa: BLE001 - report any failure to the app
        traceback.print_exc()
        progress.write_status("failed", error=f"{type(error).__name__}: {error}")
        return 1
    progress.flush("stopped" if progress.stopped else "finished", ended_by=progress.ended_by())
    return 0


def main(arguments: list[str]) -> int:
    """Entry point: `python -m vamos_studio.backend.worker <run-dir>`."""
    if len(arguments) != 1:
        print("usage: python -m vamos_studio.backend.worker <run-dir>", file=sys.stderr)
        return 2
    return run(Path(arguments[0]))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
