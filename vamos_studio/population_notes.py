"""What New run says about an algorithm's population and its fit to the number of objectives.

The population a configuration runs with is not always its `pop_size`: MOEA/D's follows its weight
vectors, NSGA-III's reference directions are the largest lattice that fits the population, and
RVEA's population is the largest lattice that fits its `pop_size`. Some algorithms are also known
to struggle with four or more objectives. Each note is a level ("caption", "info" or "warning")
and a text.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any, Final, Literal

from vamos_studio.backend.upstream.vamos_bridge import (
    exact_divisions,
    lattice,
    population,
    weight_file,
    weight_population,
    weight_populations,
)

Level = Literal["caption", "info", "warning"]
Note = tuple[Level, str]

# From this number of objectives on, Pareto-based algorithms are flagged.
MANY_OBJECTIVES: Final = 4
# RVEA populations outside these bounds get a warning.
SMALL_POPULATION: Final = 50
LARGE_POPULATION: Final = 1000
# Algorithms designed for many objectives, named in the warnings.
MANY_OBJECTIVE_ALGORITHMS: Final = "NSGA-III, MOEA/D, RVEA or AGE-MOEA"


def population_notes(algorithm: str, values: Mapping[str, Any], n_obj: int) -> list[Note]:
    """The notes on the population of `algorithm` with `values`, for `n_obj` objectives."""
    if algorithm == "moead" and n_obj >= 3:
        return [_moead_note(int(values["pop_size"]), n_obj)]
    if algorithm == "nsgaiii":
        divisions, directions = lattice(int(values["pop_size"]), n_obj)
        return [
            (
                "caption",
                f"NSGA-III uses {directions:,} reference directions, the largest Das-Dennis "
                f"lattice that fits its population of {int(values['pop_size'])} ({divisions} "
                f"divisions for {n_obj} objectives).",
            )
        ]
    if algorithm == "rvea":
        return _rvea_notes(values, n_obj)
    return []


def objective_notes(algorithm: str, n_obj: int) -> list[Note]:
    """Warnings about `algorithm` with `n_obj` objectives, if it is not suited to them."""
    if n_obj < MANY_OBJECTIVES:
        return []
    if algorithm in ("nsgaii", "spea2"):
        density = "crowding distance" if algorithm == "nsgaii" else "k-th nearest neighbor"
        name = "NSGA-II" if algorithm == "nsgaii" else "SPEA2"
        return [
            (
                "warning",
                f"{name} ranks solutions by Pareto dominance and {density}, which lose selection "
                f"pressure with {n_obj} objectives (most solutions become non-dominated). "
                f"{MANY_OBJECTIVE_ALGORITHMS} are designed for many objectives.",
            )
        ]
    if algorithm == "smsemoa":
        return [
            (
                "warning",
                f"SMS-EMOA computes hypervolume contributions at every step, whose cost grows "
                f"exponentially with the number of objectives: with {n_obj} the run can be very "
                f"slow. {MANY_OBJECTIVE_ALGORITHMS} are faster with many objectives.",
            )
        ]
    return []


def _moead_note(asked: int, n_obj: int) -> Note:
    if asked < n_obj:
        return (
            "warning",
            f"MOEA/D needs at least one weight vector per objective: a population of at least "
            f"{n_obj} for {n_obj} objectives.",
        )
    size = weight_population(asked, n_obj)
    shortfall = "." if size == asked else f", the largest population up to {asked} that has them."
    file = weight_file(asked, n_obj)
    if file is not None:
        return (
            "caption",
            f"MOEA/D reads its {size} weight vectors from {file}, jMetal's file shipped with "
            f"VAMOS, as jMetal and Evolver do{shortfall}",
        )
    divisions = exact_divisions(size, n_obj)
    files = weight_populations(n_obj)
    return (
        "caption" if size == asked else "info",
        f"MOEA/D's weight vectors are VAMOS's Das-Dennis lattice of {divisions} divisions, "
        f"{size:,} vectors{shortfall}"
        + (
            f" jMetal's weight files for {n_obj} objectives have "
            + ", ".join(str(item) for item in files)
            + " vectors."
            if files
            else ""
        ),
    )


def _rvea_notes(values: Mapping[str, Any], n_obj: int) -> list[Note]:
    size = population(values, "rvea", n_obj)
    if "n_partitions" in values:  # a run saved before VAMOS 1.4
        divisions = int(values["n_partitions"])
        asked = size
    else:
        asked = int(values["pop_size"])
        divisions = lattice(asked, n_obj)[0]
    notes: list[Note] = [
        (
            "caption",
            f"RVEA runs with {size:,} solutions, one per reference vector: the largest Das-Dennis "
            f"lattice up to {asked}, {divisions} divisions for {n_obj} objectives.",
        )
    ]
    if size < SMALL_POPULATION:
        following = math.comb(divisions + 1 + n_obj - 1, n_obj - 1)
        notes.append(
            (
                "warning",
                f"A population of {size} is small: the next lattice for {n_obj} objectives has "
                f"{following:,} vectors, and needs a population of at least that.",
            )
        )
    elif size > LARGE_POPULATION:
        notes.append(
            (
                "warning",
                f"A population of {size:,} is large: every generation evaluates that many "
                "solutions. A smaller population gives a smaller lattice.",
            )
        )
    return notes
