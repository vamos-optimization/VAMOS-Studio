"""VAMOS's built-in grammars as the studio's forms, and a configuration as a VAMOS configuration.

VAMOS 1.4 ships its tuning spaces as grammars (``vamos/resources/parameter_spaces``, schema
``vamos.parameter-space`` 1.0.0), the model this studio prototyped
(docs/design/parameter-spaces.md).
The studio reads them as they ship and adds a layer of its own (``spaces/studio.yaml``):

- ``pop_size``, which VAMOS treats as a run setting rather than a tuned parameter;
- ``archive_subset_selection`` under an unbounded external archive, which the studio applies itself
  (``vamos_studio/backend/subset.py``);
- the labels and descriptions of the parameters, for the forms.

VAMOS builds the algorithm's configuration from an assignment of the grammar's values
(``config_from_assignment``), which also turns the mutation probability factor into a probability,
gives MOEA/D the largest population up to ``pop_size`` with weight vectors (a complete Das-Dennis
lattice or one of jMetal's files) and RVEA the largest lattice up to ``pop_size``.
"""

from __future__ import annotations

import copy
import dataclasses
import math
from collections.abc import Mapping
from functools import cache
from importlib.resources import files
from typing import Any, Final

import yaml
from vamos.engine.algorithm.components.weight_vectors import largest_weighted_population
from vamos.engine.algorithm.config.types import AlgorithmConfigProtocol
from vamos.engine.tuning.racing.bridge_assignments import config_from_assignment

from .parameter_space import Configuration, ParameterSpace, space_from_dict

SPACES_PACKAGE: Final = "vamos_studio.backend.upstream.spaces"
VAMOS_SPACES: Final = files("vamos") / "resources" / "parameter_spaces"
VAMOS_WEIGHTS: Final = files("vamos") / "resources" / "weights"
# The grammars the studio offers, as (algorithm, encoding).
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
    ("nsgaiii", "real"),
)
# Parameters of the studio's layer that VAMOS's grammars do not have.
STUDIO_ONLY_PARAMETERS: Final = frozenset({"pop_size", "archive_subset_selection"})
# The configuration field that takes a file of reference vectors, by algorithm (VAMOS 1.5).
VECTOR_FIELDS: Final = {"nsgaiii": "reference_directions", "rvea": "reference_vectors"}
# Algorithms whose population depends on the problem's number of objectives.
_NEEDS_N_OBJ: Final = frozenset({"moead", "rvea", "nsgaiii"})


def space_name(algorithm: str, encoding: str) -> str:
    """The studio's name of the grammar of `algorithm` for `encoding` (e.g. "nsgaii_real")."""
    return f"{algorithm}_{encoding}"


def vamos_space_name(algorithm: str, encoding: str) -> str:
    """VAMOS's name of the same grammar (e.g. "nsgaii", "nsgaii_binary")."""
    return algorithm if encoding == "real" else f"{algorithm}_{encoding}"


@cache
def studio_layer() -> dict[str, Any]:
    """The studio's layer over VAMOS's grammars (spaces/studio.yaml)."""
    text = files(SPACES_PACKAGE).joinpath("studio.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(text)


@cache
def builtin_space(algorithm: str, encoding: str) -> ParameterSpace | None:
    """VAMOS's grammar of `algorithm` for `encoding` with the studio's layer, if offered."""
    if (algorithm, encoding) not in BUILTIN_SPACES:
        return None
    text = VAMOS_SPACES.joinpath(f"{vamos_space_name(algorithm, encoding)}.yaml")
    document = yaml.safe_load(text.read_text(encoding="utf-8"))
    return space_from_dict(with_studio_layer(document, algorithm, encoding))


def with_studio_layer(document: dict[str, Any], algorithm: str, encoding: str) -> dict[str, Any]:
    """A VAMOS grammar document with the studio's population, subset selection and labels."""
    layer = studio_layer()
    document = copy.deepcopy(document)
    name = space_name(algorithm, encoding)
    document["name"] = name
    population = dict(layer["pop_size"])
    population["description"] = layer["population_descriptions"].get(
        algorithm, population["description"]
    )
    document["parameters"] = {"pop_size": population, **document["parameters"]}
    archive = document["parameters"].get("external_archive")
    if archive is not None and "unbounded" in archive.get("values", {}):
        unbounded = archive["values"]["unbounded"] or {}
        unbounded.setdefault("conditional_parameters", {})["archive_subset_selection"] = dict(
            layer["archive_subset_selection"]
        )
        archive["values"]["unbounded"] = unbounded
    labels = layer["labels"] | layer["space_labels"].get(name, {})
    _label(document["parameters"], labels)
    return document


def _label(parameters: dict[str, Any], labels: Mapping[str, Mapping[str, str]]) -> None:
    for parameter_name, parameter in parameters.items():
        for key, text in labels.get(parameter_name, {}).items():
            if text and not parameter.get(key):
                parameter[key] = text
        _label(parameter.get("global_sub_parameters") or {}, labels)
        values = parameter.get("values")
        if isinstance(values, dict):
            for production in values.values():
                _label((production or {}).get("conditional_parameters") or {}, labels)


def to_vamos_assignment(configuration: Configuration, n_obj: int | None = None) -> dict[str, Any]:
    """The assignment VAMOS's `config_from_assignment` builds the configuration from.

    The grammar's values, without the studio's subset selection, with the population and, for the
    algorithms whose population depends on it, the problem's number of objectives.
    """
    assignment = {
        name: value
        for name, value in configuration.values.items()
        if name != "archive_subset_selection"
    }
    if configuration.space.algorithm in _NEEDS_N_OBJ:
        assignment["n_obj"] = n_obj or 2
    return assignment


def to_algorithm_config(
    configuration: Configuration,
    n_var: int | None = None,
    n_obj: int | None = None,
    vectors: tuple[str, int] | None = None,
) -> AlgorithmConfigProtocol:
    """The VAMOS algorithm configuration that `configuration` describes for a problem.

    Args:
        configuration: A configuration of a built-in grammar.
        n_var: The problem's number of variables (VAMOS resolves the mutation probability factor
            when the run starts; kept for the callers that pass it).
        n_obj: The problem's number of objectives: MOEA/D, RVEA and NSGA-III need it.
        vectors: For NSGA-III and RVEA, a file of reference vectors and how many it has: they
            start from it instead of a lattice, with one individual per vector.
    """
    del n_var
    space = configuration.space
    config = config_from_assignment(
        vamos_space_name(space.algorithm, space.encoding),
        to_vamos_assignment(configuration, n_obj),
    )
    if vectors is None:
        return config
    if space.algorithm not in VECTOR_FIELDS:
        raise ValueError(f"{space.algorithm} does not take a file of reference vectors.")
    path, size = vectors
    return dataclasses.replace(
        config, pop_size=size, **{VECTOR_FIELDS[space.algorithm]: {"path": path}}
    )


def population(
    values: Mapping[str, Any], algorithm: str, n_obj: int, vectors: int | None = None
) -> int:
    """The population a configuration runs with on a problem of `n_obj` objectives.

    With a file of `vectors` reference vectors (NSGA-III and RVEA), one individual per vector.
    Otherwise MOEA/D's, with three or more objectives, is the largest up to `pop_size` with weight
    vectors; RVEA's, its largest Das-Dennis lattice up to `pop_size` (or the lattice of
    `n_partitions`, for a run saved before VAMOS 1.4); the others', `pop_size`.
    """
    if vectors is not None:
        return vectors
    if algorithm == "rvea" and "n_partitions" in values:
        return math.comb(int(values["n_partitions"]) + n_obj - 1, n_obj - 1)
    pop_size = int(values["pop_size"])
    if algorithm == "rvea":
        return lattice(pop_size, n_obj)[1]
    if algorithm == "moead":
        return weight_population(pop_size, n_obj)
    return pop_size


def lattice(pop_size: int, n_obj: int) -> tuple[int, int]:
    """The largest Das-Dennis lattice with at most `pop_size` vectors: (divisions, vectors).

    With fewer solutions than objectives, the lattice of one division (`n_obj` vectors).
    """
    divisions = 1
    while math.comb(divisions + 1 + n_obj - 1, n_obj - 1) <= pop_size:
        divisions += 1
    return divisions, math.comb(divisions + n_obj - 1, n_obj - 1)


def exact_divisions(size: int, n_obj: int) -> int | None:
    """The divisions of the complete Das-Dennis lattice with exactly `size` vectors, if any."""
    divisions = 1
    while (vectors := math.comb(divisions + n_obj - 1, n_obj - 1)) < size:
        divisions += 1
    return divisions if vectors == size else None


@cache
def weight_populations(n_obj: int) -> tuple[int, ...]:
    """The populations with a jMetal weight vector file that VAMOS ships, for `n_obj` objectives."""
    prefix = f"W{n_obj}D_"
    return tuple(
        sorted(
            int(path.name[len(prefix) : -len(".dat")])
            for path in VAMOS_WEIGHTS.iterdir()
            if path.name.startswith(prefix) and path.name.endswith(".dat")
        )
    )


def weight_population(pop_size: int, n_obj: int) -> int:
    """MOEA/D's population for `pop_size`: the largest up to it with weight vectors, as VAMOS runs.

    With two objectives any size works. With more, a complete Das-Dennis lattice or one of jMetal's
    files; with fewer solutions than objectives, `pop_size` (VAMOS rejects it).
    """
    if n_obj < 3 or pop_size < n_obj:
        return pop_size
    return largest_weighted_population(pop_size, n_obj)


def weight_file(pop_size: int, n_obj: int) -> str | None:
    """The jMetal file MOEA/D reads its weights from for `pop_size`, or None.

    None with two objectives (uniform weights) and when the population is a complete Das-Dennis
    lattice, which VAMOS prefers to a file of the same size.
    """
    if n_obj < 3:
        return None
    size = weight_population(pop_size, n_obj)
    if exact_divisions(size, n_obj) is not None or size not in weight_populations(n_obj):
        return None
    return f"W{n_obj}D_{size}.dat"
