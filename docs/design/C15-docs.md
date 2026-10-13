# C15 — Documentation

## Deliverables

**`README.md`:**
- the problem in 3 lines
- install
- 30-second CLI quickstart with real output
- Python API
- how it works (rules table)
- safety levels and verification
- CI / GitHub Action
- benchmark headline + link
- how it differs (vs mcp-context-budget, Headroom, LLMLingua, LiteLLM)
- FAQ: does prompt caching make this pointless? is tiktoken accurate for Claude?
- contributing
- license

**`CONTRIBUTING.md`:**
- dev setup with `uv`
- running tests, lint and types
- **adding a rule in 3 steps** (module, fixture file, `docs/rules.md` regen)
- commit style (Conventional Commits)
- release process including the trusted-publisher setup

**Also:**
- `docs/rules.md` — generated from the registry by `scripts/gen_rules_doc.py`; a test fails if it's stale.
- `CHANGELOG.md` (Keep a Changelog), `SECURITY.md`
- `.github/ISSUE_TEMPLATE/{bug_report,new_rule}.yml`, `.github/pull_request_template.md`
- `examples/`: `openai_tools.json`, `anthropic_tools.json`, `mcp_tools.json`, `agent_startup.py` (embedding `slim_tools`)

## Review

| Issue | Change |
|---|---|
| A hand-maintained rules doc goes stale the first time a contributor adds a rule. | Generated, with a staleness test. |
| README claims must match measured numbers. | The README's numbers are copied from `bench/RESULTS.md` with its date. No unmeasured percentages anywhere. |
| "Good first issues" belong on GitHub, not in the repo. | Listed in CONTRIBUTING as a seed list. The maintainer opens them as issues after the first push. |
