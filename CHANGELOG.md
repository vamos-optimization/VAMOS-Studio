# Changelog

All notable changes to VAMOS-Studio are documented in this file. VAMOS-Studio has its own version
numbers, independent of VAMOS's: the [README](README.md) says which VAMOS series each version works
with.

## 0.1.0 (unreleased)

Works with VAMOS 1.1.

### Added

- The app's shell: a home page with a card for each page, and the Explore, Optimize and Analyze
  sections, organized as Transept's.
- **Explore › Algorithms** (prototype): the parameter space of NSGA-II for real-coded problems
  as a grammar, shown as a tree, as a table of parameters with when each one is active, as its
  default configuration (a command line that runs exactly as VAMOS's default NSGA-II) and as
  downloadable YAML. The other algorithms and encodings are listed as coming soon.
- **Explore › Problems** (prototype): VAMOS's problem families, with the real-coded ZDT problems
  (ZDT1–4, ZDT6) available: their variables, objectives, bounds and reference front. ZDT5 (binary)
  and the other families are listed as coming soon.
- **Explore › Quality indicators**: the ten indicators of VAMOS with what each one measures,
  whether higher or lower is better and what it is measured against; HV, NHV, IGD, IGD+, additive
  epsilon and Δp are available, the others list why not yet. Fronts are normalized with their
  problem's reference front, as Evolver does, so values match Evolver-Studio's. A sandbox moves
  points of a ZDT reference front away from it and shows how each indicator responds.
- Fronts are measured against **jMetal's reference fronts** (release 7.11), the same files Evolver
  and Evolver-Studio use, copied into the studio by `make sync-resources` with their checksums
  and jMetal's license. VAMOS 1.1's ZDT samples are inaccurate (up to 0.0146 off the true front
  for ZDT4, whose bounds are wrong too); jMetal's lie on the true fronts. Explore › Problems and
  Explore › Quality indicators say where each front comes from.
- **Optimize › New run**: choose a ZDT problem and NSGA-II, adjust its configuration from the
  default one in a form built from its grammar (only the active parameters are shown, and the
  changes and the equivalent command line are listed), set the evaluations and the seed, and
  launch the run in the background, as a worker process that survives the browser.
- **Optimize › Monitor**: follow a run live (generation, evaluations, elapsed time and its
  non-dominated front over the reference front), stop it keeping what it found, or cancel it; see
  why a run failed or was interrupted.
- **Live view** (New run): a run can be slowed down to watch its front converge in the Monitor,
  pausing a chosen time every chosen number of generations, with an estimate of what the pauses
  add. The front is reported before each pause; the pauses change the runtime, never the results.
  The Monitor refreshes twice a second.
- **Optimize › History**: every run with its state, problem, algorithm, budget and seed; open one
  in the monitor or in the results; delete runs, after confirming, to a trash from where they can
  be restored, or empty it for good. Active runs cannot be deleted: cancel them first.
- **Analyze › Results**: the front of a run with its knee and extremes, its quality indicators,
  its solutions (downloadable as FUN.csv and VAR.csv), and its details: evaluations, runtime,
  configuration, the specification VAMOS resolved, and a check of VAMOS's run artifact.
- Runs are kept in `solve-runs/` (or `$VAMOS_STUDIO_RUNS`), each with VAMOS's run artifact.
- Parameter spaces as grammars (`vamos.parameter-space` 1.0.0) and configurations as their
  derivations, with a validator, YAML serialization and content hashes; see
  `docs/design/parameter-spaces.md`.
