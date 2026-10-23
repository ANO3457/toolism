# C13 — GitHub Action, CI & release

## GitHub Action (`action.yml`, composite)

```yaml
inputs:
  source:            # path to a tools JSON file (or use `mcp`)
  mcp:               # command to launch an MCP server
  baseline:          # required, e.g. .toolslim/baseline.json
  max-increase:      # e.g. "10%" or "500"
  max-total:
  max-tool:
  tokenizer:         # default tiktoken:o200k_base
  python-version:    # default "3.12"
  update-baseline:   # "false"
outputs:
  total, delta, status   # status = pass | fail
```

**Steps:**
1. `actions/setup-python@v5`.
2. `pip install "$GITHUB_ACTION_PATH[mcp]"`. Installs exactly the code at the action ref, so `@v0.1.0` = toolslim 0.1.0.
3. `toolslim check … --summary-md "$RUNNER_TEMP/toolslim.md" -f json > "$RUNNER_TEMP/toolslim.json"`.
4. Parse outputs with Python (no `jq` dependency).
5. Exit with the check's status.

**PR comments:** the README documents a 6-line `marocchino/sticky-pull-request-comment` snippet reading `$RUNNER_TEMP/toolslim.md`. That way no write token is needed by our action.

## CI (`.github/workflows/ci.yml`)

| Job | What |
|---|---|
| lint | `ruff check`, `ruff format --check` |
| types | `mypy` strict on `src` |
| test | matrix Python 3.10–3.13 on ubuntu, plus 3.12 on macOS and Windows; `uv sync --all-extras`; `pytest --cov` (fail under 90) |
| bench-equivalence | `pytest -m "not network" tests/test_bench.py` — all default rules, bidirectional, on every snapshot |
| dogfood | runs **our own action** (`uses: ./`) on `bench/snapshots/fastmcp-pydantic.json` against `.toolslim/baseline.json` |

## Release (`.github/workflows/release.yml`)

On tag `v*`:
1. `uv build`.
2. Check the version in `__about__.py` equals the tag.
3. `pypa/gh-action-pypi-publish` with `id-token: write`, in environment `pypi` (trusted publishing — no API token stored).
4. GitHub Release with notes from `CHANGELOG.md`.

**One-time manual step for the maintainer** (documented in CONTRIBUTING): add a trusted publisher on pypi.org — owner `rakeshnitb23`, repo `toolism`, workflow `release.yml`, environment `pypi`.

## Review

| Issue | Change |
|---|---|
| Installing from PyPI inside the action ties action and package versions loosely. | Install from `$GITHUB_ACTION_PATH`, which is exact. |
| Posting PR comments needs `pull-requests: write`. Many orgs restrict that, and fork PRs don't get it. | Not built in. The step summary always works; the comment is opt-in via a documented snippet. |
| Windows/macOS for the full matrix is slow. | One Python version on each. |
| The tiktoken vocab download in CI is a network dependency. | It's cached via `actions/cache` on `~/.cache/toolslim-tiktoken` with `TIKTOKEN_CACHE_DIR` set. |
