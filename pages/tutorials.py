"""Tutorials: interactive, step-by-step tutorials, grouped by level.

Adapted from Evolver-Studio's Tutorials page (pages/tutorials.py), by the same authors.
"""

import streamlit as st

from vamos_studio import (
    tutorial_parameter_spaces,
    tutorial_reading_fronts,
    tutorial_solving,
    tutorial_tour,
)
from vamos_studio.tutorial_navigation import SELECTED_KEY, STEP_KEY, go_to_step, open_tutorial
from vamos_studio.tutorials import (
    TUTORIALS,
    VAMOS_TUTORIALS_URL,
    Tutorial,
    TutorialLevel,
    tutorials_by_level,
    vamos_tutorial_url,
)

# Steps of every tutorial with content in this app, by topic (see Tutorial.available).
TUTORIAL_STEPS = {
    "tour": tutorial_tour.STEPS,
    "solving": tutorial_solving.STEPS,
    "reading_fronts": tutorial_reading_fronts.STEPS,
    "parameter_spaces": tutorial_parameter_spaces.STEPS,
}


def _render_catalogue() -> None:
    st.markdown(
        "Step-by-step tutorials on VAMOS-Studio. Those that run something launch their runs "
        "from a button, and end with a **Jupyter notebook** that does the same with VAMOS's "
        "Python API. Each one pairs with the "
        f"[tutorials of VAMOS's documentation]({VAMOS_TUTORIALS_URL}) (T01, T03…) that cover "
        "the same ground with Python code. The ones still to be written are listed without a "
        "number."
    )
    for level in TutorialLevel:
        st.subheader(level.value)
        for item in tutorials_by_level(level):
            _render_catalogue_entry(item)


def _render_catalogue_entry(item: Tutorial) -> None:
    pairs = ", ".join(f"[{number}]({vamos_tutorial_url(number)})" for number in item.pairs_with)
    extras = [f"pairs with {pairs}"] if pairs else []
    if item.notebook:
        extras.append("with a notebook")
    with st.container(border=True):
        st.markdown(f"**{item.label}**" + (f" — {' · '.join(extras)}" if extras else ""))
        st.caption(item.summary)
        st.button(
            "Start" if item.available else "Coming soon",
            key=f"tutorial_open_{item.slug}",
            disabled=not item.available,
            on_click=open_tutorial,
            args=(item.slug,),
        )


def _render_tutorial(item: Tutorial) -> None:
    steps = TUTORIAL_STEPS[item.slug]
    step = min(st.session_state.get(STEP_KEY, 0), len(steps) - 1)
    st.button("← All tutorials", on_click=open_tutorial, args=(None,))
    st.header(item.label)
    st.progress((step + 1) / len(steps), text=f"Step {step + 1} of {len(steps)}")
    st.subheader(steps[step].title)
    steps[step].render()
    previous_column, next_column = st.columns(2)
    previous_column.button("← Previous", disabled=step == 0, on_click=go_to_step, args=(step - 1,))
    next_column.button(
        "Next →", disabled=step == len(steps) - 1, on_click=go_to_step, args=(step + 1,)
    )


st.title("Tutorials")

selected_slug = st.session_state.get(SELECTED_KEY)
selected = next((t for t in TUTORIALS if t.slug == selected_slug and t.available), None)
if selected is None:
    _render_catalogue()
else:
    _render_tutorial(selected)
