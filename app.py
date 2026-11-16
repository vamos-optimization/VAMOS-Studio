"""VAMOS-Studio entrypoint: navigation shell over the app's sections.

Each page is its own script under pages/ (Streamlit's st.navigation model: nothing at Python
module level survives between pages, only st.session_state does). The home page leads to the
others, which are grouped (see vamos_studio/sections.py) by purpose. The menu runs along the top,
under the VAMOS logo; the light and dark themes (.streamlit/config.toml) take the logo's colors.
"""

import streamlit as st

from vamos_studio.branding import MARK, wordmark
from vamos_studio.sections import HOME_PAGE, SECTIONS

VAMOS_URL = "https://github.com/vamos-optimization/VAMOS"

st.set_page_config(page_title="VAMOS-Studio", page_icon=MARK, layout="wide")
st.logo(wordmark(), size="large", link=VAMOS_URL)

pg = st.navigation(
    {
        "": [st.Page(HOME_PAGE, title="Home", icon=":material/home:", default=True)],
        **{
            section.name: [
                st.Page(page.path, title=page.title, icon=page.icon) for page in section.pages
            ]
            for section in SECTIONS
        },
    },
    position="top",
)
pg.run()
