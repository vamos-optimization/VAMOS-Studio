"""Approximations of a reference front, to show how quality indicators respond.

Pure NumPy, no Streamlit.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def sample_front(
    reference_front: NDArray[np.float64], n_points: int, shift: float
) -> NDArray[np.float64]:
    """An approximation of a reference front: well-spread points of it, moved away from it.

    Args:
        reference_front: The reference front, one row per point.
        n_points: How many of its points to take (at most all of them). With two objectives
            they are evenly spread along the first one; with more, they are chosen far from each
            other (farthest-point sampling, starting at the point with the smallest f1).
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
    if ordered.shape[1] == 2:
        indices = np.unique(np.round(np.linspace(0, len(ordered) - 1, count)).astype(int))
    else:
        indices = _farthest_points(ordered, count)
    span = ordered.max(axis=0) - ordered.min(axis=0)
    return ordered[indices] + shift * span


def _farthest_points(points: NDArray[np.float64], count: int) -> NDArray[np.int_]:
    """Indices of `count` points, each the farthest from those chosen before (normalized)."""
    span = points.max(axis=0) - points.min(axis=0)
    scaled = (points - points.min(axis=0)) / np.where(span > 0, span, 1.0)
    chosen = [0]
    distance = np.linalg.norm(scaled - scaled[0], axis=1)
    while len(chosen) < count:
        next_index = int(np.argmax(distance))
        chosen.append(next_index)
        distance = np.minimum(distance, np.linalg.norm(scaled - scaled[next_index], axis=1))
    return np.sort(np.asarray(chosen, dtype=int))
