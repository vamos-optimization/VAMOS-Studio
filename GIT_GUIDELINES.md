# Git and Commit Guidelines

This project follows the [Conventional Commits](https://www.conventionalcommits.org/) specification.

## Message format

```
<type>[(scope)][!]: <short imperative description>

[optional body]

[optional footer(s)]
```

- Subject line: imperative mood ("add", not "added"/"adds"), no trailing period, ≤ 72 characters.
- `scope` is optional and names the affected area, e.g. `backend`, `explore`, `solve`, `ui`, `docs`.
- `!` after the type/scope marks a breaking change (see below).
- Identifiers and messages must be in **English**, per [CODING_GUIDELINES.md](CODING_GUIDELINES.md).

## Allowed types

| Type       | When to use                                                         |
| ---------- | ------------------------------------------------------------------- |
| `feat`     | A new feature, page, or user-visible capability                     |
| `fix`      | A bug fix                                                           |
| `perf`     | A change that improves performance without changing behavior        |
| `test`     | Adding or correcting tests (no production code)                     |
| `refactor` | Code change that is neither a fix nor a new feature                 |
| `style`    | Formatting only (whitespace, `black`/`ruff` fixes); no logic change |
| `docs`     | Documentation only (`README.md`, `AGENTS.md`, docstrings, etc.)     |
| `build`    | Packaging or dependency changes (`pyproject.toml`, `setup.cfg`)     |
| `ci`       | Changes to CI configuration (`.github/workflows/*.yml`)             |
| `chore`    | Tooling, `.gitignore`, and other changes that don't fit above       |
| `revert`   | Reverts a previous commit                                           |

## Breaking changes

Mark commits that change or remove something users rely on (e.g. the run-directory format) with `!`:

```
feat(solve)!: store the live front as CSV instead of NumPy
```

Explain the impact and migration in the body/footer:

```
BREAKING CHANGE: runs launched with earlier versions no longer show their
live front.
```

## Body and footers

- Add a body when the *why* isn't obvious from the subject line alone (wrap at ~72 chars).
- Reference issues with a footer, e.g. `Closes #187`, `Refs #42`.
- Trailers such as `Co-Authored-By:` are allowed and go last.

## Atomic commits

Each commit must represent **one single logical change**. Guidelines:

- If the commit message needs "and" to describe what it does, split it into two commits.
- Before committing, run the checks relevant to the change:
  - `make test` (or `pytest tests/ -x`) — tests pass
  - `make lint` — `ruff` is clean
- Never mix production code changes with test changes in the same commit.
- Never mix code changes with documentation changes in the same commit.

## Branches and releases

VAMOS-Studio has its own version numbers (`MAJOR.MINOR.PATCH`), independent of VAMOS's:

- **`develop`** is where the work happens, as atomic commits. Its version is the upcoming release
  with a `.dev0` suffix (`pyproject.toml`: `0.1.0.dev0`), and the top section of
  [CHANGELOG.md](CHANGELOG.md) is that release, marked `(unreleased)`. Every user-visible change
  adds an entry to it, in the same commit as its documentation.
- **`main`** holds the releases only, and moves only when a release is cut.
- **A release** is a `chore(release): prepare release X.Y.Z` commit on `develop` (the version in
  `pyproject.toml`, the changelog section dated, the VAMOS series it works with in the README),
  then the annotated tag `vX.Y.Z` and `main` fast-forwarded to it. Right after, a
  `chore: start X.Y+1.0.dev0 development` commit on `develop` opens the next version.
- The studio follows **released VAMOS versions** (the pinned series in `pyproject.toml`). Moving to
  a new VAMOS minor series is its own `build:` commit, with the drift-detection tests passing.

Prefer squash-merging pull requests into `develop`, so it keeps one Conventional Commit per
logical change.

## Examples

```bash
# Good
git commit -m "feat(explore): list the parameters of each algorithm"
git commit -m "fix(solve): keep the live front when the worker restarts"
git commit -m "test(backend): cover cancelling a run through the stop file"
git commit -m "docs: describe the run directory in the README"
git commit -m "ci: run tests on Python 3.11 and 3.12"

# Bad — too broad, mixes concerns
git commit -m "add stuff and fix tests and update readme"

# Bad — no type, not English
git commit -m "cambios"
```
