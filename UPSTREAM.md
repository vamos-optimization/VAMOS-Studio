# Upstream candidates

Temporary local versions of features that belong in VAMOS. They live in
`vamos_studio/backend/upstream/` and follow the rules in [CLAUDE.md](CLAUDE.md) ("Changes that
belong in VAMOS: local first, upstream later").

Status values: **local** (used only here), **proposed** (issue or pull request open in VAMOS),
**upstreamed** (released in VAMOS; the local version is deleted).

| Local module | Target in VAMOS | Purpose | Status | VAMOS issue/PR |
| --- | --- | --- | --- | --- |
| `parameter_space.py` | `vamos.algorithms.parameter_space`, schemas `vamos.parameter-space` and `vamos.parameter-configuration` | Parameter spaces as grammars and configurations as derivations: model, validator (G1–G5), YAML, hashes ([design](docs/design/parameter-spaces.md)) | local | — |
| `vamos_bridge.py` | Per-algorithm configuration builders of `vamos.algorithms` | From a configuration to a VAMOS algorithm configuration, undoing the renames M1 and M2 | local | — |
| `spaces/nsgaii_real.yaml` | Grammars shipped as VAMOS resources | NSGA-II for real-coded problems, with M1–M5 applied | local | — |
| `resources/referenceFronts/ZDT*.csv` (jMetal 7.11) | The reference fronts VAMOS ships | Exact ZDT fronts, the same files Evolver uses; VAMOS 1.1's are inaccurate. VAMOS `main` already ships exact fronts with a different sampling: decide whether VAMOS adopts jMetal's files, so that IGD-like values match across frameworks | local | — |
| _postponed_ | A time limit in VAMOS's termination, e.g. `("max_time", seconds)` | Stop a run after some computing time, as Transept does. VAMOS 1.1 only ends by evaluations or a hypervolume target; the studio could stop by time through `should_stop()`, but this is postponed until VAMOS supports it | proposed idea | — |
