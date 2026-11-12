# Changelog

All notable changes to VAMOS-Studio are documented in this file. VAMOS-Studio has its own version
numbers, independent of VAMOS's: the [README](README.md) says which VAMOS series each version works
with.

## 0.1.0 (unreleased)

Works with VAMOS 1.1.

### Added

- The app's shell: a home page with a card for each page, and the Explore (Algorithms, Problems,
  Quality indicators) and Solve (Run algorithm) sections as placeholders.
- **Explore › Algorithms** (prototype): the parameter space of NSGA-II for real-coded problems
  as a grammar, shown as a tree, as a table of parameters with when each one is active, as its
  default configuration (a command line that runs exactly as VAMOS's default NSGA-II) and as
  downloadable YAML. The other algorithms and encodings are listed as coming soon.
- **Explore › Problems** (prototype): VAMOS's problem families, with the real-coded ZDT problems
  (ZDT1–4, ZDT6) available: their variables, objectives, bounds and reference front. ZDT5 (binary)
  and the other families are listed as coming soon.
- Parameter spaces as grammars (`vamos.parameter-space` 1.0.0) and configurations as their
  derivations, with a validator, YAML serialization and content hashes; see
  `docs/design/parameter-spaces.md`.
