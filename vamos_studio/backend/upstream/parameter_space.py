"""Parameter spaces as grammars, and configurations as their derivations.

Upstream target: ``vamos.algorithms.parameter_space`` and the ``vamos.parameter-space`` and
``vamos.parameter-configuration`` schemas. Status: local. Design:
``docs/design/parameter-spaces.md``.

A space is a strict grammar: a categorical parameter chooses between productions, one per value,
and each production holds the parameters its value activates; a categorical parameter may also
have global sub-parameters, present whatever its value; numeric and boolean parameters are
terminals. Every parameter has exactly one place in the tree and a default, so the defaults form
the default configuration. This module does not import VAMOS.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Literal, TypeAlias

import yaml

SPACE_SCHEMA: Final = "vamos.parameter-space"
CONFIGURATION_SCHEMA: Final = "vamos.parameter-configuration"
SCHEMA_VERSION: Final = "1.0.0"

Scalar: TypeAlias = str | int | float | bool
ParameterType: TypeAlias = Literal["categorical", "real", "int", "boolean"]
PARAMETER_TYPES: Final = ("categorical", "real", "int", "boolean")
ROLES: Final = ("structural", "operator", "operator_rate", "population", "adaptive")
_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


class ParameterSpaceError(ValueError):
    """A parameter space or a configuration that breaks the grammar's rules."""


def same_value(left: object, right: object) -> bool:
    """Whether two parameter values are equal, telling booleans apart from numbers.

    Args:
        left: A parameter value.
        right: Another parameter value.

    Returns:
        True when both are booleans and equal, or neither is a boolean and they compare equal.
    """
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    return left == right


@dataclass(slots=True, frozen=True)
class Production:
    """One value of a categorical parameter and the parameters that the value activates.

    Attributes:
        value: The value.
        parameters: The conditional parameters this value activates, in order.
    """

    value: Scalar
    parameters: tuple[Parameter, ...] = ()


@dataclass(slots=True, frozen=True)
class Parameter:
    """A node of the grammar: a categorical choice or a numeric or boolean terminal.

    Attributes:
        name: Its name, unique in the space.
        type: "categorical", "real", "int" or "boolean".
        default: Its default value, which belongs to its domain.
        description: What it does, in one sentence.
        label: Its display name; empty means its name.
        role: Its tuning role (one of `ROLES`), or empty.
        low: The lower end of the range of a numeric parameter.
        high: The upper end of the range of a numeric parameter.
        log: Whether a numeric parameter is sampled on a log scale.
        productions: The values of a categorical parameter, with what each one activates.
        global_sub_parameters: The parameters of a categorical parameter that are present
            whatever its value.
    """

    name: str
    type: ParameterType
    default: Scalar
    description: str = ""
    label: str = ""
    role: str = ""
    low: float | None = None
    high: float | None = None
    log: bool = False
    productions: tuple[Production, ...] = ()
    global_sub_parameters: tuple[Parameter, ...] = ()

    @property
    def display_name(self) -> str:
        """Its label, or its name when it has none."""
        return self.label or self.name

    @property
    def values(self) -> tuple[Scalar, ...]:
        """The values of a categorical parameter, in order."""
        return tuple(production.value for production in self.productions)

    def contains(self, value: object) -> bool:
        """Whether `value` belongs to the domain of this parameter."""
        if self.type == "categorical":
            return any(same_value(value, choice) for choice in self.values)
        if self.type == "boolean":
            return isinstance(value, bool)
        if self.type == "int" and (isinstance(value, bool) or not isinstance(value, int)):
            return False
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        return self.low is not None and self.high is not None and self.low <= value <= self.high

    def production(self, value: object) -> Production:
        """The production of `value`, for a categorical parameter.

        Raises:
            ParameterSpaceError: If `value` is not one of its values.
        """
        for production in self.productions:
            if same_value(production.value, value):
                return production
        raise ParameterSpaceError(f"'{value}' is not a value of '{self.name}'.")

    def active_children(self, value: object) -> tuple[Parameter, ...]:
        """The parameters below this one that `value` makes active: global ones first."""
        if self.type != "categorical":
            return ()
        return self.global_sub_parameters + self.production(value).parameters

    def descendants(self) -> Iterator[Parameter]:
        """Every parameter below this one, depth-first: global ones, then each production's."""
        for child in self.global_sub_parameters:
            yield child
            yield from child.descendants()
        for production in self.productions:
            for child in production.parameters:
                yield child
                yield from child.descendants()


@dataclass(slots=True, frozen=True)
class ParameterSpace:
    """A grammar of the configurations of an algorithm for one problem encoding.

    Attributes:
        name: Its unique id (e.g. "nsgaii_real").
        algorithm: The VAMOS algorithm it configures.
        encoding: The problem encoding it is for.
        parameters: The parameters at the root of the tree, in order.
        description: What it is, in one sentence.
    """

    name: str
    algorithm: str
    encoding: str
    parameters: tuple[Parameter, ...]
    description: str = ""

    def all_parameters(self) -> tuple[Parameter, ...]:
        """Every parameter of the space, depth-first."""
        found: list[Parameter] = []
        for parameter in self.parameters:
            found.append(parameter)
            found.extend(parameter.descendants())
        return tuple(found)

    def parameter(self, name: str) -> Parameter:
        """The parameter called `name`.

        Raises:
            KeyError: If the space has no such parameter.
        """
        for parameter in self.all_parameters():
            if parameter.name == name:
                return parameter
        raise KeyError(name)

    def default_values(self) -> dict[str, Scalar]:
        """The default value of every parameter of the space, active or not."""
        return {parameter.name: parameter.default for parameter in self.all_parameters()}

    def default_configuration(self) -> Configuration:
        """The configuration made of every active parameter's default value."""
        return self.configuration(self.default_values(), complete=True)

    def configuration(
        self, values: Mapping[str, object], *, complete: bool = False
    ) -> Configuration:
        """The configuration that `values` derives.

        Args:
            values: A value for every active parameter. With `complete`, values of inactive
                parameters are allowed and ignored; without it, they are an error.
            complete: Whether `values` may hold values for parameters that are not active.

        Returns:
            The configuration, with the active parameters in depth-first order.

        Raises:
            ParameterSpaceError: If an active parameter has no value or a value outside its
                domain, or (without `complete`) a value is given for an inactive parameter.
        """
        derived: dict[str, Scalar] = {}
        self._derive(self.parameters, values, derived)
        if not complete:
            unused = [name for name in values if name not in derived]
            if unused:
                raise ParameterSpaceError(f"Parameters not active in this configuration: {unused}")
        return Configuration(self, derived)

    def _derive(
        self, nodes: tuple[Parameter, ...], values: Mapping[str, object], out: dict[str, Scalar]
    ) -> None:
        for node in nodes:
            if node.name not in values:
                raise ParameterSpaceError(f"Missing a value for '{node.name}'.")
            value = values[node.name]
            if not node.contains(value):
                raise ParameterSpaceError(f"{value!r} is outside the domain of '{node.name}'.")
            out[node.name] = _canonical_scalar(node, value)
            self._derive(node.active_children(value), values, out)

    def to_dict(self) -> dict[str, Any]:
        """The space as a document of the `vamos.parameter-space` schema."""
        return {
            "schema": SPACE_SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "name": self.name,
            "algorithm": self.algorithm,
            "encoding": self.encoding,
            "description": self.description,
            "parameters": {p.name: _parameter_to_dict(p) for p in self.parameters},
        }

    def to_yaml(self) -> str:
        """The space as YAML."""
        return yaml.safe_dump(self.to_dict(), sort_keys=False, allow_unicode=True)

    def content_hash(self) -> str:
        """The SHA-256 of the space's canonical JSON form, as "sha256:<hex>"."""
        canonical = json.dumps(self.to_dict(), separators=(",", ":"), ensure_ascii=False)
        return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(slots=True, frozen=True)
class Configuration:
    """A derivation of a parameter space: a value for each of its active parameters.

    Attributes:
        space: The space it derives from.
        values: The active parameters and their values, in depth-first order.
    """

    space: ParameterSpace
    values: Mapping[str, Scalar] = field(default_factory=dict)

    def to_cli(self) -> str:
        """The configuration as a command-line string: "--name value ..."."""
        return " ".join(f"--{name} {_format(value)}" for name, value in self.values.items())

    def to_dict(self) -> dict[str, Any]:
        """The configuration as a document of the `vamos.parameter-configuration` schema."""
        return {
            "schema": CONFIGURATION_SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "space": {
                "name": self.space.name,
                "schema_version": SCHEMA_VERSION,
                "hash": self.space.content_hash(),
            },
            "values": dict(self.values),
        }


def space_from_dict(document: Mapping[str, Any]) -> ParameterSpace:
    """Build a parameter space from a `vamos.parameter-space` document and validate it.

    Raises:
        ParameterSpaceError: If the document is malformed or breaks a rule of the grammar.
    """
    if document.get("schema") != SPACE_SCHEMA:
        raise ParameterSpaceError(f"Not a {SPACE_SCHEMA} document.")
    if document.get("schema_version") != SCHEMA_VERSION:
        raise ParameterSpaceError(f"Unsupported schema version {document.get('schema_version')}.")
    space = ParameterSpace(
        name=str(document["name"]),
        algorithm=str(document["algorithm"]),
        encoding=str(document["encoding"]),
        description=str(document.get("description", "")),
        parameters=_parameters_from_dict(document.get("parameters"), "parameters"),
    )
    problems = validate_space(space)
    if problems:
        raise ParameterSpaceError("Invalid parameter space:\n- " + "\n- ".join(problems))
    return space


def space_from_yaml(text: str) -> ParameterSpace:
    """Build and validate a parameter space from its YAML text."""
    return space_from_dict(yaml.safe_load(text))


def load_space(path: Path) -> ParameterSpace:
    """Load and validate a parameter space from a YAML file."""
    return space_from_yaml(path.read_text(encoding="utf-8"))


def validate_space(space: ParameterSpace) -> list[str]:
    """Check the rules G1 to G5 of the design.

    Returns:
        A description of every violation; empty when the space is well formed.
    """
    problems: list[str] = []
    if not space.parameters:
        problems.append("The space has no parameters.")
    seen: set[str] = set()
    for parameter in space.all_parameters():
        if parameter.name in seen:
            problems.append(f"G1: '{parameter.name}' appears more than once.")
        seen.add(parameter.name)
        problems.extend(_check_parameter(parameter))
    return problems


def _check_parameter(parameter: Parameter) -> list[str]:
    name = parameter.name
    problems: list[str] = []
    if not _NAME.match(name):
        problems.append(f"G1: '{name}' is not a lowercase snake_case name.")
    if parameter.role and parameter.role not in ROLES:
        problems.append(f"'{name}' has an unknown role '{parameter.role}'.")
    if parameter.type == "categorical":
        problems.extend(_check_categorical(parameter))
    elif parameter.type in ("real", "int"):
        problems.extend(_check_numeric(parameter))
    if not problems and not parameter.contains(parameter.default):
        problems.append(
            f"G3: the default of '{name}' ({parameter.default!r}) is not in its domain."
        )
    return problems


def _check_categorical(parameter: Parameter) -> list[str]:
    problems: list[str] = []
    values = parameter.values
    if not values:
        problems.append(f"G5: '{parameter.name}' has no values.")
    if any(same_value(a, b) for i, a in enumerate(values) for b in values[i + 1 :]):
        problems.append(f"G5: '{parameter.name}' repeats a value.")
    for production in parameter.productions:
        if production.parameters and not isinstance(production.value, str):
            problems.append(f"G5: '{parameter.name}' value {production.value!r} has parameters.")
    return problems


def _check_numeric(parameter: Parameter) -> list[str]:
    low, high = parameter.low, parameter.high
    if low is None or high is None or not (math.isfinite(low) and math.isfinite(high)):
        return [f"G4: '{parameter.name}' needs a finite range."]
    problems: list[str] = []
    if low > high:
        problems.append(f"G4: '{parameter.name}' has low > high.")
    if parameter.log and low <= 0:
        problems.append(f"G4: '{parameter.name}' is on a log scale and needs low > 0.")
    if parameter.type == "int" and not (isinstance(low, int) and isinstance(high, int)):
        problems.append(f"G4: '{parameter.name}' is an int and needs integer ends.")
    return problems


def _parameters_from_dict(nodes: object, path: str) -> tuple[Parameter, ...]:
    if nodes is None:
        return ()
    if not isinstance(nodes, Mapping):
        raise ParameterSpaceError(f"{path} must be a mapping of parameter names to parameters.")
    return tuple(
        _parameter_from_dict(str(name), body, f"{path}.{name}") for name, body in nodes.items()
    )


def _parameter_from_dict(name: str, body: object, path: str) -> Parameter:
    if not isinstance(body, Mapping):
        raise ParameterSpaceError(f"{path} must be a mapping.")
    kind = body.get("type")
    if kind not in PARAMETER_TYPES:
        raise ParameterSpaceError(f"{path}: type must be one of {PARAMETER_TYPES}.")
    if "default" not in body:
        raise ParameterSpaceError(f"{path}: every parameter needs a default.")
    low, high = _range(body.get("range"), path) if kind in ("real", "int") else (None, None)
    return Parameter(
        name=name,
        type=kind,
        default=body["default"],
        description=str(body.get("description", "")),
        label=str(body.get("label", "")),
        role=str(body.get("role", "")),
        low=low,
        high=high,
        log=bool(body.get("log", False)),
        productions=_productions(body.get("values"), path) if kind == "categorical" else (),
        global_sub_parameters=_parameters_from_dict(
            body.get("global_sub_parameters"), f"{path}.global_sub_parameters"
        ),
    )


def _range(value: object, path: str) -> tuple[float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ParameterSpaceError(f"{path}: range must be [low, high].")
    return value[0], value[1]


def _productions(values: object, path: str) -> tuple[Production, ...]:
    if isinstance(values, (list, tuple)):
        return tuple(Production(value) for value in values)
    if isinstance(values, Mapping):
        return tuple(
            Production(
                value,
                _parameters_from_dict(
                    (body or {}).get("conditional_parameters"), f"{path}.values.{value}"
                ),
            )
            for value, body in values.items()
        )
    raise ParameterSpaceError(f"{path}: values must be a list or a mapping of productions.")


def _parameter_to_dict(parameter: Parameter) -> dict[str, Any]:
    body: dict[str, Any] = {"type": parameter.type, "default": parameter.default}
    for key in ("description", "label", "role"):
        if getattr(parameter, key):
            body[key] = getattr(parameter, key)
    if parameter.type in ("real", "int"):
        body["range"] = [parameter.low, parameter.high]
        if parameter.log:
            body["log"] = True
    if parameter.global_sub_parameters:
        body["global_sub_parameters"] = {
            child.name: _parameter_to_dict(child) for child in parameter.global_sub_parameters
        }
    if parameter.type == "categorical":
        body["values"] = _values_to_dict(parameter.productions)
    return body


def _values_to_dict(productions: tuple[Production, ...]) -> list[Scalar] | dict[str, Any]:
    if not any(production.parameters for production in productions):
        return [production.value for production in productions]
    return {
        str(production.value): (
            {
                "conditional_parameters": {
                    child.name: _parameter_to_dict(child) for child in production.parameters
                }
            }
            if production.parameters
            else {}
        )
        for production in productions
    }


def _canonical_scalar(parameter: Parameter, value: object) -> Scalar:
    """The value as its parameter's type: a float for a real, the matching choice otherwise."""
    if parameter.type == "real":
        return float(value)  # type: ignore[arg-type]
    if parameter.type == "categorical":
        return parameter.production(value).value
    return value  # type: ignore[return-value]


def _format(value: Scalar) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
