"""What the home page shows besides its links: recent activity, news and a one-click first run.

Kept apart from the page (pages/home.py) so that it can be tested without Streamlit.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final

from vamos_studio.backend import runs, series
from vamos_studio.backend.catalogue import problem_details
from vamos_studio.backend.upstream.vamos_bridge import builtin_space

QUICK_START_PROBLEM: Final = "zdt1"
QUICK_START_ALGORITHM: Final = "nsgaii"
QUICK_START_EVALUATIONS: Final = 25000
QUICK_START_PAUSE_SECONDS: Final = 0.05
QUICK_START_PAUSE_EVERY: Final = 5

_STAMP: Final = re.compile(r"(\d{8}-\d{6})")
_VERSION_HEADING: Final = re.compile(r"^## (.+)$")
_BOLD_LEAD: Final = re.compile(r"^- \*\*(.+?)\*\*:?\s*(.*)$")


@dataclass(slots=True, frozen=True)
class RecentRun:
    """A run as the home page lists it.

    Attributes:
        run: The run.
        state: Its state now.
        algorithm: Its algorithm's key.
        problem: Its problem's key.
        evaluations: Its budget.
        launched: When it was launched, from its directory's name.
        in_series: Whether it belongs to a series.
    """

    run: runs.SolveRun
    state: runs.RunState
    algorithm: str
    problem: str
    evaluations: int
    launched: datetime | None
    in_series: bool


@dataclass(slots=True, frozen=True)
class Activity:
    """The runs and series under a directory, summarized.

    Attributes:
        recent: The newest runs, newest first.
        total: How many runs there are.
        by_state: How many runs are in each state.
        series_count: How many series there are.
        active: The newest run still starting or running, if any.
        latest_result: The newest run with results, if any.
    """

    recent: tuple[RecentRun, ...]
    total: int
    by_state: dict[runs.RunState, int]
    series_count: int
    active: runs.SolveRun | None
    latest_result: runs.SolveRun | None = None

    @property
    def finished(self) -> int:
        """How many runs left results."""
        return sum(count for state, count in self.by_state.items() if state.has_results)


def launched_at(run_id: str) -> datetime | None:
    """When a run was launched, from its directory's name (e.g. "20261114-101500")."""
    match = _STAMP.search(run_id)
    return datetime.strptime(match.group(1), "%Y%m%d-%H%M%S") if match else None


def activity(parent: Path, limit: int = 6) -> Activity:
    """The activity under `parent`: its newest `limit` runs and counts of all of them."""
    all_runs = runs.list_runs(parent)
    in_series = series.series_of_runs(parent)
    states = {run.run_id: runs.state(run) for run in all_runs}
    recent = []
    for run in all_runs[:limit]:
        request = runs.read_request(run)
        if request is None:
            continue
        recent.append(
            RecentRun(
                run=run,
                state=states[run.run_id],
                algorithm=request.algorithm,
                problem=request.problem,
                evaluations=request.max_evaluations,
                launched=launched_at(run.run_id),
                in_series=run.run_id in in_series,
            )
        )
    active = next((run for run in all_runs if states[run.run_id].active), None)
    latest_result = next((run for run in all_runs if states[run.run_id].has_results), None)
    return Activity(
        recent=tuple(recent),
        total=len(all_runs),
        by_state=dict(Counter(states.values())),
        series_count=len(series.list_series(parent)),
        active=active,
        latest_result=latest_result,
    )


def latest_changes(changelog: str, limit: int = 5) -> tuple[str, list[tuple[str, str]]]:
    """The newest version of a changelog, and the lead and text of its first bold items.

    Args:
        changelog: The text of CHANGELOG.md.
        limit: How many items at most.

    Returns:
        The version heading (e.g. "0.1.0 (unreleased)"), and (lead, rest) per item, the lead
        being the item's bold opening (e.g. "Explore › Problems"). Empty if there is no version.
    """
    version, items, current = "", [], ""
    for line in changelog.splitlines() + [""]:
        heading = _VERSION_HEADING.match(line)
        if heading:
            if version:
                break
            version = heading.group(1).strip()
            continue
        if not version:
            continue
        if line.startswith("- ") or not line.strip() or line.startswith("#"):
            _collect(current, items)
            current = line if line.startswith("- ") else ""
        elif current:
            current += " " + line.strip()
        if len(items) >= limit:
            break
    return version, items[:limit]


def _collect(item: str, items: list[tuple[str, str]]) -> None:
    match = _BOLD_LEAD.match(item)
    if match:
        items.append((match.group(1), match.group(2)))


def quick_start_request() -> runs.SolveRequest:
    """NSGA-II with its default configuration on ZDT1, with a live view: a first run."""
    space = builtin_space(QUICK_START_ALGORITHM, "real")
    if space is None:  # pragma: no cover - the grammar ships with the studio
        raise LookupError("The NSGA-II grammar for real-coded problems is missing.")
    return runs.SolveRequest(
        problem=QUICK_START_PROBLEM,
        algorithm=QUICK_START_ALGORITHM,
        encoding="real",
        space=space.name,
        space_hash=space.content_hash(),
        configuration=dict(space.default_configuration().values),
        max_evaluations=QUICK_START_EVALUATIONS,
        seed=1,
        pause_seconds=QUICK_START_PAUSE_SECONDS,
        pause_every=QUICK_START_PAUSE_EVERY,
        n_var=problem_details(QUICK_START_PROBLEM).n_var,
    )
