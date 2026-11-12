"""The extremes and the knee of a front of solutions, every objective minimized.

Adapted from Transept (transept/front.py, which maximizes), by the same authors.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from numpy.typing import NDArray


def objective_names(n_obj: int) -> list[str]:
    """The column names of the objectives: f1, f2, ..."""
    return [f"f{index + 1}" for index in range(n_obj)]


def summarize(front: NDArray[np.float64]) -> pd.DataFrame:
    """The solutions of a front, sorted by the first objective, with their extremes and knee.

    Args:
        front: The objective values, one row per non-dominated solution.

    Returns:
        A table with `solution` (row of `front`), the objectives, `distance` (to the ideal point,
        every objective scaled to [0, 1] over the front) and `note` ("best f<i>", "knee" or "").
    """
    names = objective_names(front.shape[1])
    table = pd.DataFrame(front, columns=names)
    table.insert(0, "solution", range(len(front)))
    if table.empty:
        return table.assign(distance=[], note=[])
    best, worst = front.min(axis=0), front.max(axis=0)
    span = np.where(worst - best > 0, worst - best, 1.0)
    table["distance"] = np.sqrt((((front - best) / span) ** 2).sum(axis=1))
    table["note"] = ""
    if len(names) > 1:
        table.loc[table["distance"].idxmin(), "note"] = "knee"
    for name in reversed(names):  # the first objective wins when one row is best in several
        table.loc[table[name].idxmin(), "note"] = f"best {name}"
    return table.sort_values(names[0], ignore_index=True)


def knee(table: pd.DataFrame) -> int | None:
    """The solution closest to the ideal point, if the table has any."""
    if table.empty:
        return None
    return int(table.loc[table["distance"].idxmin(), "solution"])
