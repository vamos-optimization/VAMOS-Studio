"""Writes the companion notebooks of the tutorials (vamos_studio/notebooks/), without outputs.

Run it after changing a notebook's cells here: `python scripts/make_tutorial_notebooks.py`.
tests/test_tutorial_notebooks.py executes every notebook and checks that it finds the values its
tutorial announces.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

NOTEBOOKS = Path(__file__).resolve().parent.parent / "vamos_studio" / "notebooks"
DOCS = "https://vamos-optimization.org/tutorials"

SETUP = '''\
from importlib.resources import files

import numpy as np
import plotly.graph_objects as go
import vamos
from vamos.algorithms import NSGAIIConfig
from vamos.foundation.quality_indicators import get_indicator

print("VAMOS", vamos.__version__)


def reference_front(name: str) -> np.ndarray:
    """A reference front copied from jMetal, as VAMOS-Studio ships it (e.g. "ZDT1.csv")."""
    path = files("vamos_studio") / "resources" / "referenceFronts" / name
    return np.loadtxt(path, delimiter=",", ndmin=2)


def indicators(front: np.ndarray, reference: np.ndarray) -> dict[str, float]:
    """HV and IGD+ as VAMOS-Studio computes them: objectives normalized by the reference front."""
    lower = reference.min(axis=0)
    span = reference.max(axis=0) - lower
    span[span == 0] = 1.0
    normalized, normalized_reference = (front - lower) / span, (reference - lower) / span
    hv = get_indicator("hv", reference_point=np.ones(front.shape[1]))
    igd_plus = get_indicator("igd_plus", reference_front=normalized_reference)
    return {
        "HV": round(float(hv.compute(np.clip(normalized, 0.0, 1.0)).value), 4),
        "IGD+": round(float(igd_plus.compute(normalized).value), 4),
    }


def plot(front: np.ndarray, reference: np.ndarray, title: str) -> go.Figure:
    """A two-objective front in blue over its reference front in grey."""
    figure = go.Figure()
    figure.add_scatter(
        x=reference[:, 0], y=reference[:, 1], mode="markers", name="Reference front",
        marker={"size": 3, "color": "#b7bcc5"},
    )
    figure.add_scatter(
        x=front[:, 0], y=front[:, 1], mode="markers", name="Front",
        marker={"size": 7, "color": "#1769aa"},
    )
    figure.update_layout(title=title, xaxis_title="f1", yaxis_title="f2")
    return figure'''

S2_DEFAULT = """\
default = NSGAIIConfig.default(pop_size=100, n_var=30)
result = vamos.optimize(
    "zdt1", algorithm="nsgaii", algorithm_config=default, max_evaluations=25000, seed=1
)
front = np.asarray(result.F)
zdt1 = reference_front("ZDT1.csv")
print(len(front), "solutions", indicators(front, zdt1))  # 100 solutions, HV 0.6593, IGD+ 0.0038
plot(front, zdt1, "NSGA-II on ZDT1").show()"""

S2_OTHER = """\
import dataclasses

other = dataclasses.replace(
    NSGAIIConfig.default(pop_size=50, n_var=30),
    crossover=("blx_alpha", {"prob": 0.9, "alpha": 0.5}),
)
result = vamos.optimize(
    "zdt1", algorithm="nsgaii", algorithm_config=other, max_evaluations=25000, seed=1
)
front = np.asarray(result.F)
print(len(front), "solutions", indicators(front, zdt1))  # 50 solutions, HV 0.6495, IGD+ 0.0091"""

S2_ZDT4 = """\
zdt4 = reference_front("ZDT4.csv")
for budget in (10000, 25000):
    result = vamos.optimize(
        "zdt4",
        algorithm="nsgaii",
        algorithm_config=NSGAIIConfig.default(pop_size=100, n_var=10),
        max_evaluations=budget,
        seed=1,
    )
    print(budget, "evaluations:", indicators(np.asarray(result.F), zdt4))
# 10000 evaluations: HV 0.0, IGD+ 0.827; 25000 evaluations: HV 0.6566, IGD+ 0.0054"""

S3_SHAPES = """\
for name in ("ZDT1", "ZDT2", "ZDT3"):
    front = reference_front(f"{name}.csv")
    plot(front, front, f"The Pareto front of {name}").show()"""

S3_MEASURING = '''\
zdt1 = reference_front("ZDT1.csv")
zdt1 = zdt1[np.argsort(zdt1[:, 0])]


def approximation(points: int, shift: float) -> np.ndarray:
    """`points` evenly spread points of the front, moved by `shift` times each range."""
    rows = np.unique(np.round(np.linspace(0, len(zdt1) - 1, points)).astype(int))
    return zdt1[rows] + shift * (zdt1.max(axis=0) - zdt1.min(axis=0))


for points, shift in ((100, 0.0), (5, 0.0), (100, 0.05)):
    print(points, "points, shift", shift, indicators(approximation(points, shift), zdt1))'''

S3_RUN = """\
default = NSGAIIConfig.default(pop_size=100, n_var=12)
result = vamos.optimize(
    "dtlz2", algorithm="nsgaii", algorithm_config=default, n_obj=3,
    max_evaluations=25000, seed=1,
)
front = np.asarray(result.F)
dtlz2 = reference_front("DTLZ2.3D.csv")
print(len(front), "solutions", indicators(front, dtlz2))  # 100 solutions, HV 0.3745, IGD+ 0.039
figure = go.Figure()
figure.add_scatter3d(
    x=dtlz2[:, 0], y=dtlz2[:, 1], z=dtlz2[:, 2], mode="markers", name="Reference front",
    marker={"size": 1, "color": "#b7bcc5"},
)
figure.add_scatter3d(
    x=front[:, 0], y=front[:, 1], z=front[:, 2], mode="markers", name="Front",
    marker={"size": 3, "color": "#1769aa"},
)
figure.show()"""

S4_DEFAULT = """\
from vamos.algorithms import available_crossover_methods

default = NSGAIIConfig.default(pop_size=100, n_var=30)
for field in ("pop_size", "crossover", "mutation", "selection", "offspring_size"):
    print(f"{field:15s}", getattr(default, field))
print("crossovers for real-coded problems:", available_crossover_methods("real"))"""

S4_BUILDER = """\
config = (
    NSGAIIConfig.builder()
    .pop_size(50)
    .crossover("blx_alpha", prob=0.9, alpha=0.5)
    .mutation("pm", prob=1 / 30, eta=20.0)
    .selection("tournament", size=2)
    .build()
)
zdt1 = reference_front("ZDT1.csv")
for name, algorithm_config in (("default", default), ("built", config)):
    result = vamos.optimize(
        "zdt1", algorithm="nsgaii", algorithm_config=algorithm_config,
        max_evaluations=25000, seed=1,
    )
    print(name, indicators(np.asarray(result.F), zdt1))
# default: HV 0.6593, IGD+ 0.0038; built: HV 0.6495, IGD+ 0.0091 (S2's other configuration)"""


def s2_solving() -> nbformat.NotebookNode:
    return new_notebook(
        cells=[
            new_markdown_cell(
                "# S2. Solving a problem, in Python\n\n"
                "The companion of VAMOS-Studio's tutorial *S2. Solving a problem*: the same runs "
                "with VAMOS's Python API. Each run is fixed by its seed, so it finds the same "
                "front and the same values as the tutorial (measured with VAMOS 1.5.0). It pairs "
                f"with VAMOS's tutorial [T01. Your first result]({DOCS}/t01-first-result/)."
            ),
            new_markdown_cell(
                "## Setup\n\nThe reference fronts are jMetal's, which VAMOS-Studio ships, and the "
                "indicators are computed as the studio computes them: with the objectives "
                "normalized so that the reference front spans [0, 1]."
            ),
            new_code_cell(SETUP),
            new_markdown_cell(
                "## NSGA-II with its default configuration on ZDT1\n\n`vamos.optimize` takes a "
                "problem, an algorithm, its configuration and a budget. `NSGAIIConfig.default` is "
                "NSGA-II's default configuration, the one VAMOS-Studio starts from, with a "
                "population of 100. (Without a configuration, `vamos.optimize` chooses a quick "
                "one for a first look, with a population of max(50, 10 × variables) up to 200: "
                "200 on ZDT1, so it would find another front.)"
            ),
            new_code_cell(S2_DEFAULT),
            new_markdown_cell(
                "## Another configuration\n\nStart from the default configuration and change two "
                "things: a population of 50 and BLX-α crossover (with probability 0.9 and α = 0.5, "
                "the values VAMOS-Studio uses)."
            ),
            new_code_cell(S2_OTHER),
            new_markdown_cell(
                "## A harder problem: ZDT4\n\nZDT4 has the same front as ZDT1 but many local "
                "fronts. With 10,000 evaluations NSGA-II is still on one of them; with 25,000 it "
                "reaches the true front."
            ),
            new_code_cell(S2_ZDT4),
            new_markdown_cell(
                "## Next\n\nChange the problem, the algorithm (`moead`, `smsemoa`, `nsgaiii`…), "
                "the budget or the seed, and compare. `vamos.available_problem_names()` lists the "
                "problems and `vamos.algorithms.available_algorithms()` the algorithms."
            ),
        ]
    )


def s3_reading_fronts() -> nbformat.NotebookNode:
    return new_notebook(
        cells=[
            new_markdown_cell(
                "# S3. Reading a front and its quality indicators, in Python\n\n"
                "The companion of VAMOS-Studio's tutorial *S3*: fronts of different shapes, how "
                "quality indicators respond to an approximation, and the indicators of a run. It "
                "pairs with VAMOS's tutorial "
                f"[T07. Quality and budget]({DOCS}/t07-quality-and-budget/)."
            ),
            new_code_cell(SETUP),
            new_markdown_cell("## Shapes of fronts\n\nConvex, concave and disconnected:"),
            new_code_cell(S3_SHAPES),
            new_markdown_cell(
                "## Measuring an approximation\n\nTake evenly spread points of the front of ZDT1 "
                "and move them by a fraction of each objective's range, as the tutorial's sliders "
                "do. Few points lower HV (spread); a shift worsens every indicator (convergence)."
            ),
            new_code_cell(S3_MEASURING),
            new_markdown_cell(
                "## The indicators of a run\n\nNSGA-II on DTLZ2 with three objectives: the points "
                "lie on the sphere, but are spread unevenly."
            ),
            new_code_cell(S3_RUN),
        ]
    )


def s4_parameter_spaces() -> nbformat.NotebookNode:
    return new_notebook(
        cells=[
            new_markdown_cell(
                "# S4. Configuring an algorithm, in Python\n\n"
                "The companion of VAMOS-Studio's tutorial *S4. Exploring a parameter space*. In "
                "VAMOS an algorithm's configuration is an object such as `NSGAIIConfig`, built "
                "from its default or with a builder; the studio's parameter spaces describe the "
                "same choices as a grammar."
            ),
            new_code_cell(SETUP),
            new_markdown_cell(
                "## The default configuration\n\nEvery field of the configuration is one of the "
                "choices the parameter space describes:"
            ),
            new_code_cell(S4_DEFAULT),
            new_markdown_cell(
                "## A configuration with a builder\n\nThe builder sets one choice at a time, and "
                "each operator takes its own parameters, as each value of the grammar brings its "
                "own:"
            ),
            new_code_cell(S4_BUILDER),
            new_markdown_cell(
                "## Next\n\nThe other algorithms have their own configuration classes "
                "(`MOEADConfig`, `SMSEMOAConfig`, `NSGAIIIConfig`, `RVEAConfig`…) in "
                "`vamos.algorithms`, with `default()` and `builder()` as NSGA-II's."
            ),
        ]
    )


def main() -> None:
    for name, notebook in (
        ("s2_solving.ipynb", s2_solving()),
        ("s3_reading_fronts.ipynb", s3_reading_fronts()),
        ("s4_parameter_spaces.ipynb", s4_parameter_spaces()),
    ):
        notebook.metadata["kernelspec"] = {
            "name": "python3",
            "display_name": "Python 3",
            "language": "python",
        }
        for index, cell in enumerate(notebook.cells):  # fixed ids: the same file every time
            cell.id = f"cell-{index}"
        nbformat.write(notebook, NOTEBOOKS / name)
        print("wrote", NOTEBOOKS / name)
    # The notebooks' code follows the project's style, as `make format` leaves it.
    subprocess.run(["ruff", "format", str(NOTEBOOKS)], check=True)


if __name__ == "__main__":
    main()
