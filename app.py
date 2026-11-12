"""VAMOS-Studio entrypoint: navigation shell over the app's sections.

Each page is its own script under pages/ (Streamlit's st.navigation model: nothing at Python
module level survives between pages, only st.session_state does). The home page leads to the
others, which are grouped (see vamos_studio/sections.py) by purpose.
"""

import streamlit as st

from vamos_studio.sections import HOME_PAGE, SECTIONS

st.set_page_config(page_title="VAMOS-Studio", page_icon="🧭", layout="wide")

pg = st.navigation(
    {
        "": [st.Page(HOME_PAGE, title="Home", icon="🏠", default=True)],
        **{
            section.name: [
                st.Page(page.path, title=page.title, icon=page.icon) for page in section.pages
            ]
            for section in SECTIONS
        },
    }
)
pg.run()
