"""The configuration form of a run: which parameters it shows, and what differs from the default.

The form keeps a value for every parameter of the grammar, active or not, so that switching a
categorical value back restores what its parameters had; it shows only the active ones. Pure
functions over the grammar model, with no Streamlit dependency.

The idea follows Transept's and Evolver-Studio's parameter forms (transept/parameter_form.py,
evolver_studio/parameter_form.py), rebuilt on the grammar of docs/design/parameter-spaces.md.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass

from vamos_studio.backend.upstream.parameter_space import (
    Configuration,
    Parameter,
    ParameterSpace,
    Scalar,
    same_value,
)


@dataclass(slots=True, frozen=True)
class FormField:
    """A parameter shown in the form.

    Attributes:
        parameter: The parameter.
        depth: How deep it is in the tree (0 at the root).
        parent: The categorical parameter it hangs from, or None at the root.
    """

    parameter: Parameter
    depth: int
    parent: str | None


@dataclass(slots=True, frozen=True)
class Change:
    """An active parameter whose value differs from its default.

    Attributes:
        name: The parameter.
        default: Its default value.
        value: Its value in the configuration.
    """

    name: str
    default: Scalar
    value: Scalar


def active_fields(space: ParameterSpace, values: Mapping[str, object]) -> list[FormField]:
    """The parameters active for `values`, depth-first, with their depth and parent."""
    return list(_walk(space.parameters, values, 0, None))


def configuration_of(space: ParameterSpace, values: Mapping[str, object]) -> Configuration:
    """The configuration that `values` (a value for every parameter) derives."""
    return space.configuration(values, complete=True)


def changes(configuration: Configuration) -> list[Change]:
    """The active parameters of `configuration` whose value is not their default."""
    space = configuration.space
    return [
        Change(name, space.parameter(name).default, value)
        for name, value in configuration.values.items()
        if not same_value(value, space.parameter(name).default)
    ]


def with_configuration(
    space: ParameterSpace, configuration_values: Mapping[str, object]
) -> dict[str, object]:
    """A value for every parameter: the defaults, overridden by a stored configuration's values."""
    return space.default_values() | dict(configuration_values)


def _walk(
    nodes: tuple[Parameter, ...], values: Mapping[str, object], depth: int, parent: str | None
) -> Iterator[FormField]:
    for node in nodes:
        yield FormField(node, depth, parent)
        value = values.get(node.name, node.default)
        if node.type == "categorical" and node.contains(value):
            yield from _walk(node.active_children(value), values, depth + 1, node.name)
