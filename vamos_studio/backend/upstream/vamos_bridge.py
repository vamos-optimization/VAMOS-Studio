"""The built-in grammars, and the step from a configuration to a VAMOS algorithm configuration.

Upstream target: the per-algorithm builders of ``vamos.algorithms`` that turn a configuration
into ``NSGAIIConfig`` and the rest (today ``config_from_assignment`` plays this role), and the
grammars shipped as VAMOS resources. Status: local. Design: ``docs/design/parameter-spaces.md``.

The grammars rename a few parameters of VAMOS 1.1's tuning spaces (changes M1 and M2 of the
design); `to_vamos_assignment` maps them back, so VAMOS builds the configuration itself.
"""

from __future__ import annotations

from functools import cache
from importlib.resources import files
from typing import Any, Final

from vamos.engine.algorithm.config.types import AlgorithmConfigProtocol
from vamos.engine.tuning.racing.bridge_assignments import config_from_assignment

from .parameter_space import Configuration, ParameterSpace, space_from_yaml

SPACES_PACKAGE: Final = "vamos_studio.backend.upstream.spaces"
# Grammars shipped with the studio, as (algorithm, encoding).
BUILTIN_SPACES: Final = (("nsgaii", "real"),)

# Parameters of the grammars that VAMOS does not have: the studio applies them itself.
STUDIO_ONLY_PARAMETERS: Final = frozenset({"archive_subset_selection"})
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
    """The configuration in the vocabulary of VAMOS 1.1's tuning spaces.

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


def to_algorithm_config(configuration: Configuration) -> AlgorithmConfigProtocol:
    """The VAMOS algorithm configuration that `configuration` describes."""
    space = configuration.space
    vamos_space = space.algorithm if space.encoding == "real" else space.name
    return config_from_assignment(vamos_space, to_vamos_assignment(configuration))


def _archive_assignment(choice: str) -> dict[str, bool]:
    """M1: the external_archive choice as VAMOS's two archive switches."""
    if choice == "none":
        return {"use_external_archive": False}
    return {"use_external_archive": True, "archive_unbounded": choice == "unbounded"}
