# C14 — Benchmark

## Responsibility

Produce reproducible, honest numbers on real tool definitions, and serve as the main correctness corpus (review R15).

## Layout

```
bench/
  servers.toml          # [[server]] name, command, source (npm/pypi), notes
  collect.py            # dev script: run each server via toolslim's MCP loader → snapshots/<name>.json
  make_pydantic.py      # generates a FastMCP/Pydantic-style snapshot from real Pydantic models
  snapshots/*.json      # committed tools/list results (inputs to everything else)
  run.py                # slim each snapshot with SAFE rules; measure under each available tokenizer
  RESULTS.md            # generated table + methodology + date + toolslim version
  results.json          # machine-readable version
```

## Method

- **Rules:** default (`--level safe`). A second table covers `--level annotations`.
- **Tokenizers:** `heuristic`, and `tiktoken:o200k_base` / `tiktoken:cl100k_base` when available. `anthropic:<model>` is added when `ANTHROPIC_API_KEY` is set (ground truth for Claude).
- **Per snapshot:** tool count, before, after, saved, saved %, top rule.
- **Totals:** across all snapshots, plus the median saved %.
- **Heuristic calibration:** mean absolute % error of the heuristic vs o200k across snapshots, published.
- **Reproducibility:** `RESULTS.md` records the date, toolslim version, tokenizer versions and the exact command.

## Candidate servers

All installable from npm/PyPI, no credentials needed for `tools/list`:
- `@modelcontextprotocol/server-filesystem`
- `@modelcontextprotocol/server-memory`
- `@modelcontextprotocol/server-everything`
- `@modelcontextprotocol/server-sequential-thinking`
- `mcp-server-git`
- `mcp-server-fetch`
- `mcp-server-time`
- a few popular FastMCP-based servers from PyPI, chosen by what installs cleanly

## Tests (`tests/test_bench.py`)

For every snapshot:
1. round-trip `serialize(parse(x)) == x`
2. slim with default rules
3. bidirectional equivalence on every changed tool → no counterexample (SKIPPED allowed, but listed)
4. inputs unchanged
5. idempotence: slimming twice equals slimming once

## Review

| Issue | Change |
|---|---|
| Hand-picking servers that happen to have lots of bloat would inflate the headline number. | Include the official reference servers, which are lean TypeScript/zod. Report the median, not only the best case. |
| Snapshots go stale as servers change. | Each snapshot records the package and version it came from (in `servers.toml` + a `_toolslim_source` note in RESULTS.md, not inside the snapshot, so round-trip stays exact). |
| Idempotence wasn't specified anywhere. | Added: `slim(slim(x)) == slim(x)`. It catches non-converging rules. |
