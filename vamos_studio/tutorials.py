"""Catalogue of VAMOS-Studio's interactive tutorials.

Adapted from Evolver-Studio (evolver_studio/tutorials.py), by the same authors. As there, only the
tutorials that are written have a number, S1, S2..., consecutive in the order of the catalogue (by
level), and the planned ones are listed without one; a tutorial is identified by its topic
(`slug`), which does not change when they are renumbered. Each one pairs with the tutorials of
VAMOS's documentation that cover the same ground with Python code (T01, T03...). Unlike
Evolver-Studio, whose framework is Java, a tutorial can also come with a Jupyter notebook that does
what it shows with VAMOS's Python API (see `vamos_studio/notebooks/`).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Final

VAMOS_TUTORIALS_URL: Final = "https://vamos-optimization.org/tutorials/"
# VAMOS's documentation tutorials a studio tutorial can pair with, and their pages.
VAMOS_TUTORIALS: Final = {
    "T01": "t01-first-result",
    "T02": "t02-constrained-problem",
    "T03": "t03-pareto-decision",
    "T06": "t06-fair-study",
    "T07": "t07-quality-and-budget",
    "T08": "t08-study-report",
}


class TutorialLevel(Enum):
    """How much a tutorial assumes of the reader."""

    BASIC = "Basic"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"


@dataclass(slots=True, frozen=True)
class Tutorial:
    """An interactive tutorial of VAMOS-Studio.

    Attributes:
        slug: Its topic, which identifies it (e.g. "solving").
        number: Its number (e.g. "S2") when it is written, None while it is only planned.
        title: Its title.
        level: Its level.
        summary: One-sentence description of what it teaches.
        pairs_with: VAMOS documentation tutorials it pairs with (keys of `VAMOS_TUTORIALS`).
        notebook: The file name of its companion notebook in `vamos_studio/notebooks/`, if any.
    """

    slug: str
    number: str | None
    title: str
    level: TutorialLevel
    summary: str
    pairs_with: tuple[str, ...] = ()
    notebook: str | None = None

    @property
    def available(self) -> bool:
        """Whether its content exists in this app: only a written tutorial has a number."""
        return self.number is not None

    @property
    def label(self) -> str:
        """Its number and title (e.g. "S2. Solving a problem"), or the title alone."""
        return f"{self.number}. {self.title}" if self.number else self.title


@dataclass(slots=True, frozen=True)
class TutorialStep:
    """One step of a tutorial.

    Attributes:
        title: The step's title.
        render: Renders the step's content.
    """

    title: str
    render: Callable[[], None]


def vamos_tutorial_url(number: str) -> str:
    """The page of one of VAMOS's documentation tutorials (e.g. "T01")."""
    return f"{VAMOS_TUTORIALS_URL}{VAMOS_TUTORIALS[number]}/"


_BASIC = TutorialLevel.BASIC
_MID = TutorialLevel.INTERMEDIATE
_ADVANCED = TutorialLevel.ADVANCED

TUTORIALS: Final[tuple[Tutorial, ...]] = (
    Tutorial(
        "tour",
        "S1",
        "A tour of VAMOS-Studio",
        _BASIC,
        "What the studio does for you, how it runs VAMOS, its pages and where it keeps the runs.",
    ),
    Tutorial(
        "solving",
        "S2",
        "Solving a problem",
        _BASIC,
        "Run NSGA-II on ZDT1, read its result, change its configuration and try a harder "
        "problem, then do it yourself in New run.",
        ("T01",),
        "s2_solving.ipynb",
    ),
    Tutorial(
        "reading_fronts",
        "S3",
        "Reading a front and its quality indicators",
        _BASIC,
        "What a Pareto front looks like, how quality indicators measure an approximation of it, "
        "and how to read them in a run.",
        ("T07",),
        "s3_reading_fronts.ipynb",
    ),
    Tutorial(
        "parameter_spaces",
        "S4",
        "Exploring a parameter space",
        _BASIC,
        "Read the parameter space of NSGA-II as a tree, see which parameters each choice "
        "activates, and write a configuration as a command line.",
        (),
        "s4_parameter_spaces.ipynb",
    ),
    Tutorial(
        "comparing_algorithms",
        None,
        "Comparing algorithms with independent runs",
        _MID,
        "Series of runs with consecutive seeds, their aggregate and summary statistics, and the "
        "best run.",
        ("T06",),
    ),
    Tutorial(
        "many_objectives",
        None,
        "Many objectives",
        _MID,
        "DTLZ with four to eight objectives in parallel coordinates, and the algorithms designed "
        "for them.",
    ),
    Tutorial(
        "front_to_decision",
        None,
        "From a front to a decision",
        _MID,
        "The knee and the extremes of a front, its solutions, and the result of an archive.",
        ("T03",),
    ),
    Tutorial(
        "without_reference_front",
        None,
        "Problems without a reference front",
        _MID,
        "Approximate fronts built from runs, their versions, and binary problems.",
    ),
    Tutorial(
        "reproducibility",
        None,
        "Reproducibility",
        _ADVANCED,
        "A run's artifact, its verification and the specification VAMOS resolved, to repeat it "
        "exactly.",
        ("T06", "T08"),
    ),
    Tutorial(
        "long_running_runs",
        None,
        "Long-running runs",
        _ADVANCED,
        "Background runs: leaving and coming back, stopping keeping the results, cancelling, the "
        "history and the trash.",
    ),
    Tutorial(
        "automatic_configuration",
        None,
        "Automatic configuration",
        _ADVANCED,
        "Tune an algorithm for a family of problems and analyze what the tuning found.",
    ),
    Tutorial(
        "constrained_problems",
        None,
        "Constrained problems",
        _ADVANCED,
        "Feasibility, constraint-handling techniques and the algorithms designed for constraints.",
        ("T02",),
    ),
)


def tutorials_by_level(level: TutorialLevel) -> list[Tutorial]:
    """The tutorials of a level, in catalogue order."""
    return [tutorial for tutorial in TUTORIALS if tutorial.level is level]


def tutorial(slug: str) -> Tutorial:
    """The tutorial of a topic.

    Raises:
        KeyError: If there is none.
    """
    for item in TUTORIALS:
        if item.slug == slug:
            return item
    raise KeyError(slug)
