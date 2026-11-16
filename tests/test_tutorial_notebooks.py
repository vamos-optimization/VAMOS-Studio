"""Tests for the tutorials' notebooks: each one runs and finds the values its tutorial gives."""

import json

import pytest
from nbclient import NotebookClient
from nbformat import reads

from vamos_studio.tutorial_reading_fronts import NSGAII_ON_DTLZ2
from vamos_studio.tutorial_runs import INDICATOR_NAMES, PreparedRun, notebook_text
from vamos_studio.tutorial_solving import DEFAULT_ON_ZDT1, OTHER_ON_ZDT1, ZDT4_LONG, ZDT4_SHORT

# The prepared runs of each notebook's tutorial, whose values the notebook must print.
NOTEBOOK_RUNS = {
    "s2_solving.ipynb": (DEFAULT_ON_ZDT1, OTHER_ON_ZDT1, ZDT4_SHORT, ZDT4_LONG),
    "s3_reading_fronts.ipynb": (NSGAII_ON_DTLZ2,),
    "s4_parameter_spaces.ipynb": (DEFAULT_ON_ZDT1, OTHER_ON_ZDT1),
}


def printed(name: str) -> str:
    """What a notebook prints when executed."""
    notebook = reads(notebook_text(name), as_version=4)
    NotebookClient(notebook, timeout=600, kernel_name="python3").execute()
    return "".join(
        output.get("text", "")
        for cell in notebook.cells
        if cell.cell_type == "code"
        for output in cell.outputs
        if output.get("output_type") == "stream"
    )


def announced(prepared: PreparedRun) -> str:
    """The values of a prepared run as the notebooks print them (rounded to four decimals)."""
    values = {INDICATOR_NAMES[key]: round(value, 4) for key, value in prepared.expected.items()}
    return json.dumps(values).replace('"', "'")[1:-1]


@pytest.mark.parametrize(("name", "prepared_runs"), list(NOTEBOOK_RUNS.items()))
def test_should_find_the_values_the_tutorial_announces(name, prepared_runs):
    # Act
    text = printed(name)

    # Assert
    for prepared in prepared_runs:
        assert announced(prepared) in text, prepared.key
