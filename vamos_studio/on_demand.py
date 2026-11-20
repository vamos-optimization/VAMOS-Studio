"""Quality indicators computed when the user asks, with a warning when they may take long.

The hypervolume grows quickly with the number of objectives: with a few it takes a moment, with
many it can take minutes. The pages that measure runs offer a button instead of computing on
every visit, and remember the values computed in the session, so that switching tabs or widgets
does not compute them again. Beside the button the user chooses how the hypervolume is computed:
exactly, or by VAMOS's approximation, the default from `SLOW_FROM` objectives.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Final, TypeVar

import streamlit as st

from vamos_studio.backend.indicators import APPROXIMATE, EXACT, HV_METHODS

# From this number of objectives on, the button warns that the hypervolume may take long.
SLOW_FROM: Final = 5
COMPUTE_LABEL: Final = "Compute the quality indicators"
_STORE: Final = "on_demand.values"

T = TypeVar("T")


def slow_warning(n_obj: int) -> str | None:
    """The warning to show before computing the exact hypervolume with `n_obj` objectives."""
    if n_obj < SLOW_FROM:
        return None
    return (
        f"With {n_obj} objectives the exact hypervolume can take from seconds to minutes, growing "
        "with the number of objectives and of solutions; the page waits meanwhile. The "
        "approximate one is much faster."
    )


def default_method(n_obj: int) -> str:
    """The hypervolume method offered first: the approximate one from `SLOW_FROM` objectives."""
    return APPROXIMATE if n_obj >= SLOW_FROM else EXACT


def method_note(hv: str) -> str | None:
    """What to say under the values about how the hypervolume was computed, if approximate."""
    if hv != APPROXIMATE:
        return None
    return (
        "HV and NHV are approximate: VAMOS's estimate of the hypervolume (moocore's Rphi-FWE+, "
        "100,000 samples, deterministic), within about 0.1 % of the exact value in the studio's "
        "checks."
    )


def computed(key: str, n_obj: int, compute: Callable[[str], T]) -> tuple[T, str] | None:
    """The values `compute` returns, once the user asks for them, and the hypervolume method.

    Args:
        key: What the values are of (a run and its reference front, a series...): values already
            computed under it in this session, with the same method, are returned at once.
        n_obj: The number of objectives, which sets the default method and the warning.
        compute: Computes the values, given the hypervolume method (`EXACT` or `APPROXIMATE`).

    Returns:
        The values and the method, or None until the user asks.
    """
    hv = st.radio(
        "Hypervolume",
        list(HV_METHODS),
        index=list(HV_METHODS).index(default_method(n_obj)),
        format_func=HV_METHODS.get,
        horizontal=True,
        key=f"hv_method:{key}",
        help="How HV and NHV compute the hypervolume. The exact one grows exponentially with the "
        "number of objectives; VAMOS's approximation stays fast and is within about 0.1 %.",
    )
    store: dict[str, object] = st.session_state.setdefault(_STORE, {})
    stored = f"{key}:{hv}"
    if stored in store:
        return store[stored], hv  # type: ignore[return-value]
    warning = slow_warning(n_obj) if hv == EXACT else None
    if warning is not None:
        st.warning(warning, icon=":material/hourglass_top:")
    if not st.button(COMPUTE_LABEL, key=f"compute:{key}", icon=":material/calculate:"):
        return None
    with st.spinner("Computing the quality indicators…"):
        store[stored] = compute(hv)
    return store[stored], hv  # type: ignore[return-value]
