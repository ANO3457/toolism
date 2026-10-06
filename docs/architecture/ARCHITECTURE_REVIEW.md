# Architecture review — toolslim v0.1

Reviewed document: [ARCHITECTURE.md](ARCHITECTURE.md) (commit `17b050b`).

**Lens:** what can make toolslim ship a schema that rejects a valid tool call, report a number that isn't true, or be painful to contribute to?

**Verdict:** approve with changes. Every High and Medium finding below is applied to ARCHITECTURE.md (section 14) and to the component designs.

## Findings

| # | Sev | Finding | Decision | Applied in |
|---|---|---|---|---|
| R1 | High | Most rules key off JSON Schema keywords (`title`, `description`, `default`). A property *named* `title` lives inside `properties`, and instance data lives inside `enum` / `const` / `default` / `examples`. A naive recursive walk would delete a property called `title`, or rewrite an enum value. | The walker is **keyword-table driven**. It recurses only into known subschema positions (single schema, schema array, schema map). It never enters instance-valued or unknown keywords. Fixtures with properties named `title`, `description`, `default`, `type` and `$ref` are mandatory. | C3 design, walker tests |
| R2 | High | `$ref` semantics depend on the dialect. In draft-04/06/07, keywords next to `$ref` are **ignored**; in 2019-09/2020-12 they **apply**. Inlining a `$ref` that has siblings changes validation under draft ≤ 7. `$id`, `$anchor` and `$dynamicRef` change how refs resolve. | `schema/dialect.py` detects the dialect from `$schema` (default 2020-12). SL004 skips `$ref` nodes with siblings under draft ≤ 7, and skips any tool that uses `$id`, `$anchor`, `$dynamicRef` or `$recursiveRef`. The verifier validates with the same dialect. | C3, SL004, C8 |
| R3 | High | OpenAI `strict: true` tools need every property in `required` and `additionalProperties: false`, and only allow a keyword subset. A "safe" rule that drops `required: []` or adds a keyword could make the tool unusable. | `RuleContext.strict` is true for tools with `strict: true`. Rules that touch `required` or `additionalProperties` are no-ops on strict tools. A test helper `assert_strict_shape()` runs on every strict fixture after slimming. | C5, SL008, tests |
| R4 | Medium | Rules depend on each other's output: inlining a `$def` can expose a now-redundant `title`. A single ordered pass under-slims and depends on run order. | Fixpoint passes (max 3) in ID order; stop when nothing changed. If the cap is hit while rules are still changing things, log a warning and report it. Attribution accumulates across passes. | C7 |
| R5 | Medium | Token counts on our JSON rendering may not equal what a provider bills. A provider might drop `title` itself, which would make "savings" partly illusory. | Every report and baseline names its tokenizer and says if it's approximate. The benchmark always includes a ground-truth column (`anthropic:<model>`) when an API key is available. The README only claims measured numbers, per tokenizer. | C9, C14, C15 |
| R6 | Medium | The default tokenizer (`tiktoken:o200k_base`) downloads its vocabulary on first use, so offline or air-gapped CI fails. Silently falling back to the heuristic would change numbers without anyone noticing and break baselines. | No silent fallback. Exit code 3 with an actionable message. `TOOLSLIM_TOKENIZER` env var sets the default. `check` refuses to compare against a baseline made with a different tokenizer unless `--allow-tokenizer-change` is given. | C4, C10, C11 |
| R7 | Medium | Property-based verification is slow on large tool sets (two directions × examples × tools). | Verify only tools a rule changed; `max_examples` defaults to 50 (`--verify-examples`); `derandomize=True` so CI is reproducible. A schema Hypothesis can't generate for is reported as **skipped**, never as passed. | C8 |
| R8 | Medium | On a counterexample, what do we roll back? | Roll back the **whole tool** to its original and list the rules that touched it. `--fail-on-rollback` turns this into exit 1 for CI. Finer-grained bisection is future work. | C7, C11 |
| R9 | Low | Frozen dataclasses with `dict` fields aren't deeply immutable, so a rule can still mutate shared state. | Rules receive deep copies. `ToolDef.fingerprint()` (SHA-256 of canonical JSON) lets tests assert inputs are unchanged. The pipeline compares fingerprints, not identity. | C1, C7 |
| R10 | Low | Write-back fidelity: key order, unknown tool-level keys, envelope fields (`nextCursor`, wrapper objects). | `ToolDef.extras` keeps unknown keys in order. `ToolSet.envelope` keeps the container. Serialization restores the original key order of known keys. Round-trip test: `serialize(parse(x)) == x` for every fixture and snapshot. | C2 |
| R11 | Low | The layering rule is only a convention. | An AST test checks every `src/toolslim` import against the allowed-layer table. No extra dependency. | C0 tests |
| R12 | Low | Performance on huge tool sets (Cloudflare-scale, 2,500+ tools). | Re-count only tools a rule changed; cache counts by fingerprint. Target: 1,000 tools, all SAFE rules, heuristic tokenizer, in under 2 s. | C7, C4 |
| R13 | Low | Unknown and vendor keywords (`x-*`, OpenAPI's `nullable`, `discriminator`) could be mishandled. | The walker doesn't recurse into them, and no rule rewrites them. | C3 |
| R14 | Low | MCP tools have a display `title` and `outputSchema` that clients generally don't send to the model. | They're kept in `extras`, preserved on write-back and not counted. Documented in the report notes. | C2, C9 |
| R15 | Process | Fixture tests alone are hand-picked examples. | CI runs bidirectional equivalence for **all default rules on every benchmark snapshot**. That's the main evidence behind the "safe" claim. | C14, tests |

## Things I considered and rejected

- **Pydantic for models** — rejected. Embedding toolslim in agents should cost almost nothing, and frozen dataclasses are enough.
- **Plugin entry points for third-party rules** — deferred. The in-repo registry keeps v0.1 simple, and entry points can be added without breaking anything.
- **Sorting keys inside schemas for cache stability** — rejected. Property order can steer argument generation. SL007 only sorts *tools*, and it's off by default.
- **LLM-assisted description rewriting** — out of scope by design (non-goal: no model calls in the slimming path).
