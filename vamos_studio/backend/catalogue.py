"""What VAMOS offers, and which part of it the studio supports so far.

Algorithms come from `vamos.algorithms.available_algorithms` and problems from
`vamos.available_problem_names` and `vamos.make_problem_selection`, all stable VAMOS APIs. The
studio supports an algorithm for an encoding when it ships its grammar, and a problem when its
family is in `SUPPORTED_PROBLEM_FAMILIES`; everything else is listed as inactive.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache
from typing import Final

import numpy as np
import vamos
from numpy.typing import NDArray
from vamos.algorithms import available_algorithms
from vamos.foundation.problem.resolver import resolve_reference_front_path

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
# Problem families the studio supports, and the encoding it supports them for.
SUPPORTED_PROBLEM_FAMILIES: Final = {"zdt": "real"}
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
}
_FAMILY = re.compile(r"^(.*?)_?\d+$")
# VAMOS 1.1.0 ships inaccurate samples of some reference fronts (its docs/reference/problems.md,
# "Replaced samples"; fixed after 1.1.0). For the ZDT fronts the studio supports: the largest
# distance, in f2, between a point of the shipped file and the analytic front at the same f1.
# tests/test_catalogue.py measures it again, so it fails once VAMOS ships the corrected files.
REFERENCE_FRONT_DEVIATIONS: Final = {
    "zdt1": 0.0006,
    "zdt2": 0.0005,
    "zdt3": 0.0016,
    "zdt4": 0.0146,
    "zdt6": 0.0023,
}


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
    """

    key: str
    label: str
    family: str
    description: str
    encoding: str
    n_var: int
    n_obj: int
    available: bool


@dataclass(slots=True, frozen=True)
class ProblemDetails:
    """The bounds and the reference front of a problem, with its default dimensions.

    Attributes:
        entry: The problem.
        lower: The lower bound of each variable.
        upper: The upper bound of each variable.
        reference_front: The reference front shipped with VAMOS, or None.
    """

    entry: ProblemEntry
    lower: NDArray[np.float64]
    upper: NDArray[np.float64]
    reference_front: NDArray[np.float64] | None


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


def problem_details(key: str) -> ProblemDetails:
    """The bounds and reference front of the problem `key`, with its default dimensions."""
    entry = problem_entry(key)
    problem = vamos.make_problem_selection(key).instantiate()
    lower = np.broadcast_to(np.asarray(problem.xl, dtype=float), (entry.n_var,))
    upper = np.broadcast_to(np.asarray(problem.xu, dtype=float), (entry.n_var,))
    return ProblemDetails(entry, lower, upper, reference_front(key, entry.n_obj))


def reference_front(key: str, n_obj: int) -> NDArray[np.float64] | None:
    """The reference front VAMOS ships for `key` with `n_obj` objectives, or None."""
    path = resolve_reference_front_path(key, None, n_obj=n_obj)
    if path is None:
        return None
    front = np.loadtxt(path, delimiter=",", ndmin=2)
    return front if front.shape[1] == n_obj else None


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
        available=SUPPORTED_PROBLEM_FAMILIES.get(family) == encoding,
    )
