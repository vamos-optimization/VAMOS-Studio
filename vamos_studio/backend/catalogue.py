"""What VAMOS offers, and which part of it the studio supports so far.

Algorithms come from `vamos.algorithms.available_algorithms` and problems from
`vamos.available_problem_names` and `vamos.make_problem_selection`, all stable VAMOS APIs. The
studio supports an algorithm for an encoding when it ships its grammar, and a problem when its
family is in `SUPPORTED_PROBLEM_FAMILIES`; everything else is listed as inactive.
"""

from __future__ import annotations

import inspect
import re
import typing
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from typing import Final

import numpy as np
import vamos
from numpy.typing import NDArray
from vamos.algorithms import available_algorithms
from vamos.foundation.problem.resolver import resolve_reference_front_path

from .bundled_resources import JMETAL_VERSION, reference_front_file
from .upstream.vamos_bridge import BUILTIN_SPACES

ENCODINGS: Final = ("real", "binary", "integer", "permutation", "mixed")
ENCODING_LABELS: Final = {
    "real": "Real",
    "binary": "Binary",
    "integer": "Integer",
    "permutation": "Permutation",
    "mixed": "Mixed",
}
ALGORITHM_LABELS: Final = {
    "agemoea": "AGE-MOEA",
    "ibea": "IBEA",
    "moead": "MOEA/D",
    "nsgaii": "NSGA-II",
    "nsgaiii": "NSGA-III",
    "rvea": "RVEA",
    "smpso": "SMPSO",
    "smsemoa": "SMS-EMOA",
    "spea2": "SPEA2",
}
# Problem families the studio supports, and the encodings it supports them for.
SUPPORTED_PROBLEM_FAMILIES: Final = {
    "zdt": ("real", "binary"),
    "dtlz": ("real",),
    "bin_knapsack": ("binary",),
    "bin_qubo": ("binary",),
    "bin_feat": ("binary",),
}
# Numbers of objectives the studio offers for problems that let you choose: those of the reference
# fronts it copies from jMetal, and those its charts draw (2D and 3D).
SUPPORTED_N_OBJ: Final = (2, 3)
FAMILY_LABELS: Final = {
    "zdt": "ZDT",
    "dtlz": "DTLZ",
    "wfg": "WFG",
    "mw": "MW",
    "lsmop": "LSMOP",
    "zcat": "ZCAT",
    "re": "RE (real-world)",
    "rwa": "RWA (real-world)",
    "cec2009_uf": "CEC 2009 (UF)",
    "cec2009_cf": "CEC 2009 (CF)",
    "lz09_f": "LZ09",
    "bin_knapsack": "Knapsack (binary)",
    "bin_qubo": "QUBO (binary)",
    "bin_feat": "Feature selection (binary)",
}
_FAMILY = re.compile(r"^(.*?)_?\d+$")
ARGUMENT_LABELS: Final = {"n_var": "Variables", "n_obj": "Objectives"}
_ARGUMENT_TYPES: Final = {"int": "integer", "float": "number", "bool": "boolean"}


@dataclass(slots=True, frozen=True)
class AlgorithmEntry:
    """A VAMOS algorithm and the encodings the studio supports it for.

    Attributes:
        key: Its VAMOS id (e.g. "nsgaii").
        label: Its display name (e.g. "NSGA-II").
        encodings: The encodings the studio has a grammar for; empty when it is inactive.
    """

    key: str
    label: str
    encodings: tuple[str, ...]

    @property
    def available(self) -> bool:
        """Whether the studio supports it for at least one encoding."""
        return bool(self.encodings)


@dataclass(slots=True, frozen=True)
class ProblemEntry:
    """A VAMOS problem.

    Attributes:
        key: Its VAMOS id (e.g. "zdt1").
        label: Its display name (e.g. "ZDT1").
        family: The family it belongs to (e.g. "zdt").
        description: What it is, in one sentence.
        encoding: The encoding of its variables.
        n_var: Its default number of variables.
        n_obj: Its default number of objectives.
        available: Whether the studio supports it.
        n_obj_options: The numbers of objectives the studio offers for it: its default one, or
            `SUPPORTED_N_OBJ` when VAMOS lets you choose.
    """

    key: str
    label: str
    family: str
    description: str
    encoding: str
    n_var: int
    n_obj: int
    available: bool
    n_obj_options: tuple[int, ...] = ()


@dataclass(slots=True, frozen=True)
class ProblemArgument:
    """An argument of a problem's constructor in VAMOS, as Evolver-Studio's problem forms show it.

    Attributes:
        name: Its name in VAMOS (e.g. "n_var", "complicated_pareto_set").
        type: "integer", "number" (a decimal) or "boolean".
        default: Its value in the problem built with its defaults.
    """

    name: str
    type: str
    default: int | float | bool

    @property
    def label(self) -> str:
        """Its display name."""
        return ARGUMENT_LABELS.get(self.name, self.name.replace("_", " ").capitalize())


@dataclass(slots=True, frozen=True)
class ProblemDetails:
    """The dimensions, bounds and reference front of a problem with a number of objectives.

    Attributes:
        entry: The problem.
        n_var: Its number of variables with `n_obj` objectives.
        n_obj: The number of objectives.
        lower: The lower bound of each variable.
        upper: The upper bound of each variable.
        reference_front: Its reference front (see `reference_front`), or None.
        reference_front_source: Where the reference front comes from, or None.
    """

    entry: ProblemEntry
    n_var: int
    n_obj: int
    lower: NDArray[np.float64]
    upper: NDArray[np.float64]
    reference_front: NDArray[np.float64] | None
    reference_front_source: str | None


def algorithm_label(key: str) -> str:
    """The display name of a VAMOS algorithm."""
    return ALGORITHM_LABELS.get(key, key.upper())


def family_of(problem: str) -> str:
    """The family of a problem, from its id: "zdt1" -> "zdt", "cec2009_uf1" -> "cec2009_uf"."""
    match = _FAMILY.match(problem)
    return match.group(1) if match else problem


def family_label(family: str) -> str:
    """The display name of a problem family."""
    return FAMILY_LABELS.get(family, family.replace("_", " ").upper())


def algorithm_entries() -> list[AlgorithmEntry]:
    """Every VAMOS algorithm, with the encodings the studio supports it for."""
    return [
        AlgorithmEntry(
            key=key,
            label=algorithm_label(key),
            encodings=tuple(enc for enc in ENCODINGS if (key, enc) in BUILTIN_SPACES),
        )
        for key in sorted(available_algorithms(), key=algorithm_label)
    ]


@cache
def problem_entries() -> tuple[ProblemEntry, ...]:
    """Every VAMOS problem, in VAMOS's order."""
    return tuple(_problem_entry(key) for key in vamos.available_problem_names())


def problem_entry(key: str) -> ProblemEntry:
    """The entry of the problem `key`.

    Raises:
        KeyError: If VAMOS has no such problem.
    """
    for entry in problem_entries():
        if entry.key == key:
            return entry
    raise KeyError(key)


@cache
def problem_arguments(key: str) -> tuple[ProblemArgument, ...]:
    """The arguments of a problem's constructor in VAMOS, in order, with their defaults.

    They are read from the constructor's signature, as Evolver-Studio reads them from Evolver's
    DescribeMain. The number of objectives is an argument only when VAMOS lets you choose it;
    the defaults of `n_var` and `n_obj` are the problem's default dimensions.
    """
    entry = problem_entry(key)
    constructor = type(vamos.make_problem_selection(key).instantiate()).__init__
    found = []
    for parameter in list(inspect.signature(constructor).parameters.values())[1:]:
        if parameter.name == "n_obj" and len(entry.n_obj_options) < 2:
            continue
        default = {"n_var": entry.n_var, "n_obj": entry.n_obj}.get(
            parameter.name, parameter.default
        )
        found.append(ProblemArgument(parameter.name, _argument_type(parameter), default))
    return tuple(found)


def default_arguments(key: str) -> dict[str, int | float | bool]:
    """The value of every argument of a problem built with its defaults."""
    return {argument.name: argument.default for argument in problem_arguments(key)}


def standard_variables(key: str, n_obj: int) -> int:
    """The number of variables VAMOS gives a problem with `n_obj` objectives by default.

    For DTLZ it follows the number of objectives (DTLZ2: 11 with two, 12 with three).
    """
    return int(vamos.make_problem_selection(key, n_obj=n_obj).n_var)


def min_variables(key: str, n_obj: int) -> int:
    """The fewest variables the studio accepts: a DTLZ problem needs one per objective at least."""
    return n_obj if family_of(key) == "dtlz" else 2


def argument_problems(key: str, arguments: Mapping[str, object]) -> list[str]:
    """What is wrong with these arguments of a problem; empty when they are fine."""
    entry = problem_entry(key)
    n_obj = int(arguments.get("n_obj", entry.n_obj))
    problems = []
    if n_obj not in entry.n_obj_options:
        problems.append(f"{entry.label} cannot have {n_obj} objectives here.")
    n_var = arguments.get("n_var")
    if n_var is not None and int(n_var) < min_variables(key, n_obj):
        problems.append(
            f"{entry.label} with {n_obj} objectives needs at least "
            f"{min_variables(key, n_obj)} variables."
        )
    return problems


def problem_details(key: str, n_obj: int | None = None, n_var: int | None = None) -> ProblemDetails:
    """The problem `key` with `n_obj` objectives and `n_var` variables (its defaults when None).

    Raises:
        ValueError: If the problem does not allow those arguments.
    """
    entry = problem_entry(key)
    n_obj = entry.n_obj if n_obj is None else n_obj
    arguments = {"n_obj": n_obj} | ({} if n_var is None else {"n_var": n_var})
    problems = argument_problems(key, arguments)
    if problems:
        raise ValueError(" ".join(problems))
    selection = vamos.make_problem_selection(
        key, n_var=n_var, n_obj=n_obj if n_obj != entry.n_obj else None
    )
    n_var = int(selection.n_var)
    problem = selection.instantiate()
    lower = np.broadcast_to(np.asarray(problem.xl, dtype=float), (n_var,))
    upper = np.broadcast_to(np.asarray(problem.xu, dtype=float), (n_var,))
    front = reference_front(key, n_obj)
    source = reference_front_source(key, n_obj) if front is not None else None
    return ProblemDetails(entry, n_var, n_obj, lower, upper, front, source)


def reference_front(key: str, n_obj: int) -> NDArray[np.float64] | None:
    """The reference front of `key` with `n_obj` objectives, or None.

    The studio's copy of jMetal's front comes first (see `bundled_resources`): VAMOS 1.1 ships
    inaccurate samples of some fronts. Otherwise, the one VAMOS ships.
    """
    path = reference_front_file(key, n_obj) or resolve_reference_front_path(key, None, n_obj=n_obj)
    if path is None:
        return None
    front = np.loadtxt(path, delimiter=",", ndmin=2)
    return front if front.shape[1] == n_obj else None


def reference_front_source(key: str, n_obj: int) -> str:
    """Where the reference front of `key` with `n_obj` objectives comes from: jMetal or VAMOS."""
    if reference_front_file(key, n_obj) is not None:
        return f"jMetal {JMETAL_VERSION}"
    return f"VAMOS {vamos_version_label()}"


def vamos_version_label() -> str:
    """The installed VAMOS version, for display."""
    return str(getattr(vamos, "__version__", "")) or "(unknown version)"


def _problem_entry(key: str) -> ProblemEntry:
    selection = vamos.make_problem_selection(key)
    spec = selection.spec
    family = family_of(key)
    encoding = str(spec.encoding)
    return ProblemEntry(
        key=key,
        label=str(spec.label),
        family=family,
        description=str(spec.description or ""),
        encoding=encoding,
        n_var=int(selection.n_var),
        n_obj=int(selection.n_obj),
        available=encoding in SUPPORTED_PROBLEM_FAMILIES.get(family, ()),
        n_obj_options=SUPPORTED_N_OBJ if spec.allow_n_obj_override else (int(selection.n_obj),),
    )


def format_arguments(key: str) -> str:
    """A problem's arguments in one line, e.g. "n_var: integer = 12, n_obj: integer = 3"."""
    return ", ".join(
        f"{argument.name}: {argument.type} = {argument.default}"
        for argument in problem_arguments(key)
    )


def _argument_type(parameter: inspect.Parameter) -> str:
    """The type of a constructor parameter, from its annotation or its default."""
    annotation = parameter.annotation
    members = [a for a in typing.get_args(annotation) if a is not type(None)] or [annotation]
    text = annotation if isinstance(annotation, str) else getattr(members[0], "__name__", "")
    if not text and parameter.default is not inspect.Parameter.empty:
        text = type(parameter.default).__name__
    base = str(text).split("|")[0].strip()
    return _ARGUMENT_TYPES.get(base, "number")
