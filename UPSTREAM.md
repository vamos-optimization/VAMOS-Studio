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
