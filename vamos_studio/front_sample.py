"""Approximations of a reference front, to show how quality indicators respond.

Pure NumPy, no Streamlit.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def sample_front(
    reference_front: NDArray[np.float64], n_points: int, shift: float
) -> NDArray[np.float64]:
    """An approximation of a reference front: evenly spread points of it, moved away from it.

    Args:
        reference_front: The reference front, one row per point.
        n_points: How many of its points to take (at most all of them), evenly spread along the
            first objective.
        shift: How far to move every point in every objective, as a fraction of the reference
            front's range in that objective (0 keeps the points on the front).

    Returns:
        The approximation, one row per point.

    Raises:
        ValueError: If `n_points` is not positive or `shift` is negative.
    """
    if n_points < 1:
        raise ValueError("n_points must be at least 1.")
    if shift < 0:
        raise ValueError("shift must not be negative.")
    ordered = reference_front[np.argsort(reference_front[:, 0], kind="stable")]
    count = min(n_points, len(ordered))
    indices = np.unique(np.round(np.linspace(0, len(ordered) - 1, count)).astype(int))
    span = ordered.max(axis=0) - ordered.min(axis=0)
    return ordered[indices] + shift * span
