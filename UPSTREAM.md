# Upstream candidates

Temporary local versions of features that belong in VAMOS. They live in
`vamos_studio/backend/upstream/` and follow the rules in [CLAUDE.md](CLAUDE.md) ("Changes that
belong in VAMOS: local first, upstream later").

Status values: **local** (used only here), **proposed** (issue or pull request open in VAMOS),
**upstreamed** (released in VAMOS; the local version is deleted).

| Local module | Target in VAMOS | Purpose | Status | VAMOS issue/PR |
| --- | --- | --- | --- | --- |
| `parameter_space.py` | `vamos.engine.tuning.grammar` (VAMOS 1.4) | The grammar model the studio reads VAMOS's grammars with: the same schema, `vamos.parameter-space` 1.0.0, plus what the forms use (active children of a value, complete configurations, content hashes) ([design](docs/design/parameter-spaces.md)) | upstreamed as a design; the studio still reads with its own model, a candidate to replace by VAMOS's | #296, #333 |
| `spaces/studio.yaml` | — | The studio's layer over VAMOS's grammars: `pop_size` (a run setting in VAMOS), `archive_subset_selection`, and labels for the forms | local (studio only) | — |
| `vamos_bridge.py` | `config_from_assignment` (VAMOS 1.4) | Loads VAMOS's grammars with the studio's layer; VAMOS builds the configuration, its populations and weight vectors | thin adapter | #333–#336 |
| `resources/referenceFronts/` (jMetal 7.11) | The reference fronts VAMOS ships | VAMOS 1.3 ships jMetal's ZDT and DTLZ fronts with two and three objectives as an optional source (`source="jmetal"`); the studio still needs its copies of the DTLZ fronts with 4, 6 and 8 objectives, which VAMOS does not have (R4 in the notes) | partly upstreamed | #322 |
| `subset.py`, parameter `archive_subset_selection` | `ExternalArchiveConfig.final_selection` and `select_top_k_farthest(normalize=True)` (VAMOS 1.3) | A diverse subset of an unbounded archive as the result, as jMetal's BestSolutionsArchive; the studio selects it itself so that the Monitor can preview it during the run, with VAMOS's selections | upstreamed; the studio keeps the preview | #320, #323 |
| `vamos_bridge.weight_population`, `weight_file` | MOEA/D's populations and weight vectors (VAMOS 1.3) | What New run says about MOEA/D's population: VAMOS's own rule (`largest_weighted_population`), and which of jMetal's files it reads | upstreamed; the studio only describes it | #321 |

Deleted with VAMOS 1.4: the studio's own grammars (`spaces/*_real.yaml`, `spaces/*_binary.yaml`),
SMS-EMOA's own configuration builder, the conversion of the mutation probability factor,
`worker.problem_to_solve` (problems with other arguments are given by id again, `problem_kwargs`,
#286), and the normalization of the farthest-point selection.
