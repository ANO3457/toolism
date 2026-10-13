# C6 — Rule catalogue (v0.1)

Shared helper: `norm(s) = re.sub(r"[^0-9a-z]", "", s.lower())`.

**Every rule:**
- returns the input object unchanged (same identity) when it has nothing to do
- never touches opaque tools
- is tested with fixtures **and** bidirectional equivalence

## SL001 `redundant-title` — SAFE, on

Drops a string `title` when it carries no information:

- **Property schema** (`path` ends in `properties/<name>`): `norm(title) == norm(name)` — e.g. Pydantic's `"User Id"` for `user_id`.
- **`$defs` / `definitions` entry:** `norm(title) == norm(def_key)`.
- **Root schema:** `norm(title)` equals `norm(tool.name)`, optionally followed by one of `arguments, args, input, inputs, params, parameters, request, schema`. This is FastMCP's `search_eventsArguments`.

Informative titles (`"Shipping address"` on property `addr`) are kept.

## SL002 `nullable-anyof` — SAFE, on

At a node with `anyOf` **or** `oneOf` (not both), and no `type` of its own, where every branch is exactly `{"type": T}` (T a string or list of strings):

- Replace the keyword with `"type": [T…]`, deduplicated in order, at the same key position. A single type stays a string.
- `oneOf` only when the branch types are pairwise disjoint. `integer` overlaps `number`; duplicates overlap.

Example: `{"anyOf":[{"type":"string"},{"type":"null"}],"default":null}` → `{"type":["string","null"],"default":null}`

## SL003 `null-default` — SAFE, on

At an object node with `properties`: for each property **not** in `required` whose schema has `"default": null`, drop `default`.

Skipped for strict tools, where every property is required anyway. `default` is an annotation, so validation is unchanged.

## SL004 `inline-defs` — SAFE, on

Operates on the root schema only.

**Skip the tool** if `uses_dynamic_scope`, or if the root has `$id` and any non-fragment `$ref` exists.

**Delete** a root `$defs` / `definitions` entry with zero exact refs that isn't pinned. Remove the container if it becomes empty.

**Inline** a def when all of these hold:
- exactly 1 exact ref, not pinned, not recursive
- the def value is an object
- no foreign refs anywhere in the schema
- the ref node's siblings are allowed: none under draft ≤ 7; under 2019-09+ only annotation keywords may collide (`title, description, default, examples, deprecated, readOnly, writeOnly, $comment`), and the site's value wins
- any other key collision → skip

**Merge order:** the def's keys are placed where `$ref` was; siblings keep their positions.

Repeat until there's nothing left to inline or delete.

## SL005 `description-whitespace` — SAFE, on

For the tool description and every schema-node `description`:
1. Drop leading and trailing blank lines.
2. Remove the first line's leading spaces.
3. Dedent the remaining lines by their common indentation (docstring style, tabs untouched).
4. Strip trailing whitespace on each line.
5. Collapse internal runs of 2+ spaces to one, but keep leading indentation (nested lists).
6. Collapse 3+ newlines to 2.

Only whitespace ever changes.

## SL006 `echo-description` — SAFE, on

At a property schema with a string `description`, drop it when:

`content_words(description) == content_words(property name)` (as sets, both non-empty)

- **Words:** split snake/kebab/camel case and digits, lowercase.
- **Stop-words removed:** `a, an, the, of, for, to, this, that, is, value, field, param, parameter, argument, arg, property, given, specified, input`.

Examples:
- `user_id` + "The user ID." → dropped
- `max_results` + "Maximum number of results" → kept (different words)

## SL007 `stable-order` — SAFE, **off**, `reorders=True`

Stable-sort tools by `name`. Saves 0 tokens. Use it when an agent assembles tools in a non-deterministic order, which breaks prompt caching.

## SL008 `noop-keywords` — SAFE, on

At every schema node:
- drop `required: []` (not on strict tools)
- drop `description: ""`
- drop empty `$defs` / `definitions`
- drop `additionalProperties: true`, `additionalItems: true`, `items: {}` / `items: true` (not on strict tools)
- `type: ["x"]` → `"x"`

**Never drops `properties: {}`** — providers require it on object roots.

## SL009 `schema-uri` — SAFE, on

Drops the root `$schema` (draft-06, draft-07, 2019-09 or 2020-12) when the schema has no dialect-sensitive constructs:
- a `$ref` with siblings
- array-form `items`
- `additionalItems`
- `dependencies`
- boolean `exclusiveMinimum` / `exclusiveMaximum`
- draft-04 `id`
- `$recursiveRef` / `$recursiveAnchor`

Under the default dialect (2020-12) the schema then validates identically. Draft-04 is never touched.

## SL101 `max-description-length` — LOSSY_ANNOTATIONS, off

Options: `max_chars: int = 300`, `include_tool: bool = False`.

Truncates schema-node descriptions (and the tool description if `include_tool`):
- at the last sentence end (`. ! ?` + space, or a newline) before `max_chars`
- otherwise at the last space, plus `…`

## SL102 `drop-examples` — LOSSY_ANNOTATIONS, off

Removes `examples` (JSON Schema) and `example` (OpenAPI) from schema nodes.

## Tests (per rule)

- `tests/fixtures/rules/SLxxx.json`: list of `{name, tool, expected_schema?, expected_description?, options?, strict?, dialect?}`.
- The shared runner applies only that rule, compares, asserts the input is unchanged, and — for every case with a schema change — runs bidirectional equivalence.

## Review

| Issue | Change |
|---|---|
| SL002 first draft turned `anyOf[X, null]` into `X`. That rejects explicit `null`, which is a validation change. | Uses the `type: [X, "null"]` form, which is exactly equivalent. |
| SL002 on `oneOf` with overlapping types (`integer` + `number`) is not equivalent. | Disjointness check added. |
| SL004 inlining under draft-07 with `$ref` siblings activates keywords that validators used to ignore. | Disallowed (review R2). |
| SL008 dropping `properties: {}` breaks OpenAI no-argument functions. | Explicitly never dropped. |
| SL005 originally used `inspect.cleandoc`, which expands tabs and so changes content inside lines. | Custom dedent that never touches tabs. |
| `$schema` URIs cost ~10–15 tokens per tool on zod- and FastMCP-generated servers but were in no rule. | New SL009 with a dialect-invariance guard. |
| SL006 could drop descriptions that add meaning through word order ("ID of the user that created it"). | Exact set equality after stop-words, so any extra word keeps the description. Conservative by construction. |
