# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this
repository.

## Project overview

VAMOS-Studio is a **Python/Streamlit GUI and analysis tool for
[VAMOS](https://github.com/vamos-optimization/VAMOS)**, a Python framework for multi-objective
optimization. It is inspired by Evolver-Studio (a Streamlit front end for the Java framework
Evolver) and reuses its design: the same page structure, the same split between Streamlit pages
and pure, testable modules, and the same file-based contract with runs in separate processes.
The difference is the backend: VAMOS, called from Python, instead of a Java jar.

The roadmap, in phases:

1. **Explore + Solve** (current): catalogue of algorithms, problems and indicators; run an
   algorithm on a problem with a live view of the front, cancel it, inspect the result.
2. **Training**: automatic algorithm configuration through the `vamos tune` CLI.
3. **Validation**: VAMOS studies (`StudySpec`, `create_study`) plus a statistical-analysis layer
   (Wilcoxon, effect sizes, rankings, attainment, LaTeX/SAES export).

VAMOS also ships its own experimental Panel-based studio (`vamos studio`). VAMOS-Studio is a
separate project and does not depend on it.

## Architecture

```
Streamlit UI (pages/)
  └─> vamos_studio/ (pure modules: forms, figures, state, polling)
        └─> vamos_studio/backend/  <- the only package that imports `vamos`
              ├─> catalogue: algorithms, problems, parameter spaces
              ├─> runs: create a run directory, launch the worker, find, cancel
              └─> worker: `python -m vamos_studio.backend.worker <run_dir>`
                    -> vamos.optimize(..., live_viz=<writes status and live front>)
                    -> vamos.save_result(result, <run_dir>/run)
```

No server: a run is a detached worker process, and the UI polls files in its run directory
(`solve-runs/<timestamp>/`): `request.json`, `pid.txt`, `status.json`, the live front, a `stop`
file to request cancellation, `worker.log` and `run/`, VAMOS's stable run artifact
(`manifest.json`, `result.npz`, `environment.json`), read back with `vamos.load_result` and
checkable with `vamos.verify_run`. Runs survive closing the browser.

## Relationship to VAMOS

- Prefer VAMOS's **stable** surfaces: `vamos.optimize`, `vamos.save_result`, `vamos.load_run`,
  `vamos.load_result`, `vamos.verify_run`, `vamos.algorithms` (config classes,
  `available_algorithms`, operator discovery) and `vamos.problems`.
- Some needs (problem metadata, parameter spaces of each algorithm, the live-visualization
  protocol with `should_stop()`) are only covered by **internal or experimental** VAMOS code in
  1.1. Use them only inside `vamos_studio/backend/`, and keep VAMOS pinned to a minor series
  (`pyproject.toml`). A drift-detection test must fail when VAMOS adds or removes algorithms or
  parameters that the catalogue has not triaged.
- Parameter spaces follow [docs/design/parameter-spaces.md](docs/design/parameter-spaces.md):
  strict grammars (Evolver's derivation-tree model) shared with the future VAMOS-CONFIG.

### Changes that belong in VAMOS: local first, upstream later

When VAMOS-Studio needs something VAMOS lacks (e.g. a public parameter-space facade with
defaults), build a **temporary local version here first**, and move it into VAMOS once real use
has validated its design. VAMOS treats every public surface as a compatibility commitment for its
whole 1.x series, so this keeps the studio unblocked without freezing an untested API in VAMOS.

- **Adapters only.** Local versions may only add to or read from VAMOS: catalogue, parameter
  spaces and their defaults, serialization, progress protocols. Never reimplement or monkeypatch
  VAMOS's algorithms, operators, problems or quality indicators: a bug there is fixed in VAMOS
  itself, because it changes scientific results.
- **One place.** They live in `vamos_studio/backend/upstream/`. Each module starts with a header
  naming its target location in VAMOS and its status, and is listed in [UPSTREAM.md](UPSTREAM.md).
- **Written as VAMOS code.** Follow VAMOS's naming, strict typing and test style, with tests that
  move with the module, so upstreaming is a near copy.
- **Removed when VAMOS ships it.** Delete the local version, raise the VAMOS pin in a `build:`
  commit, and update `UPSTREAM.md`.

## Build and test commands

Dependencies live in the **Conda environment** `vamos-studio` (`environment.yml`, backed by
`pyproject.toml`):

```bash
make env     # create or update the environment
make lint    # ruff check . and ruff format --check .
make format  # ruff format .
make test    # pytest tests/ -x
make run     # streamlit run app.py
make sync-resources  # refresh the reference fronts copied from jMetal
```

## Conventions

Follow `CODING_GUIDELINES.md` (Python style, typing, testing) and `GIT_GUIDELINES.md`
(Conventional Commits, atomic commits, `develop`/`main`). Code, identifiers, comments and docs
are in English. Every user-visible change adds an entry to `CHANGELOG.md`.
