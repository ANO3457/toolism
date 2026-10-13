# C8 — Equivalence verification

## Responsibility

Give evidence — not proof — that two schemas accept the same instances. Used by `slim --verify` at runtime, and by the test suite on every fixture and benchmark snapshot.

## Interface

```python
class Verdict(str, Enum): EQUIVALENT = "equivalent"; COUNTEREXAMPLE = "counterexample"; SKIPPED = "skipped"

@dataclass(frozen=True)
class VerificationResult:
    tool: str
    verdict: Verdict
    direction: str | None   # "original→slim" | "slim→original"
    example: Any = None     # the instance that broke equivalence
    reason: str = ""        # for SKIPPED

def check_equivalence(original: Any, slim: Any, *, tool: str = "", max_examples: int = 50) -> VerificationResult
def verify_available() -> bool
```

## Behaviour

1. `None` schemas are treated as `{}` (accept anything).
2. Identical schemas (canonical JSON) → EQUIVALENT immediately.
3. For each direction `(src, dst)`:
   1. Build `strategy = hypothesis_jsonschema.from_schema(prepare(src))`. `prepare` drops `$schema` for generation only, since hypothesis-jsonschema supports drafts 4/6/7 keywords.
   2. Validate with `jsonschema.validators.validator_for(schema, default=Draft202012Validator)`. Each side uses its own declared dialect, which is exactly what SL009 must survive.
   3. Run a Hypothesis test with `settings(max_examples, derandomize=True, database=None, deadline=None, suppress_health_check=all)`. The body is: if `src_validator` rejects `x` → ignore (generator imprecision); if `dst_validator` rejects `x` → raise `_Counterexample(x)`.
   4. Hypothesis shrinks and re-raises → COUNTEREXAMPLE with the minimal example.
4. **Generation can't run** → SKIPPED with the message. This covers unsupported keywords, unresolvable refs, `Unsatisfiable`, or an `InvalidArgument` from the strategy.
5. **Missing extra** → `MissingExtraError("pip install 'toolslim[verify]'")`.

## Limits (documented, not hidden)

- Sampling can miss rare counterexamples. Rules are designed equivalent by construction; verification is a safety net plus regression detection.
- `format` is an annotation under the default validators (not asserted), consistent with providers.
- Recursive schemas: hypothesis-jsonschema may not generate for them, so they're SKIPPED (honest).

## Tests

- Equivalent pairs (title removed, type-array rewrite) → EQUIVALENT.
- Non-equivalent pair (`required` dropped; `anyOf[X,null]` → `X`) → COUNTEREXAMPLE, with a minimal example that is actually rejected.
- Unsupported schema → SKIPPED with a reason.
- Deterministic: two runs give the same result and example.
- Missing extra → `MissingExtraError`. The test simulates the missing import via `monkeypatch` of `sys.modules`.

## Review

| Issue | Change |
|---|---|
| hypothesis-jsonschema's `from_schema` can raise at strategy-build time *or* lazily during draw. | Both are caught and mapped to SKIPPED. |
| Generated instances that the source validator rejects (a generator bug) would count as counterexamples if we only checked `dst`. | Check `src` first and ignore those samples. |
| Hypothesis prints falsifying examples to stdout, which would pollute CLI output. | Run with `verbosity=quiet` and capture the example from our own exception. |
| Running Hypothesis inside a library is unusual. Its example database writes files. | `database=None` — no files are written. |
