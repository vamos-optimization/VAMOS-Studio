# VAMOS-Studio

A graphical front end and analysis tool for [VAMOS](https://github.com/vamos-optimization/VAMOS),
a Python framework for multi-objective optimization. It is inspired by
[Evolver-Studio](https://github.com/jMetal/Evolver), with VAMOS as its backend.

> **Status:** first prototype (0.1.0.dev0): NSGA-II on the real-coded ZDT problems. The other
> algorithms, encodings and problems are listed in the app as coming soon.

## What it does

| Section | Page | |
| --- | --- | --- |
| **Explore** | **Algorithms** | The parameter space of each algorithm as a grammar: tree, table, default configuration and YAML |
| | **Problems** | The problem families, with each problem's variables, bounds and reference front |
| | **Quality indicators** | What each indicator measures, with a sandbox to see how they respond |
| **Optimize** | **New run** | Choose a problem and an algorithm, adjust its configuration, set the budget and launch the run |
| | **Monitor** | Follow a run live; stop it keeping its results, or cancel it |
| | **History** | Every run with its state; open one in the monitor or the results |
| **Analyze** | **Results** | The front with its knee and extremes, the quality indicators, the solutions and the details of the run |

Runs go on in the background and are kept in `solve-runs/` (set `VAMOS_STUDIO_RUNS` to use another
directory), each with VAMOS's run artifact. Fronts are measured against jMetal's reference fronts,
the same files Evolver-Studio uses, so the values of both tools match.

## Quick start

VAMOS-Studio needs Python 3.11 or newer. With Conda:

```bash
make env   # creates (or updates) the vamos-studio Conda environment
make run   # opens the app in the browser
```

Or with any virtual environment:

```bash
python -m pip install -e ".[dev]"
streamlit run app.py
```

Install the `fast` extra (`pip install -e ".[fast]"`) for VAMOS's Numba kernels.

## Development

```bash
make test    # pytest
make lint    # ruff check and format check
make format  # ruff format
```

See [CLAUDE.md](CLAUDE.md) for the architecture, [CODING_GUIDELINES.md](CODING_GUIDELINES.md)
and [GIT_GUIDELINES.md](GIT_GUIDELINES.md).
