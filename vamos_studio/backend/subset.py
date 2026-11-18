"""Choosing the result of a run from an unbounded archive: a diverse subset of it.

An unbounded external archive keeps every non-dominated solution found, thousands of them. As
jMetal does (its BestSolutionsArchive), the studio returns a subset as large as the population,
chosen by the configuration's `archive_subset_selection`, and keeps the whole archive beside it.
The selection itself is VAMOS's (vamos.engine.algorithm.components.subset_selection).

`farthest` is VAMOS's farthest-point (max-min distance) selection on objectives normalized with
the archive's bounds (`normalize=True`, VAMOS 1.3): the greedy selection of the distance-based
subset selection (DSS) of Singh, Bhattacharjee and Ray (IEEE TEC, 2019), which jMetal applies for
three or more objectives.

VAMOS 1.3 can also select the result itself (`ExternalArchiveConfig.final_selection`); the studio
selects it here so that the Monitor can preview the subset of the archive while the run goes on.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Final

import numpy as np
from numpy.typing import NDArray
from vamos.engine.algorithm.components.subset_selection import (
    select_top_k_crowding,
    select_top_k_farthest,
    select_top_k_hv_greedy,
    select_top_k_kmeans,
)

Selector = Callable[[NDArray[np.float64], int], NDArray[np.int_]]
NO_SELECTION: Final = "none"


METHODS: Final[dict[str, Selector]] = {
    "farthest": lambda front, k: select_top_k_farthest(front, k, normalize=True),
    "crowding": select_top_k_crowding,
    "hv_greedy": select_top_k_hv_greedy,
    # A fixed seed gives each front one subset.
    "kmeans": lambda front, k: select_top_k_kmeans(front, k, rng=np.random.default_rng(0)),
}


def select(method: str, front: NDArray[np.float64], size: int) -> NDArray[np.int_]:
    """The rows of `front` that `method` keeps, at most `size`, sorted.

    Raises:
        ValueError: If `method` is unknown or `size` is not positive.
    """
    if method not in METHODS:
        raise ValueError(f"Unknown subset selection '{method}'.")
    if size <= 0:
        raise ValueError("size must be positive.")
    if len(front) <= size:
        return np.arange(len(front), dtype=int)
    return np.sort(np.asarray(METHODS[method](np.asarray(front, dtype=float), size), dtype=int))


def method_of(configuration_values: dict[str, object]) -> str | None:
    """The subset selection a configuration asks for, or None to return the whole archive."""
    if configuration_values.get("external_archive") != "unbounded":
        return None
    method = configuration_values.get("archive_subset_selection", NO_SELECTION)
    return None if method == NO_SELECTION else str(method)
