# C9 — Measure & reports

## Responsibility

Count a tool set, and render `TokenReport` and `SlimReport` for humans (terminal, Markdown) and machines (JSON).

## Interface

```python
@dataclass(frozen=True) class ToolCount: name: str; tokens: int
@dataclass(frozen=True) class TokenReport:
    tokenizer: str; approximate: bool; total: int; tool_count: int
    tools: tuple[ToolCount, ...]; uncounted: tuple[str, ...]
    @property average -> float

def measure(toolset: ToolSet, tokenizer: str | Tokenizer | None = None) -> TokenReport

# report.py
def token_report_to_dict(r: TokenReport) -> dict      # {"toolism_report": 1, "kind": "measure", ...}
def slim_report_to_dict(r: SlimReport) -> dict        # {"toolism_report": 1, "kind": "slim", ...}
def render_token_report(r, fmt: Literal["table","json","markdown"]) -> str
def render_slim_report(r, fmt) -> str
```

## Behaviour

**`total`.** Uses `tokenizer.count_tools(function_tools)`. For local tokenizers that's the sum of per-tool counts; for Anthropic it's the provider's set total.

**Table** — built with `rich` and rendered to a string:
- columns: Tool | Tokens | % of total; sorted descending
- footer: total, average, tokenizer, approximate note
- If more than 25 tools, show the top 25 plus "… N more".

**Slim table** — summary line `before → after (−X tokens, −Y.Y%)`, then:
- a rules table: Rule | Name | Tokens saved | Tools changed
- a top-changed-tools table: Tool | Before | After | Saved
- warnings, rollbacks, verification summary

**Markdown** has the same content as GitHub-flavoured tables (used by the Action step summary and PR comments).

**JSON:** stable keys, versioned with `"toolism_report": 1`, integers for tokens, percentages rounded to 2 decimals.

## Tests

- Golden-string tests for markdown and JSON.
- The table renders without errors at 80 and 200 columns.
- Percentages sum is sane.
- `uncounted` notes appear.
- Zero-tool report renders.

## Review

| Issue | Change |
|---|---|
| Rich auto-detects terminal width, which makes golden tests flaky. | Render through `Console(width=…, record=True, color_system=None)`. The width is passed by the CLI from the actual terminal. |
| JSON had floats for token counts in the draft (averages). | Tokens are always ints; only `average` and `*_pct` are floats. |
| `measure` lived in the pipeline in the architecture draft. | Separate `measure.py` so `check` doesn't depend on the pipeline. |
