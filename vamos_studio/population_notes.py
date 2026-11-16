"""What New run says about an algorithm's population and its fit to the number of objectives.

The population a configuration runs with is not always its `pop_size`: MOEA/D's follows its weight
vectors, NSGA-III's reference directions are the largest lattice that fits the population, and
RVEA has no population of its own (its lattice). Some algorithms are also known to struggle with
four or more objectives. Each note is a level ("caption", "info" or "warning") and a text.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final, Literal

from vamos_studio.backend.upstream.vamos_bridge import (
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
    size = weight_population(asked, n_obj)
    if not weight_populations(n_obj):
        divisions = lattice(asked, n_obj)[0]
        return (
            "info",
            f"Neither jMetal nor VAMOS has a weight vector file for {n_obj} objectives: MOEA/D "
            f"uses VAMOS's Das-Dennis lattice of {divisions} divisions, {size:,} vectors, the "
            f"largest that fits the population of {asked}, and runs with that population.",
        )
    sizes = ", ".join(str(item) for item in weight_populations(n_obj))
    return (
        "caption",
        f"MOEA/D reads its {size} weight vectors from {weight_file(asked, n_obj)}, jMetal's file "
        "shipped with VAMOS, as jMetal and Evolver do"
        + ("." if size == asked else f": there is none for {asked}.")
        + f" Populations with a file for {n_obj} objectives: {sizes}.",
    )


def _rvea_notes(values: Mapping[str, Any], n_obj: int) -> list[Note]:
    size = population(values, "rvea", n_obj)
    divisions = int(values["n_partitions"])
    notes: list[Note] = [
        (
            "caption",
            f"RVEA runs with {size:,} solutions, one per reference vector: the Das-Dennis lattice "
            f"of {divisions} divisions for {n_obj} objectives.",
        )
    ]
    if size < SMALL_POPULATION:
        more = (
            "more divisions give a larger lattice (VAMOS allows up to 12)"
            if divisions < 12
            else f"VAMOS's RVEA allows at most 12 divisions, so with {n_obj} objectives it "
            "cannot have more"
        )
        notes.append(("warning", f"A population of {size} is small: {more}."))
    elif size > LARGE_POPULATION:
        notes.append(
            (
                "warning",
                f"A population of {size:,} is large: every generation evaluates that many "
                "solutions. Fewer divisions give a smaller lattice (VAMOS allows 4 to 12).",
            )
        )
    return notes
