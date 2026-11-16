"""The theme the viewer sees: light or dark.

The studio defines both themes in .streamlit/config.toml ([theme.light] and [theme.dark]); it
follows the system's preference, and the viewer can choose Light, Dark or System in ⋮ › Settings.
Streamlit reruns the app when the theme changes, so a figure drawn with colours of its own reads
the theme on every run.
"""

from __future__ import annotations

import streamlit as st


def is_dark() -> bool:
    """Whether the viewer sees the dark theme (False outside a session, or if it is unknown)."""
    try:
        return st.context.theme.type == "dark"
    except Exception:  # noqa: BLE001 - no session (bare mode, tests): the light theme
        return False
