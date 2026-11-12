# Python Coding and Testing Guidelines (Python 3.11+)

All source code, identifiers, and comments **must be written in English**.

## 1. General Rules

- Target version: **Python 3.11+**
- Build backend: **setuptools**
- Code and comments: **English only**
- One responsibility per function, one module per concept

## 2. Typing and Structure

- Use `|` for unions, `TypeAlias`, `Literal`, `Final`, `TypedDict`, and `Self`
- Annotate parameters, return types, and key variables on new/modified code
- Use `@dataclass(slots=True, frozen=True)` for stateless, immutable data — config
  objects, requests, catalogue entries, parameter bundles
- Prefer `Enum` for discrete choices
- Public functions should be typed on new/modified code. This is a style
  convention, not tool-enforced — the project doesn't run a static type
  checker (see [Enforcement](#enforcement))
- Cognitive complexity ≤ 10 (enforced by ruff on new/modified code)

## 3. Function Rules

- One `return` per function (except parameter validation guards)
- Guard clauses only for invalid inputs
- Keep functions ≤ 20 lines when possible
- Avoid nested conditionals (“pyramid of ifs”)

## 4. Error and Resource Handling

- Always use context managers (`with`)
- Raise specific exceptions (`ValueError`, `TypeError`, etc.) for invalid input
  and unrecoverable errors; pages turn them into messages for the user
- Avoid global exception handling except at the entry point

## 5. Style, Tooling, and Documentation

- **ruff**: linting, formatting, import order, and complexity — the blocking gate
  (`make lint`, `make format`).
- No static type checker (mypy) is enforced; running it locally is fine.
- Use **Google-style docstrings** with Args / Returns / Raises
- Clarity over cleverness — no "smart" one-liners

## 6. Unit Testing

- Framework: **pytest**
- Follow **AAA pattern** (Arrange–Act–Assert)
- Name tests `test_should_<behavior>` (e.g. `test_should_raise_error_on_negative_probability`);
  put given/when/then detail in a one-line docstring, not in the function name.
  `given_when_then`-style names are a Java/BDD import, not idiomatic pytest, and are not
  required — this is descriptive, not enforced by tooling
- Group related scenarios under `class Test<Subject>:` rather than flat module-level functions
- Prefer `@pytest.mark.parametrize` over hand-written near-duplicate tests for scenario variants
- Each test should focus on a single behavior
- Use fixtures for setup
- Always include both success and failure paths
- Exception checks use `pytest.raises`
- Use plain `assert` (pytest rewrites it for rich failure diffs); no matcher library

## 7. AI-Aware Design

- Always include type hints and docstrings
- Keep functions pure and self-contained
- Prefer descriptive variable names
- Provide minimal working examples and tests

---

## Enforcement

- **ruff** (style, imports, complexity) — `make lint`, blocking
- **pytest** (tests) — `make test`, blocking
