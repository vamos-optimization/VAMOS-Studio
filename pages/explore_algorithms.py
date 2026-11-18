"""Explore algorithms: VAMOS's algorithms and the grammar of the parameters of each one."""

import pandas as pd
import streamlit as st

from vamos_studio.backend.catalogue import (
    ENCODING_LABELS,
    ENCODINGS,
    algorithm_entries,
    default_algorithm_index,
)
from vamos_studio.backend.upstream.vamos_bridge import builtin_space
from vamos_studio.parameter_tree import parameter_rows, summarize, tree_markdown

st.title("Algorithms")
st.markdown(
    "The multi-objective algorithms of VAMOS and how each one can be configured. A parameter "
    "space is a grammar: a categorical parameter chooses a value, and each value activates its "
    "own parameters. The spaces are VAMOS's own, with Evolver's names for the parameters; the "
    "studio adds the population size."
)
st.info(
    "The algorithms with a parameter space in the studio are available; NSGA-II, MOEA/D and "
    "SMS-EMOA also for **binary** problems. The other algorithms and encodings are listed but "
    "not active yet (see *Availability*).",
    icon=":material/construction:",
)

entries = algorithm_entries()
availability = pd.DataFrame(
    [
        {
            "Algorithm": entry.label,
            **{ENCODING_LABELS[enc]: "✅" if enc in entry.encodings else "⏳" for enc in ENCODINGS},
        }
        for entry in entries
    ]
)
with st.expander("Availability: ✅ available · ⏳ coming soon", expanded=False):
    st.dataframe(availability, hide_index=True, width="stretch")

available = [entry for entry in entries if entry.available]
left, right = st.columns(2)
entry = left.selectbox(
    "Algorithm",
    available,
    index=default_algorithm_index(available),
    format_func=lambda item: item.label,
)
encoding = right.selectbox("Encoding", entry.encodings, format_func=ENCODING_LABELS.get)
space = builtin_space(entry.key, encoding)

summary = summarize(space)
metrics = st.columns(4)
metrics[0].metric("Parameters", summary.parameters)
metrics[1].metric("Top level", summary.top_level)
metrics[2].metric("Active by default", summary.default_active)
metrics[3].metric("Depth", summary.depth)

tree_tab, table_tab, default_tab, grammar_tab = st.tabs(
    ["Parameter tree", "Parameters", "Default configuration", "Grammar (YAML)"]
)
with tree_tab:
    st.markdown(tree_markdown(space))
with table_tab:
    st.dataframe(pd.DataFrame(parameter_rows(space)), hide_index=True, width="stretch")
with default_tab:
    default = space.default_configuration()
    st.markdown(
        "The configuration made of every default value. It runs exactly as VAMOS's own default "
        f"configuration of {entry.label}."
    )
    st.code(default.to_cli(), language="bash", wrap_lines=True)
    st.dataframe(
        pd.DataFrame(
            [{"Parameter": name, "Value": str(value)} for name, value in default.values.items()]
        ),
        hide_index=True,
    )
with grammar_tab:
    grammar = space.to_yaml()
    st.caption(f"`{space.name}` · {space.content_hash()}")
    st.download_button(
        "Download YAML",
        grammar,
        file_name=f"{space.name}.yaml",
        mime="application/yaml",
        icon=":material/download:",
    )
    st.code(grammar, language="yaml")
