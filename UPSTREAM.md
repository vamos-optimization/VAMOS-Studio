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
| `resources/referenceFronts/ZDT*.csv`, `DTLZ*.{2D,3D}.csv` (jMetal 7.11) | The reference fronts VAMOS ships | Exact ZDT and DTLZ fronts, the same files Evolver uses; VAMOS 1.1's are inaccurate, and it has no two-objective DTLZ fronts. VAMOS `main` already ships exact fronts with a different sampling: decide whether VAMOS adopts jMetal's files, so that IGD-like values match across frameworks | local | — |
| `subset.py`, grammar parameter `archive_subset_selection` | A final subset selection of unbounded archives in VAMOS's archive configuration, and a normalized farthest-point (DSS) selection | Return a diverse subset of an unbounded archive, as large as the population, as jMetal's BestSolutionsArchive does; VAMOS 1.1 returns the whole archive and its `farthest` selection does not normalize the objectives | local | — |
| `worker.problem_to_solve` | Fix `vamos.optimize(problem_id, problem_kwargs=...)` (`experiment/auto.py`, `_resolve_problem`) | VAMOS 1.1 (and `main`) passes `problem_kwargs` of a problem given by id to `make_problem_selection`, which takes only `n_var` and `n_obj`: any other argument fails (knapsack's `capacity_ratio`, ZCAT's `level`). The studio passes the problem's class instead, which works but loses the exact replay of some problems | local workaround; bug to fix in VAMOS | — |
| `spaces/moead_*.yaml`, `spaces/smsemoa_*.yaml` | Grammars shipped as VAMOS resources | MOEA/D and SMS-EMOA for real-coded and binary problems; M8 turns the absolute mutation probability (default 1/n) into a factor | local | — |
| `vamos_bridge.weight_population`, `with_weight_files` | MOEA/D's weight vectors in VAMOS | jMetal and Evolver read `W<m>D_<population>.dat` with three or more objectives; VAMOS 1.1 reads those files (it ships them) only when given their directory, and its default generates a Das-Dennis lattice, so a population of 100 fails or differs | local | — |
| `vamos_bridge.smsemoa_config` | SMS-EMOA's tuning bridge in VAMOS | VAMOS 1.1's bridge always uses a tournament and a reference point offset of 0.1, so it cannot express SMS-EMOA's default (random selection, offset 1.0) | local | — |
| — | Binary defaults for MOEA/D and SMS-EMOA in VAMOS | `MOEADConfig.default()` and `SMSEMOAConfig.default()` take no encoding and give real-coded operators for binary problems | proposed idea | — |
| _postponed_ | A time limit in VAMOS's termination, e.g. `("max_time", seconds)` | Stop a run after some computing time, as Transept does. VAMOS 1.1 only ends by evaluations or a hypervolume target; the studio could stop by time through `should_stop()`, but this is postponed until VAMOS supports it | proposed idea | — |
