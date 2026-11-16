"""The built-in grammars, and the step from a configuration to a VAMOS algorithm configuration.

Upstream target: the per-algorithm builders of ``vamos.algorithms`` that turn a configuration
into ``NSGAIIConfig`` and the rest (today ``config_from_assignment`` plays this role), and the
grammars shipped as VAMOS resources. Status: local. Design: ``docs/design/parameter-spaces.md``.

The grammars rename a few parameters of VAMOS 1.2's tuning spaces (changes M1, M2 and M8 of the
design); `to_vamos_assignment` maps them back, so VAMOS builds the configuration itself. Two
algorithms need more than that:

- MOEA/D: its mutation probability is a factor of 1/n (M8), and with three or more objectives it
  reads its weight vectors from jMetal's files shipped with VAMOS (`W<m>D_<population>.dat`), as
  jMetal and Evolver do: the population is one with a file. VAMOS 1.1 read those files only
  when given their directory; without it, its default generated a Das-Dennis lattice, so a
  population of 100 differed from jMetal's. VAMOS 1.2 reads them by default; the studio still
  names the directory, which gives the same vectors.
- SMS-EMOA: VAMOS's tuning bridge (1.1 and 1.2) always selects by tournament with a reference
  point offset of 0.1, while its default selects at random with an offset of 1.0, so the studio
  builds `SMSEMOAConfig` itself, with VAMOS's builder and VAMOS's helpers for the operators.
"""

from __future__ import annotations

import dataclasses
import math
import re
from collections.abc import Mapping
from functools import cache
from importlib.resources import files
from pathlib import Path
from typing import Any, Final

from vamos.algorithms import SMSEMOAConfig
from vamos.engine.algorithm.config.types import AlgorithmConfigProtocol
from vamos.engine.tuning.racing._bridge_assignment_shared import (
    apply_initializer,
    apply_optional_external_archive,
    apply_optional_repair,
    extend_crossover_params,
    extend_mutation_params,
)
from vamos.engine.tuning.racing.bridge_assignments import config_from_assignment

from .parameter_space import Configuration, ParameterSpace, space_from_yaml

SPACES_PACKAGE: Final = "vamos_studio.backend.upstream.spaces"
# Grammars shipped with the studio, as (algorithm, encoding).
BUILTIN_SPACES: Final = (
    ("nsgaii", "real"),
    ("nsgaii", "binary"),
    ("moead", "real"),
    ("moead", "binary"),
    ("smsemoa", "real"),
    ("smsemoa", "binary"),
    ("agemoea", "real"),
    ("rvea", "real"),
    ("spea2", "real"),
)
# Algorithms whose grammar gives the mutation probability as a factor of 1/n (M8) and whose VAMOS
# space names polynomial mutation "pm": VAMOS builds them from the converted assignment.
_FACTOR_ALGORITHMS: Final = frozenset({"agemoea", "rvea", "spea2"})

# Parameters of the grammars that VAMOS does not have: the studio applies them itself.
STUDIO_ONLY_PARAMETERS: Final = frozenset({"archive_subset_selection"})
# Parameters of the SMS-EMOA grammars that its constructor applies (not in VAMOS's space).
SMSEMOA_ONLY_PARAMETERS: Final = frozenset({"selection", "reference_point_offset"})
# M2: parameters duplicated per production, and the single VAMOS parameter they come from.
_RENAMED_TO_VAMOS: Final = {
    "polynomial_eta": "mutation_eta",
    "linked_polynomial_eta": "mutation_eta",
}


def space_name(algorithm: str, encoding: str) -> str:
    """The name of the grammar of `algorithm` for `encoding` (e.g. "nsgaii_real")."""
    return f"{algorithm}_{encoding}"


@cache
def builtin_space(algorithm: str, encoding: str) -> ParameterSpace | None:
    """The grammar of `algorithm` for `encoding` shipped with the studio, if there is one."""
    if (algorithm, encoding) not in BUILTIN_SPACES:
        return None
    resource = files(SPACES_PACKAGE).joinpath(f"{space_name(algorithm, encoding)}.yaml")
    return space_from_yaml(resource.read_text(encoding="utf-8"))


def to_vamos_assignment(configuration: Configuration) -> dict[str, Any]:
    """The configuration in the vocabulary of VAMOS 1.2's tuning spaces.

    Args:
        configuration: A configuration of a built-in grammar.

    Returns:
        The assignment that VAMOS's `config_from_assignment` expects.
    """
    assignment: dict[str, Any] = {}
    for name, value in configuration.values.items():
        if name in STUDIO_ONLY_PARAMETERS:
            continue
        if name == "external_archive":
            assignment.update(_archive_assignment(str(value)))
        else:
            assignment[_RENAMED_TO_VAMOS.get(name, name)] = value
    return assignment


def to_algorithm_config(
    configuration: Configuration, n_var: int | None = None, n_obj: int | None = None
) -> AlgorithmConfigProtocol:
    """The VAMOS algorithm configuration that `configuration` describes for a problem.

    Args:
        configuration: A configuration of a built-in grammar.
        n_var: The problem's number of variables: MOEA/D and SMS-EMOA need it to turn the
            mutation probability factor into a probability.
        n_obj: The problem's number of objectives: MOEA/D needs it for its population.

    Raises:
        ValueError: If the algorithm needs `n_var` and it is not given.
    """
    space = configuration.space
    vamos_space = space.algorithm if space.encoding == "real" else space.name
    assignment = to_vamos_assignment(configuration)
    if space.algorithm == "moead":
        assignment["mutation_prob"] = mutation_probability(assignment, n_var)
        assignment["pop_size"] = weight_population(int(assignment["pop_size"]), n_obj or 2)
        return with_weight_files(config_from_assignment(vamos_space, assignment), n_obj or 2)
    if space.algorithm == "smsemoa":
        return smsemoa_config(assignment, n_var)
    if space.algorithm in _FACTOR_ALGORITHMS:
        assignment["mutation_prob"] = mutation_probability(assignment, n_var)
        if assignment.get("mutation") == "polynomial":
            assignment["mutation"] = "pm"
        if space.algorithm == "rvea":
            assignment["n_obj"] = n_obj or 2  # its population is the lattice for these objectives
    return config_from_assignment(vamos_space, assignment)


def population(values: Mapping[str, Any], algorithm: str, n_obj: int) -> int:
    """The population a configuration runs with on a problem of `n_obj` objectives.

    RVEA's is its Das-Dennis lattice of `n_partitions` divisions; MOEA/D's, with three or more
    objectives, one with a weight vector file (see `weight_population`); the others', `pop_size`.
    """
    if algorithm == "rvea":
        return math.comb(int(values["n_partitions"]) + n_obj - 1, n_obj - 1)
    pop_size = int(values["pop_size"])
    if algorithm == "moead":
        return weight_population(pop_size, n_obj)
    return pop_size


def mutation_probability(assignment: dict[str, Any], n_var: int | None) -> float:
    """M8: the probability of mutating each variable, from its factor of 1/n."""
    if n_var is None:
        raise ValueError("The mutation probability needs the problem's number of variables.")
    return float(assignment.pop("mutation_prob_factor")) / n_var


_WEIGHT_FILE: Final = re.compile(r"W(\d+)D_(\d+)\.dat")


def weights_directory() -> Path:
    """The directory of jMetal's weight vector files that VAMOS ships."""
    return Path(str(files("vamos") / "resources" / "weights"))


@cache
def weight_populations(n_obj: int) -> tuple[int, ...]:
    """The population sizes there is a weight vector file for, with `n_obj` objectives."""
    sizes = []
    for path in weights_directory().iterdir():
        match = _WEIGHT_FILE.fullmatch(path.name)
        if match and int(match.group(1)) == n_obj:
            sizes.append(int(match.group(2)))
    return tuple(sorted(sizes))


def lattice(pop_size: int, n_obj: int) -> tuple[int, int]:
    """The largest Das-Dennis lattice with at most `pop_size` vectors: (divisions, vectors).

    With fewer solutions than objectives, the lattice of one division (`n_obj` vectors).
    """
    divisions = 1
    while math.comb(divisions + 1 + n_obj - 1, n_obj - 1) <= pop_size:
        divisions += 1
    return divisions, math.comb(divisions + n_obj - 1, n_obj - 1)


def weight_population(pop_size: int, n_obj: int) -> int:
    """MOEA/D's population for `pop_size`: one with a weight vector file, as in jMetal.

    With two objectives the weights are uniform and any size works. With more, the size has a
    file if there is one; otherwise the largest size with a file up to it, or the smallest. Without
    any file for `n_obj` objectives, the size of the largest Das-Dennis lattice up to `pop_size`.
    """
    if n_obj < 3:
        return pop_size
    sizes = weight_populations(n_obj)
    if not sizes:
        return lattice(pop_size, n_obj)[1]
    fitting = [size for size in sizes if size <= pop_size]
    return fitting[-1] if fitting else sizes[0]


def weight_file(pop_size: int, n_obj: int) -> str | None:
    """The weight vector file MOEA/D reads for a population, or None (two objectives, or none)."""
    if n_obj < 3 or not weight_populations(n_obj):
        return None
    return f"W{n_obj}D_{weight_population(pop_size, n_obj)}.dat"


def with_weight_files(config: Any, n_obj: int) -> Any:
    """MOEA/D's weight vectors with three or more objectives: jMetal's file, or else a lattice.

    The lattice is VAMOS's Das-Dennis lattice of exactly the configuration's population, which
    `weight_population` has made the size of one.
    """
    if n_obj < 3:
        return config
    if not weight_populations(n_obj):
        divisions = lattice(int(config.pop_size), n_obj)[0]
        return dataclasses.replace(config, weight_vectors={"path": None, "divisions": divisions})
    path = str(weights_directory())
    return dataclasses.replace(config, weight_vectors={"path": path, "divisions": None})


def smsemoa_config(assignment: dict[str, Any], n_var: int | None) -> AlgorithmConfigProtocol:
    """SMS-EMOA's configuration, built with VAMOS's builder and its helpers for the operators."""
    builder = SMSEMOAConfig.builder()
    pop_size = int(assignment["pop_size"])
    builder.pop_size(pop_size)
    apply_initializer(builder, assignment, pop_size)
    crossover = str(assignment["crossover"])
    crossover_params: dict[str, Any] = {}
    if "crossover_prob" in assignment:
        crossover_params["prob"] = float(assignment["crossover_prob"])
    extend_crossover_params(crossover, assignment, crossover_params)
    builder.crossover(crossover, **crossover_params)
    mutation = str(assignment["mutation"])
    mutation_params: dict[str, Any] = {"prob": mutation_probability(assignment, n_var)}
    extend_mutation_params(mutation, assignment, mutation_params)
    builder.mutation(mutation, **mutation_params)
    if assignment["selection"] == "tournament":
        builder.selection("tournament", size=int(assignment["selection_pressure"]))
    else:
        builder.selection("random")
    builder.reference_point(offset=float(assignment["reference_point_offset"]), adaptive=True)
    apply_optional_repair(builder, assignment)
    apply_optional_external_archive(builder, assignment, pop_size)
    return builder.build()


def _archive_assignment(choice: str) -> dict[str, bool]:
    """M1: the external_archive choice as VAMOS's two archive switches."""
    if choice == "none":
        return {"use_external_archive": False}
    return {"use_external_archive": True, "archive_unbounded": choice == "unbounded"}
