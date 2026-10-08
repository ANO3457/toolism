# C10 — Baseline check

## Responsibility

Stop tool-definition token cost from silently growing. Used in CI.

## Interface

```python
@dataclass(frozen=True)
class Baseline:
    tokenizer: str; total: int; tools: dict[str, int]; toolslim_version: str; version: int = 1

def load_baseline(path) -> Baseline            # BaselineError on missing / bad / unknown version
def save_baseline(path, report: TokenReport) -> Baseline
def baseline_from_report(report: TokenReport) -> Baseline

@dataclass(frozen=True)
class Budget:
    max_increase_pct: float | None = None   # "10%"
    max_increase_abs: int | None = None     # "500"
    max_total: int | None = None
    max_tool: int | None = None
def parse_increase(text: str) -> tuple[float | None, int | None]

@dataclass(frozen=True)
class ToolDelta: name: str; before: int | None; after: int | None   # None = added / removed

@dataclass(frozen=True)
class CheckResult:
    ok: bool; violations: tuple[str, ...]; current: TokenReport; baseline: Baseline | None
    delta_total: int | None; deltas: tuple[ToolDelta, ...]

def run_check(report, baseline: Baseline | None, budget: Budget, *, allow_tokenizer_change=False) -> CheckResult
def render_check(result, fmt: Literal["table", "markdown", "json"]) -> str
```

## Behaviour

- **Tokenizer mismatch** (`baseline.tokenizer != report.tokenizer`) → `BaselineError`, unless `allow_tokenizer_change`. In that case deltas are shown but no increase budget is enforced; a violation-free note is added.
- **Violations** (all are collected, not first-fail):
  - total increase > pct of baseline total
  - total increase > absolute
  - total > `max_total`
  - any tool > `max_tool`
- `max_total` / `max_tool` work without a baseline.
- **Deltas** list added, removed and changed tools, sorted by absolute change.
- **Baseline file:** pretty JSON, keys sorted. Tool names are the keys; with duplicate names, counts are summed with a warning.

## Tests

- Each budget type passes and fails at the boundary (equal = pass).
- Combined violations; tokenizer mismatch both ways.
- Save → load round trip; unknown version → error; markdown golden output; added/removed tools.

## Review

| Issue | Change |
|---|---|
| Is a percentage increase on a tiny baseline (e.g. 40 tokens) too noisy? | Users can combine `--max-increase 10%` with an absolute floor; the docs recommend both for small servers. |
| Should the check slim before measuring? | No. It measures what you ship, so the gate is honest. Users who ship slimmed tools run the check on the slimmed output. |
| A shrinking total could be misreported as a failure by a sign error. | Explicit tests that decreases always pass. |
