# Resources copied from jMetal

The files in `referenceFronts/` are copied, unchanged, from the `resources/referenceFronts/`
directory of [jMetal](https://github.com/jMetal/jMetal) at tag `v7.11`, and are distributed under
jMetal's MIT license, kept beside them as `LICENSE-jMetal.txt`. They are the same files Evolver and
Evolver-Studio use, so the studio's indicator values match theirs.

| File | Contents |
|---|---|
| `referenceFronts/ZDT1.csv` … `ZDT6.csv` | Reference fronts of the real-coded ZDT problems (ZDT5, binary, has none) |
| `referenceFronts/DTLZ1.2D.csv` … `DTLZ7.3D.csv` | Reference fronts of DTLZ1–7 with two and three objectives |
| `referenceFronts/DTLZ1.4D.csv` … `DTLZ7.8D.csv` | Reference fronts of DTLZ1–4 and DTLZ7 with four, six and eight objectives (jMetal has none of DTLZ5 and DTLZ6 beyond three) |

The studio reads them instead of the reference fronts shipped with VAMOS 1.1, whose samples are
inaccurate: up to 0.0146 off the true front for ZDT4 and 0.052 for DTLZ4 (three objectives), with
wrong bounds for ZDT4, DTLZ6 and DTLZ7, which shifts every normalized indicator; VAMOS 1.1 has no
two-objective DTLZ fronts at all (see `UPSTREAM.md`).

The copy is made by `make sync-resources` (`scripts/sync_resources.py`), which downloads the files
listed in `COPIED_FILES` (`vamos_studio/backend/bundled_resources.py`) at the jMetal release set by
`JMETAL_VERSION`, and records their checksums in `SHA256SUMS`. `tests/test_resources.py` fails if a
file is missing, added or changed with respect to `SHA256SUMS`.
