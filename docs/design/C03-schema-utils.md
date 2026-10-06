# C3 — Schema utilities

## Responsibility

Correct, dialect-aware primitives for reading and rewriting JSON Schema. Every rule depends on this being exactly right (review R1, R2).

## Interface

```python
# schema/walker.py
SchemaPath = tuple[str | int, ...]   # e.g. ("properties", "user_id") or ("anyOf", 0)

def iter_subschemas(schema: Any, path: SchemaPath = ()) -> Iterator[tuple[SchemaPath, dict]]
    # pre-order over dict subschemas only (boolean schemas are skipped)

def map_subschemas(schema: Any, fn: Callable[[dict, SchemaPath], Any], path=()) -> Any
    # post-order rebuild: children first, then fn(new_node, path). Returns a NEW tree.
    # Non-schema values (enum/const/default/examples/unknown keywords) are shallow-copied untouched.

def property_name(path: SchemaPath) -> str | None   # name when path ends in ("properties", name)
def defs_name(path: SchemaPath) -> str | None       # name when path ends in ("$defs"|"definitions", name)

# schema/dialect.py
class Dialect(Enum): DRAFT4, DRAFT6, DRAFT7, DRAFT2019_09, DRAFT2020_12
def detect_dialect(schema: Any) -> Dialect           # from "$schema"; default DRAFT2020_12
def ref_siblings_apply(d: Dialect) -> bool            # True for 2019-09 and 2020-12

# schema/refs.py
@dataclass(frozen=True) class DefRef: container: str; name: str     # "$defs" | "definitions"
def parse_def_ref(ref: str) -> DefRef | None          # "#/$defs/A%20B" -> DefRef("$defs","A B"); "~1"→"/", "~0"→"~"
def iter_refs(schema) -> Iterator[tuple[SchemaPath, str]]
def def_usage(schema) -> DefUsage   # counts of exact refs per def, pinned defs (refs *into* a def),
                                    # foreign refs present?, and the def→def reference graph
def is_recursive(usage: DefUsage, name: str) -> bool  # reaches itself through the def graph
def uses_dynamic_scope(schema) -> bool                # nested $id, $anchor, $dynamicRef/$dynamicAnchor, $recursiveRef/$recursiveAnchor
```

## Keyword table (the heart of R1)

| Class | Keywords | Walk behaviour |
|---|---|---|
| Single subschema | `additionalProperties`, `items` (object form), `not`, `if`, `then`, `else`, `contains`, `propertyNames`, `unevaluatedItems`, `unevaluatedProperties`, `additionalItems`, `contentSchema` | recurse |
| Subschema array | `allOf`, `anyOf`, `oneOf`, `prefixItems`, `items` (array form, draft ≤ 2019) | recurse into each element |
| Subschema map | `properties`, `patternProperties`, `$defs`, `definitions`, `dependentSchemas` | recurse into each value |
| Mixed map | `dependencies` (draft ≤ 7: value is a schema **or** a string array) | recurse only into object/bool values |
| Everything else | `enum`, `const`, `default`, `examples`, `required`, `x-*`, unknown keywords | **never entered** |

## Behaviour & edge cases

- **Boolean schemas** (`true` / `false`) are valid subschemas: walked past, never passed to `fn`.
- **`fn` may return a non-dict** (e.g. `True`) to replace a node. The walker accepts any JSON value from `fn`.
- **`parse_def_ref` only accepts same-document pointers** of exactly two segments under `$defs` / `definitions`. Anything else is "foreign" (remote, `#/properties/…`, anchors).
- **`def_usage` "pinned" defs:** a ref like `#/$defs/A/properties/x` pins `A` (must not be inlined or deleted).

## Tests

- Property named `title` / `description` / `default` / `$ref` / `type` under `properties`: the walker visits it as a schema; the *keyword* `title` on that schema is distinct.
- Enum containing objects with `"title"` keys is never visited.
- `dependencies` with mixed values.
- Boolean schemas in `items` and `additionalProperties`.
- Draft-07 `items` array form.
- `parse_def_ref` with `~0`, `~1`, `%25` and invalid pointers.
- `def_usage` counts, pinned defs, recursion (self and mutual).
- `map_subschemas` never mutates input (fingerprint before and after).

## Review

| Issue | Change |
|---|---|
| Pre-order vs post-order: rules like SL002 rewrite a node based on its *already-rewritten* children. | `map_subschemas` is post-order. A pre-order iterator exists for read-only analysis. |
| `items` changed meaning in 2020-12 (array form became `prefixItems`). | The walker treats `items` by *shape*: dict → single subschema, list → array. Shape-based handling is dialect-safe. |
| Percent-decoding refs: is `%2F` the same as `/`? | Decode percent-escapes first, then JSON-pointer escapes, per RFC 6901 §6. Tested. |
| A root `$id` is common (some generators add one) and harmless for `#/$defs/…` refs. | `uses_dynamic_scope` ignores a root-level `$id`; nested `$id` counts. |
