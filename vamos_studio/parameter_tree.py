"""Text views of a parameter space: its tree as Markdown, its parameters as table rows.

Pure functions over the grammar model, so the pages stay thin and the views are testable.
"""

from __future__ import annotations

from dataclasses import dataclass

from vamos_studio.backend.upstream.parameter_space import Parameter, ParameterSpace, Scalar

INDENT = "    "


@dataclass(slots=True, frozen=True)
class SpaceSummary:
    """Counts that describe the size and shape of a parameter space.

    Attributes:
        parameters: All its parameters.
        top_level: Those at the root of the tree.
        categorical: Those that are categorical.
        numeric: Those that are real or int.
        depth: The number of parameter levels of its deepest branch.
        default_active: The parameters active in the default configuration.
    """

    parameters: int
    top_level: int
    categorical: int
    numeric: int
    depth: int
    default_active: int


def summarize(space: ParameterSpace) -> SpaceSummary:
    """The counts that describe `space`."""
    every = space.all_parameters()
    return SpaceSummary(
        parameters=len(every),
        top_level=len(space.parameters),
        categorical=sum(p.type == "categorical" for p in every),
        numeric=sum(p.type in ("real", "int") for p in every),
        depth=max((_depth(p) for p in space.parameters), default=0),
        default_active=len(space.default_configuration().values),
    )


def format_value(value: Scalar) -> str:
    """A parameter value as text: booleans in lowercase, numbers and strings as they are."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def describe_domain(parameter: Parameter) -> str:
    """The type and domain of `parameter`, e.g. "real in [5.0, 40.0]"."""
    if parameter.type == "categorical":
        return f"categorical, {len(parameter.productions)} values"
    if parameter.type == "boolean":
        return "boolean"
    scale = ", log scale" if parameter.log else ""
    return f"{parameter.type} in [{parameter.low}, {parameter.high}]{scale}"


def tree_markdown(space: ParameterSpace) -> str:
    """The grammar of `space` as a nested Markdown list.

    Each parameter shows its name, domain and default. Under a categorical parameter come its
    global sub-parameters ("any value"), then each value that activates parameters, then the
    values that activate none.
    """
    lines: list[str] = []
    for parameter in space.parameters:
        _parameter_lines(parameter, 0, lines)
    return "\n".join(lines)


def parameter_rows(space: ParameterSpace) -> list[dict[str, str]]:
    """One row per parameter, depth-first, with where it hangs in the tree."""
    rows: list[dict[str, str]] = []
    for parameter in space.parameters:
        _rows(parameter, "(root)", rows)
    return rows


def _parameter_lines(parameter: Parameter, level: int, lines: list[str]) -> None:
    indent = INDENT * level
    lines.append(
        f"{indent}- **{parameter.display_name}** `{parameter.name}` · "
        f"{describe_domain(parameter)} · default `{format_value(parameter.default)}`"
    )
    if parameter.type != "categorical":
        return
    if parameter.global_sub_parameters:
        lines.append(f"{indent}{INDENT}- *any value*")
        for child in parameter.global_sub_parameters:
            _parameter_lines(child, level + 2, lines)
    for production in parameter.productions:
        if production.parameters:
            lines.append(f"{indent}{INDENT}- `{format_value(production.value)}`")
            for child in production.parameters:
                _parameter_lines(child, level + 2, lines)
    plain = [format_value(p.value) for p in parameter.productions if not p.parameters]
    if plain:
        joined = ", ".join(f"`{value}`" for value in plain)
        label = "values" if len(plain) == len(parameter.productions) else "other values"
        lines.append(f"{indent}{INDENT}- {label}: {joined}")


def _rows(parameter: Parameter, parent: str, rows: list[dict[str, str]]) -> None:
    rows.append(
        {
            "Parameter": parameter.name,
            "Label": parameter.display_name,
            "Active when": parent,
            "Domain": describe_domain(parameter),
            "Default": format_value(parameter.default),
            "Role": parameter.role,
            "Description": parameter.description,
        }
    )
    for child in parameter.global_sub_parameters:
        _rows(child, f"{parameter.name} (any value)", rows)
    for production in parameter.productions:
        for child in production.parameters:
            _rows(child, f"{parameter.name} = {format_value(production.value)}", rows)


def _depth(parameter: Parameter) -> int:
    children = list(parameter.global_sub_parameters) + [
        child for production in parameter.productions for child in production.parameters
    ]
    return 1 + max((_depth(child) for child in children), default=0)
