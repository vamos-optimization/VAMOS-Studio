# Resources copied from jMetal

The files in `referenceFronts/` are copied, unchanged, from the `resources/referenceFronts/`
directory of [jMetal](https://github.com/jMetal/jMetal) at tag `v7.11`, and are distributed under
jMetal's MIT license, kept beside them as `LICENSE-jMetal.txt`. They are the same files Evolver and
Evolver-Studio use, so the studio's indicator values match theirs.

| File | Contents |
|---|---|
| `referenceFronts/ZDT1.csv` … `ZDT6.csv` | Reference fronts of the real-coded ZDT problems (ZDT5, binary, has none) |

The studio reads them instead of the reference fronts shipped with VAMOS 1.1, whose ZDT samples
are inaccurate: up to 0.0146 off the true front for ZDT4, whose bounds are wrong too, which shifts
every normalized indicator (see `UPSTREAM.md`).

The copy is made by `make sync-resources` (`scripts/sync_resources.py`), which downloads the files
listed in `COPIED_FILES` (`vamos_studio/backend/bundled_resources.py`) at the jMetal release set by
`JMETAL_VERSION`, and records their checksums in `SHA256SUMS`. `tests/test_resources.py` fails if a
file is missing, added or changed with respect to `SHA256SUMS`.
