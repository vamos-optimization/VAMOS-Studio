# VAMOS-Studio

A graphical front end and analysis tool for [VAMOS](https://github.com/vamos-optimization/VAMOS),
a Python framework for multi-objective optimization. It is inspired by
[Evolver-Studio](https://github.com/jMetal/Evolver), with VAMOS as its backend.

> **Status:** early development (0.1.0.dev0). The app's shell is in place; the pages are being
> implemented.

## Planned features

- **Explore**: VAMOS's algorithms and their parameters, its problems and its quality indicators.
- **Solve**: configure an algorithm, run it on a problem with a live view of the front, cancel it,
  and inspect and export the result.
- Later: automatic algorithm configuration (training with `vamos tune`), validation studies and
  their statistical analysis.

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
