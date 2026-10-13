# C4 — Tokenizers

## Responsibility

Count tokens of tools under a named, honest tokenizer.

## Interface

```python
class Tokenizer(Protocol):
    name: str          # "heuristic" | "tiktoken:o200k_base" | "anthropic:claude-sonnet-5"
    approximate: bool  # True unless the count comes from the provider for that provider's model
    local: bool        # False = network calls (unsuitable for per-rule attribution)
    def count_tool(self, tool: ToolDef) -> int
    def count_tools(self, tools: Sequence[ToolDef]) -> int

class TextTokenizer(ABC):          # base for local tokenizers
    def count_text(self, text: str) -> int
    # count_tool = count_text(tool.render()), cached by fingerprint (dict, bounded);
    # count_tools = sum of count_tool

class HeuristicTokenizer(TextTokenizer)      # name "heuristic", no dependencies
class TiktokenTokenizer(TextTokenizer)       # name f"tiktoken:{encoding}"; lazy import + load
class AnthropicTokenizer                     # name f"anthropic:{model}"; extra "anthropic"

def get_tokenizer(spec: str | Tokenizer | None = None) -> Tokenizer
DEFAULT_TOKENIZER = "tiktoken:o200k_base"; ENV_VAR = "TOOLSLIM_TOKENIZER"
```

## Behaviour & edge cases

**Heuristic.** A regex splits text into pieces close to GPT-style pre-tokenization:
- letter runs, 1–3 digit groups, whitespace runs, punctuation runs
- cost per piece:
  - letters: `ceil(len / 4)`, minimum 1
  - digit group: 1
  - punctuation run: `ceil(len / 2)`
  - whitespace: 0 if a single space before a word, otherwise 1
- Calibrated against `o200k_base` on the benchmark corpus; the measured error is published in `bench/RESULTS.md`. Deterministic and offline.

**Tiktoken.**
- Lazy `import tiktoken`; `tiktoken.get_encoding(enc)`.
- Any failure (missing package, vocabulary download blocked) → `TokenizerUnavailable` with a hint: `--tokenizer heuristic`, or pre-seed `TIKTOKEN_CACHE_DIR`.

**Anthropic.**
- `count_tools(T)` = `count(messages=[user "."], tools=T) − count(messages=[user "."])`. Includes the fixed tool-use preamble once.
- `count_tool(t)` = `count(tools=[t]) − count(tools=[PROBE])`, where `PROBE` is a minimal tool (`{"name":"x","input_schema":{"type":"object"}}`). This is a marginal cost that excludes the preamble.
- Results cached by fingerprint. Opaque tools are skipped.
- Needs `ANTHROPIC_API_KEY` or an injected client. Missing package or key → `TokenizerUnavailable`.
- The client is injectable for tests (`client=` with a `.messages.count_tokens` method).

**`get_tokenizer`:**
- `None` → the `TOOLSLIM_TOKENIZER` env var, otherwise the default.
- Unknown prefix → `TokenizerError` listing the valid forms.
- A tokenizer instance is passed through unchanged.

## Tests

- Heuristic: deterministic counts for fixed strings; monotonic (appending text never lowers the count); empty string = 0.
- Tiktoken: skipped if the vocabulary is unavailable; otherwise compared with `enc.encode`.
- Anthropic with a fake client: arithmetic for `count_tools` / `count_tool`, caching (call counts), opaque skipped, missing key → unavailable.
- `get_tokenizer`: env var precedence, error messages.

## Review

| Issue | Change |
|---|---|
| Summing per-tool renders ignores the per-tool framing tokens providers add, so totals are slightly low. | Accepted and documented. Totals from local tokenizers are labelled approximate. Relative savings — the thing toolslim optimizes — are unaffected because framing is constant per tool. |
| The original Anthropic `count_tool` design subtracted a no-tools baseline. That counts the ~300-token preamble against every tool and inflates per-tool numbers. | Changed to marginal cost against a minimal `PROBE` tool. |
| An unbounded cache could grow without limit in a long-running agent process. | Bounded dict (4,096 entries, FIFO eviction). |
| Should the heuristic try to imitate o200k closely? | No over-fitting. A simple, explained rule plus a published error figure is more honest. |
