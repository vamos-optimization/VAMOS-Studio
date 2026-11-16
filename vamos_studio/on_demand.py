"""Quality indicators computed when the user asks, with a warning when they may take long.

The hypervolume grows quickly with the number of objectives: with a few it takes a moment, with
many it can take minutes. The pages that measure runs offer a button instead of computing on
every visit, and remember the values computed in the session, so that switching tabs or widgets
does not compute them again.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Final, TypeVar

import streamlit as st

# From this number of objectives on, the button warns that the hypervolume may take long.
SLOW_FROM: Final = 5
COMPUTE_LABEL: Final = "Compute the quality indicators"
_STORE: Final = "on_demand.values"

T = TypeVar("T")


def slow_warning(n_obj: int) -> str | None:
    """The warning to show before computing indicators with `n_obj` objectives, if any."""
    if n_obj < SLOW_FROM:
        return None
    return (
        f"With {n_obj} objectives the hypervolume can take from seconds to minutes, growing with "
        "the number of objectives and of solutions; the page waits meanwhile."
    )


def computed(key: str, n_obj: int, compute: Callable[[], T]) -> T | None:
    """The values `compute` returns, once the user asks for them; None until then.

    Args:
        key: What the values are of (a run and its reference front, a series...): values already
            computed under it in this session are returned at once.
        n_obj: The number of objectives, to warn when the computation may take long.
        compute: Computes the values.
    """
    store: dict[str, object] = st.session_state.setdefault(_STORE, {})
    if key in store:
        return store[key]  # type: ignore[return-value]
    warning = slow_warning(n_obj)
    if warning is not None:
        st.warning(warning, icon=":material/hourglass_top:")
    if not st.button(COMPUTE_LABEL, key=f"compute:{key}", icon=":material/calculate:"):
        return None
    with st.spinner("Computing the quality indicators…"):
        store[key] = compute()
    return store[key]  # type: ignore[return-value]
