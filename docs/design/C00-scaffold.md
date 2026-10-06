# C0 — Scaffold & tooling

## Responsibility

Packaging, developer tooling and the quality gates every later component must pass.

## Interface

- `pyproject.toml`
  - hatchling backend; `src/toolslim`; version in `src/toolslim/__about__.py` (hatch dynamic version)
  - `[project.scripts] toolslim = "toolslim.cli:main"`
- Dependencies:
  - core: `typer>=0.12`, `tiktoken>=0.7`
  - extras: `verify` (`hypothesis>=6.100`, `hypothesis-jsonschema>=0.23`, `jsonschema>=4.21`), `mcp` (`mcp>=1.2`), `anthropic` (`anthropic>=0.40`), `all`
- `[dependency-groups] dev`: pytest, pytest-cov, ruff, mypy, pydantic (benchmark only), plus all extras.
- Tool config:
  - ruff: line length 100; rules E, F, W, I, B, UP, SIM, RUF, PL subset
  - mypy `strict = true` on `src/`
  - pytest: `-ra --strict-markers`; markers `network`, `mcp`, `slow`
  - coverage: `fail_under = 90` on `src/`
- Files: `LICENSE` (MIT), `.gitignore`, `.editorconfig`, `src/toolslim/py.typed`.

## Behaviour & edge cases

- Python ≥ 3.10. Use `from __future__ import annotations`, and no `match` statements that would trip older tooling.
- Nothing runs on import except module-level constants. Importing `toolslim` must not import `tiktoken`, `hypothesis` or `mcp` (lazy imports keep startup fast).

## Tests

- `tests/test_layering.py` — AST-parses every module under `src/toolslim` and checks each internal import against the allowed layer table from ARCHITECTURE §4.
- `tests/test_import_cost.py` — runs `import toolslim` in a subprocess and asserts `tiktoken`, `hypothesis` and `mcp` aren't in `sys.modules`.

## Review

| Issue | Change |
|---|---|
| Putting `typer` in core makes the library heavier for people who only embed `slim_tools()`. | Accepted trade-off: `typer` is small, and `pip install toolslim && toolslim …` must just work. The lazy-import test still guarantees no CLI import cost for library users. |
| `tiktoken` in core means a compiled wheel. Some platforms lack wheels. | tiktoken has wheels for all CPython 3.10–3.13 on Linux, macOS and Windows (x86-64 + arm64). Documented; the heuristic tokenizer works without it at runtime because the import is lazy. |
| A coverage gate at 90% could encourage pointless tests. | Kept, but the extras-dependent modules (`verify`, `loaders/mcp`, the Anthropic tokenizer) are covered by tests that run in CI where the extras are installed. |
