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
- **Optimize › Monitor**: follow a run live (generation, evaluations, elapsed time and its front
  over the reference front), stop it keeping what it found, or cancel it; see why a run failed or
  was interrupted. With an external archive, the live front is the archive, which is what the run
  returns; otherwise, the non-dominated front of the population. The caption says which.
- **Approximate reference fronts**, for problems without a known front (the binary knapsack,
  QUBO and feature selection) or with arguments that change it, and for any other at the user's
  choice. A run can add its non-dominated solutions (its whole archive) to the approximate front
  of its problem, kept for each set of arguments: from New run (on by default when the problem has
  no exact front) or later from Results. The front is the non-dominated union of the runs added,
  at most 10,000 points (farthest-point selection keeps its extremes and spread), with a version
  and the runs it comes from; runs ending at once do not lose each other's points. New run
  chooses what a run is measured against: the exact front, the approximate one, or none. A run
  measured against an approximate front keeps a copy of the version it was launched with, so its
  values do not change as the front grows; Results says which version and can measure with the
  current one. Explore › Problems shows each approximate front, in 2D or 3D, with its runs, to
  download or delete.
- **Binary encoding**: NSGA-II's grammar for binary problems (`nsgaii_binary`: uniform, HUX,
  one-point or two-point crossover and bit-flip or segment-inversion mutation), whose default
  configuration runs exactly as VAMOS's default for binary problems. ZDT5 and the binary
  knapsack, QUBO and feature-selection problems are available, with their arguments; Results shows
  their variables as bits. Without a reference front, a run's indicators are not computed, and the
  indicator sandbox offers only problems with one. A problem's arguments other than its variables
  and objectives (such as knapsack's `capacity_ratio`) reach VAMOS through the problem's class,
  since VAMOS 1.1 fails on them given a problem's id.
- **Problem arguments**, as in Evolver-Studio: each problem's arguments are read from its VAMOS
  constructor, with their types and defaults (ZDT: variables; DTLZ: variables and objectives;
  ZCAT's six are ready for when the family is enabled). Explore › Problems lists them, and there
  and in New run a "Set its arguments" checkbox shows one input per argument; without it, the
  problem keeps its defaults. Changing a DTLZ problem's objectives sets its variables to the
  standard number for them. Arguments VAMOS would accept but that make no sense are refused (a
  DTLZ problem with fewer variables than objectives), and a run cannot be launched with them.
  Runs record their variables; History, the Monitor and Results show them.
- **Subset of an unbounded archive**: a bounded external archive is as large as the population;
  a run with an unbounded one now returns, as jMetal does, a diverse subset of it as large as the
  population instead of every non-dominated solution found (thousands). The new parameter `archive_subset_selection` of NSGA-II's grammar chooses how:
  `farthest` (default: max-min distance on normalized objectives, the greedy selection of
  distance-based subset selection), `crowding`, `hv_greedy`, `kmeans`, or `none` for the whole
  archive; the selection is VAMOS's. Results shows the subset and can show the whole archive; the
  run artifact keeps the whole archive.
- **DTLZ problems and fronts of three objectives**: DTLZ1–7 are available, with two or three
  objectives (chosen in Explore › Problems, New run and the indicator sandbox; VAMOS derives the
  number of variables). Fronts of three objectives are drawn in 3D, which can be rotated, and in
  their three two-objective projections, as Transept draws them: the reference fronts, the live
  front in the Monitor, the front of a run in Results and the sandbox of Explore › Quality
  indicators. The sandbox spreads the points of a surface by farthest-point sampling. History and
  the run selectors show the number of objectives of each run.
- jMetal's DTLZ reference fronts, with two and three objectives, join the copy made by
  `make sync-resources`. VAMOS 1.1 ships none with two objectives (it returns its three-objective
  files), and its three-objective ones are up to 0.052 off the true fronts, with wrong bounds for
  DTLZ6 and DTLZ7.
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
