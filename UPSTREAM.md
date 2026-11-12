# Upstream candidates

Temporary local versions of features that belong in VAMOS. They live in
`vamos_studio/backend/upstream/` and follow the rules in [CLAUDE.md](CLAUDE.md) ("Changes that
belong in VAMOS: local first, upstream later").

Status values: **local** (used only here), **proposed** (issue or pull request open in VAMOS),
**upstreamed** (released in VAMOS; the local version is deleted).

| Local module | Target in VAMOS | Purpose | Status | VAMOS issue/PR |
| --- | --- | --- | --- | --- |
| `parameter_space.py` (planned) | `vamos.algorithms.parameter_space`, schemas `vamos.parameter-space` and `vamos.parameter-configuration` | Parameter spaces as grammars, with defaults, validation and configurations ([design](docs/design/parameter-spaces.md)) | local (planned) | — |
