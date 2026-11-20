"""Quality indicators: what VAMOS offers, and how the studio measures a front with them.

The studio follows Evolver's convention (ported from Evolver-Studio's ``hypervolume.py``): a
front is normalized with the minimum and maximum of each objective of its problem's reference
front, and every indicator is computed on normalized values, so values are comparable across
problems and with Evolver-Studio. The hypervolume clips the normalized front to [0, 1] and is
measured up to the point (1, ..., 1). The normalized hypervolume is 1 - HV(front) / HV(reference
front), as Evolver's NormalizedHypervolume.

The indicators themselves are computed by VAMOS (``get_indicator``, backed by moocore); this
module only normalizes the fronts and derives the normalized hypervolume.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import numpy as np
from numpy.typing import NDArray
from vamos.foundation.quality_indicators import get_indicator
from vamos.ux.api import HVApproxIndicator

Front = NDArray[np.float64]


@dataclass(slots=True, frozen=True)
class IndicatorEntry:
    """A quality indicator, as the studio describes and computes it.

    Attributes:
        key: Its name for VAMOS's `get_indicator` (or "nhv", which the studio derives).
        short_name: Its abbreviation (e.g. "IGD+").
        full_name: Its full name.
        measures: What it measures, in a sentence.
        maximized: Whether higher values are better.
        needs: What it measures a front against: "reference front" or "reference point".
        citation: The work that introduced it.
        available: Whether the studio computes it.
        computed_by_studio: Whether the studio derives it from VAMOS's indicators.
        note: Why it is not available yet, or a caveat.
    """

    key: str
    short_name: str
    full_name: str
    measures: str
    maximized: bool
    needs: str
    citation: str
    available: bool = True
    computed_by_studio: bool = False
    note: str = ""


# How the hypervolume is computed: exactly, or by VAMOS's approximation (moocore's `hv_approx`,
# VAMOS 1.5), which stays fast with many objectives. `Rphi-FWE+` is deterministic.
EXACT: Final = "exact"
APPROXIMATE: Final = "approximate"
HV_METHODS: Final = {EXACT: "Exact", APPROXIMATE: "Approximate"}
APPROXIMATE_METHOD: Final = "Rphi-FWE+"
APPROXIMATE_SAMPLES: Final = 100_000

INDICATORS: Final = (
    IndicatorEntry(
        key="hv",
        short_name="HV",
        full_name="Hypervolume",
        measures="The volume of the normalized objective space the front dominates, up to the "
        "point (1, ..., 1): convergence and spread together; Pareto compliant.",
        maximized=True,
        needs="reference point",
        citation="Zitzler & Thiele, IEEE Trans. Evol. Comput. 3(4), 1999.",
    ),
    IndicatorEntry(
        key="nhv",
        short_name="NHV",
        full_name="Normalized hypervolume",
        measures="1 - HV(front) / HV(reference front): the share of the reference front's "
        "hypervolume the front misses; 0 when it covers as much. Evolver's meta-objective.",
        maximized=False,
        needs="reference front",
        citation="Evolver's NormalizedHypervolume, from the hypervolume of Zitzler & Thiele.",
        computed_by_studio=True,
    ),
    IndicatorEntry(
        key="igd",
        short_name="IGD",
        full_name="Inverted generational distance",
        measures="The average distance from each point of the reference front to the closest "
        "point of the front: convergence and spread; not Pareto compliant.",
        maximized=False,
        needs="reference front",
        citation="Coello Coello & Reyes Sierra, MICAI 2004, LNCS 2972.",
    ),
    IndicatorEntry(
        key="igd_plus",
        short_name="IGD+",
        full_name="Inverted generational distance plus",
        measures="IGD counting only the objectives in which the front is worse than each "
        "reference point: convergence and spread; weakly Pareto compliant.",
        maximized=False,
        needs="reference front",
        citation="Ishibuchi, Masuda, Tanigaki & Nojima, EMO 2015, LNCS 9019.",
    ),
    IndicatorEntry(
        key="epsilon_additive",
        short_name="EP",
        full_name="Additive epsilon",
        measures="The smallest amount by which the front must be shifted to weakly dominate the "
        "reference front: convergence, and coverage of its extremes.",
        maximized=False,
        needs="reference front",
        citation="Zitzler, Thiele, Laumanns, Fonseca & Grunert da Fonseca, IEEE Trans. Evol. "
        "Comput. 7(2), 2003.",
    ),
    IndicatorEntry(
        key="avg_hausdorff",
        short_name="Δp",
        full_name="Averaged Hausdorff distance",
        measures="The larger of the generational distance and IGD (with p = 1): penalizes both "
        "points far from the reference front and parts of it the front misses.",
        maximized=False,
        needs="reference front",
        citation="Schütze, Esquivel, Lara & Coello Coello, IEEE Trans. Evol. Comput. 16(4), 2012.",
    ),
    IndicatorEntry(
        key="epsilon_multiplicative",
        short_name="EP×",
        full_name="Multiplicative epsilon",
        measures="The smallest factor by which the front must be scaled to weakly dominate the "
        "reference front.",
        maximized=False,
        needs="reference front",
        citation="Zitzler, Thiele, Laumanns, Fonseca & Grunert da Fonseca, IEEE Trans. Evol. "
        "Comput. 7(2), 2003.",
        available=False,
        note="Needs strictly positive objective values, which normalized fronts do not have.",
    ),
    IndicatorEntry(
        key="hv_contributions",
        short_name="HVC",
        full_name="Hypervolume contributions",
        measures="The hypervolume each point contributes on its own.",
        maximized=True,
        needs="reference point",
        citation="moocore's hv_contributions.",
        available=False,
        note="A value per point, not per front: for analysing a front, not comparing fronts.",
    ),
    IndicatorEntry(
        key="hv_approx",
        short_name="HV≈",
        full_name="Approximate hypervolume",
        measures="A sampling estimate of the hypervolume.",
        maximized=True,
        needs="reference point",
        citation="moocore's hv_approx.",
        available=False,
        note="Meant for many objectives, where the exact hypervolume is too slow.",
    ),
    IndicatorEntry(
        key="whv_rect",
        short_name="WHV",
        full_name="Weighted hypervolume",
        measures="The hypervolume weighted by user-defined rectangles of the objective space.",
        maximized=True,
        needs="reference point",
        citation="moocore's whv_rect.",
        available=False,
        note="Needs weighted regions defined by the user.",
    ),
)


def indicator(key: str) -> IndicatorEntry:
    """The indicator called `key`.

    Raises:
        KeyError: If there is no such indicator.
    """
    for entry in INDICATORS:
        if entry.key == key:
            return entry
    raise KeyError(key)


def available_indicators() -> tuple[IndicatorEntry, ...]:
    """The indicators the studio computes, in catalogue order."""
    return tuple(entry for entry in INDICATORS if entry.available)


def normalize(front: Front, reference_front: Front) -> Front:
    """`front` scaled so that the reference front spans [0, 1] in every objective.

    An objective in which the reference front does not vary is only shifted, not scaled.

    Raises:
        ValueError: If the fronts have different numbers of objectives.
    """
    front = np.asarray(front, dtype=float)
    reference_front = np.asarray(reference_front, dtype=float)
    if front.ndim != 2 or reference_front.ndim != 2 or front.shape[1] != reference_front.shape[1]:
        raise ValueError("The front and the reference front need the same number of objectives.")
    lower = reference_front.min(axis=0)
    span = reference_front.max(axis=0) - lower
    span[span == 0] = 1.0
    return (front - lower) / span


def compute(key: str, front: Front, reference_front: Front, hv: str = EXACT) -> float:
    """The value of the indicator `key` for `front`, normalized with `reference_front`.

    Args:
        key: The indicator.
        front: The front measured.
        reference_front: The reference front, which also normalizes `front`.
        hv: How HV and NHV compute the hypervolume: `EXACT` or `APPROXIMATE`.

    Raises:
        KeyError: If `key` is not an available indicator.
        ValueError: If `front` is empty, the fronts have different numbers of objectives, or `hv`
            is not a method.
    """
    if not indicator(key).available:
        raise KeyError(f"The indicator '{key}' is not available.")
    if hv not in HV_METHODS:
        raise ValueError(f"Unknown hypervolume method '{hv}'.")
    if np.asarray(front).size == 0:
        raise ValueError("The front is empty.")
    normalized = normalize(front, reference_front)
    normalized_reference = normalize(reference_front, reference_front)
    if key == "hv":
        return _hypervolume(normalized, hv)
    if key == "nhv":
        return 1.0 - _hypervolume(normalized, hv) / _hypervolume(normalized_reference, hv)
    vamos_indicator = get_indicator(key, reference_front=normalized_reference)
    return float(vamos_indicator.compute(normalized).value)


def compute_all(front: Front, reference_front: Front, hv: str = EXACT) -> dict[str, float]:
    """The value of every available indicator for `front`, by key (see `compute`)."""
    return {
        entry.key: compute(entry.key, front, reference_front, hv)
        for entry in available_indicators()
    }


def _hypervolume(normalized: Front, hv: str = EXACT) -> float:
    """VAMOS's hypervolume of a normalized front, clipped to [0, 1], up to (1, ..., 1)."""
    clipped = np.clip(normalized, 0.0, 1.0)
    reference_point = np.ones(normalized.shape[1])
    if hv == APPROXIMATE:
        approximation = HVApproxIndicator(reference_point=reference_point)
        result = approximation.compute(
            clipped, samples=APPROXIMATE_SAMPLES, method=APPROXIMATE_METHOD
        )
        return float(result.value)
    return float(get_indicator("hv", reference_point=reference_point).compute(clipped).value)
