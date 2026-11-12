"""Home: what VAMOS-Studio offers, with a card leading to each of its pages."""

import streamlit as st

from vamos_studio.backend import vamos_version
from vamos_studio.sections import SECTIONS, Page, Section

VAMOS_URL = "https://github.com/vamos-optimization/VAMOS"
CARDS_PER_ROW = 3


def _render_card(section: Section, page: Page) -> None:
    with st.container(border=True, height="stretch"):
        st.caption(section.name.upper())
        st.markdown(f"#### {page.icon} {page.title}")
        if page.available:
            st.badge("Available", icon=":material/check:", color="green")
        else:
            st.badge("Coming soon", icon=":material/construction:", color="gray")
        st.markdown(page.description)
        st.page_link(page.path, label=f"Open {page.title}", icon=":material/arrow_forward:")


installed = vamos_version()

st.title("VAMOS-Studio")
st.markdown(
    f"A graphical front end for [VAMOS]({VAMOS_URL}), a Python framework for multi-objective "
    "optimization: explore its algorithms and problems, and run them with a live view of the front."
)
if installed is None:
    st.error("VAMOS is not installed: install `vamos-optimization` in this environment.")
else:
    st.caption(f"Backend: VAMOS {installed}")

cards = [(section, page) for section in SECTIONS for page in section.pages]
for start in range(0, len(cards), CARDS_PER_ROW):
    for column, (section, page) in zip(
        st.columns(CARDS_PER_ROW), cards[start : start + CARDS_PER_ROW]
    ):
        with column:
            _render_card(section, page)
