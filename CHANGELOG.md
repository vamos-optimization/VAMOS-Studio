# Changelog

All notable changes to VAMOS-Studio are documented in this file. VAMOS-Studio has its own version
numbers, independent of VAMOS's: the [README](README.md) says which VAMOS series each version works
with.

## 0.1.0 (unreleased)

Works with VAMOS 1.4 (1.4.0 or later).

### Added

- The app's shell: a home page and the Explore, Optimize and Analyze sections, organized as
  Transept's, in a menu along the top with Material icons.
- **The VAMOS logo and colors**: the logo heads the menu and the home page, its V is the tab's
  icon, and the theme takes its colors (blue to teal on navy) and typefaces (Montserrat and IBM
  Plex Sans).
- **A light and a dark theme**: the studio follows the system's preference, and ⋮ › Settings
  chooses Light, Dark or System. The dark theme takes the colors of the VAMOS website's dark mode;
  the figures of fronts and the logo have their own tones for it.
- **Home** as a panel of the studio: the front of the latest run (live while it runs, with a link to
  the Monitor; once finished, over its reference front with its HV and IGD+ and a link to Results;
  DTLZ2's front before any run), a first run in one click (NSGA-II on ZDT1, followed in the
  Monitor), the pages grouped by section as in Transept (Explore, Optimize and Analyze numbered
  as the steps of a study, then Learn), each section with what it has now, next to first steps, the
  news of this changelog and the four latest runs, one line each with their state.
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
- **MOEA/D and SMS-EMOA**, for real-coded and binary problems, with their grammars
  (`moead_real`, `moead_binary`, `smsemoa_real`, `smsemoa_binary`). Their mutation probability is
  a factor of 1/n, as NSGA-II's. With three or more objectives MOEA/D reads jMetal's weight vector
  file for its population (`W<m>D_<population>.dat`, shipped with VAMOS), as jMetal and Evolver
  do: New run says which file and which populations have one. SMS-EMOA is built by the studio
  itself, so that its grammar can express VAMOS's default (random selection, reference point
  offset 1.0). The real-coded defaults run exactly as VAMOS's (MOEA/D with three objectives, as it
  with jMetal's file); VAMOS has no binary defaults for them, so theirs are NSGA-II's binary ones.
  NSGA-II stays the default algorithm. At the end of any run, the Monitor shows its result.
- **Series of independent runs**, as in Transept: New run launches several runs of the same
  configuration with consecutive seeds, a chosen number at a time, through a background process that
  survives the browser. A series measured against an approximate front copies it once, so all its
  runs use the same version. The Monitor follows a series (its runs, their progress, the current
  fronts of the runs in progress in blue over those finished in grey, stop or cancel), History shows
  which series each run belongs to and deletes whole series, and **Results** lists a series as one
  entry, as Transept does: it shows either the aggregate (the fronts of its runs and their union,
  and each run's quality indicators with their median, interquartile range, mean, standard
  deviation, minimum and maximum, to download, with the best run by any indicator) or any of its
  runs.
- **DTLZ with up to 20 objectives**: New run offers 2 to 20 objectives for the DTLZ problems.
  jMetal's reference fronts of DTLZ1–4 and DTLZ7 with four, six and eight objectives are copied
  beside the others; with any other number (and DTLZ5 and DTLZ6 beyond three) a run has no exact
  front and builds an approximate one by default. With four or more objectives every front is drawn
  in parallel coordinates (Results, Monitor, series, Explore › Problems and the home page): one line
  per solution across one axis per objective, each scaled over the reference front, with the values
  on hover. MOEA/D reads jMetal's weight vector file for its number of objectives when there is one,
  and otherwise a Das-Dennis lattice (see NSGA-III below).
- **AGE-MOEA, RVEA and SPEA2** for real-coded problems: their grammars (`agemoea_real`, `rvea_real`,
  `spea2_real`), built from VAMOS's tuning spaces with the same changes as SMS-EMOA's (external
  archive, a distribution index per polynomial mutation, the mutation probability as a factor of
  1/n), whose defaults run exactly as VAMOS's. RVEA has no population of its own: it is the
  Das-Dennis lattice of its divisions for the problem's objectives (13 with two, 91 with three, by
  default), and New run shows it.
- **Tutorials** (Learn › Tutorials), as Evolver-Studio's: interactive and step by step, grouped by
  level, each paired with the tutorials of VAMOS's documentation. The basic ones are written: S1. A
  tour of VAMOS-Studio, S2. Solving a problem, S3. Reading a front and its quality indicators, and
  S4. Exploring a parameter space; the others are listed as planned. A tutorial launches its runs
  from a button, fixed by a seed, and says whether they give the values it announces. Unlike
  Evolver-Studio, each tutorial that runs something comes with a Jupyter notebook that does the same
  with VAMOS's Python API (`vamos_studio/notebooks/`, written by
  `scripts/make_tutorial_notebooks.py`); the tests execute the notebooks and check that they find
  those values.
- **NSGA-III** for real-coded problems (`nsgaiii_real`), whose default runs exactly as VAMOS's: SBX
  with distribution index 30, a tournament (VAMOS's NSGA-III selects only by tournament) and the
  largest Das-Dennis lattice of reference directions that fits the population. New run says how many
  directions it uses, how many solutions RVEA runs with (warning when they are fewer than 50 or more
  than 1,000) and which weight vectors MOEA/D reads; without a jMetal weight file for its number of
  objectives (six, seven, nine…), MOEA/D runs on VAMOS's largest Das-Dennis lattice that fits the
  population instead of being refused. With four or more objectives New run warns that NSGA-II and
  SPEA2 lose selection pressure and that SMS-EMOA can be very slow.
- **Quality indicators on request**: Results, the aggregate of a series and, with four or more
  objectives, the indicator sandbox compute them when asked, with a warning from five objectives
  that the hypervolume may take long; values computed are kept while the session lasts. The home
  page shows HV and IGD+ of the latest result only with two or three objectives.
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

### Changed

- **VAMOS 1.4.0 or later** (up to 1.5) instead of 1.2.1. The algorithms' parameter spaces are now
  **VAMOS's own grammars**, which VAMOS 1.4 ships on the model the studio prototyped: the studio
  adds the population size, the subset selection of an unbounded archive and the labels of the
  forms. Parameters take Evolver's names (`sbx_distribution_index`, `crossover_probability`,
  `tournament_size`, `initial_solutions`, ...); MOEA/D gains Evolver's options (subproblem order,
  DE schemes and base, augmented and inverted aggregations, normalization of the objectives,
  crossover and mutation instead of DE); SMS-EMOA and the others gain Evolver's operators and
  Sobol, Halton and opposition-based initialization. RVEA takes a population size, and runs the
  largest Das-Dennis lattice up to it. MOEA/D with three or more objectives runs the largest
  population up to its size with weight vectors, a complete lattice before one of jMetal's files.
  Default configurations run as before. Runs saved with earlier grammars keep their
  configuration, which Results shows as saved. Problems with other arguments (ZCAT's `level`,
  the knapsack's `capacity_ratio`) are given to VAMOS by id, so their runs replay exactly.
- **VAMOS 1.2.1 or later** (up to 1.3) instead of 1.1. Following VAMOS 1.2's new defaults, the
  grammars of NSGA-II and SMS-EMOA for real-coded problems apply SBX with probability 0.9 instead
  of 1.0, the simplex crossover's expansion defaults to 2.0 within [1, 3], and SMS-EMOA no longer
  offers the three-parent crossovers (PCX, UNDX, simplex), which VAMOS 1.2 cannot run with
  SMS-EMOA's pairs of parents. Explore lists VAMOS 1.2's constrained algorithms (CCMO, C-TAEA,
  ToP, CMOEA-MS), not yet available in the studio. The k-means subset selection uses a fixed seed.
