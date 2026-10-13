# C1 — Models & errors

## Responsibility

Format-neutral, immutable representation of tools and tool sets, and the exception hierarchy. Bottom layer — no internal imports.

## Interface

```python
class ToolFormat(str, Enum):
    OPENAI_CHAT = "openai-chat"            # {"type":"function","function":{name,description,parameters,strict?}}
    OPENAI_RESPONSES = "openai-responses"  # {"type":"function",name,description,parameters,strict?}  (also legacy `functions=[...]`)
    ANTHROPIC = "anthropic"                # {name,description,input_schema,cache_control?,strict?}
    MCP = "mcp"                            # {name,title?,description,inputSchema,outputSchema?,annotations?}

@dataclass(frozen=True, slots=True)
class ToolDef:
    name: str
    description: str | None          # None = absent in source
    input_schema: dict[str, Any] | None  # None = absent in source
    strict: bool = False             # OpenAI/Anthropic strict tool
    opaque: bool = False             # built-in / server tool we can't rewrite (e.g. web_search); passed through
    source: Mapping[str, Any] = field(default_factory=dict, compare=False, repr=False)  # original item

    def replace(self, **changes) -> ToolDef
    def fingerprint(self) -> str     # sha256 of canonical JSON of (name, description, input_schema)
    def render(self) -> str          # compact JSON {"name","description","parameters"} for token counting

@dataclass(frozen=True, slots=True)
class ToolSet:
    tools: tuple[ToolDef, ...]
    format: ToolFormat
    document: Any                    # original parsed JSON document (deep copy)
    path: tuple[str | int, ...]      # where the tool list lives in `document` (() = top-level list)
    def replace_tools(self, tools: Sequence[ToolDef]) -> ToolSet
    def function_tools(self) -> tuple[ToolDef, ...]   # non-opaque
```

**Errors** (`errors.py`):

```
ToolslimError
├── FormatError           # unrecognised / invalid / mixed tool formats, bad JSON
├── TokenizerError        # unknown tokenizer spec
│   └── TokenizerUnavailable   # known, but can't load (missing extra, offline vocab, no API key)
├── RuleError             # unknown rule id, bad option, rule contract violation
├── MissingExtraError     # optional dependency not installed; message names the pip extra
├── LoaderError           # MCP server failed to start / list tools
└── BaselineError         # bad / missing / incompatible baseline file
```

## Behaviour & edge cases

- **Canonical JSON for fingerprints:** `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`.
- **`render()` keeps key order:** providers see key order, and fingerprints are order-insensitive on purpose. It omits `description` / `parameters` when they're `None`.
- **Opaque tools** have `input_schema=None` and render to `""` (counted as 0 and reported as uncounted).
- **`source` holds the original item.** Serialization patches a copy of it, so unknown keys and key order survive (C2).

## Tests

- `replace()` returns a new object; `fingerprint()` is stable across key order and changes when any of the three fields change.
- `render()` byte-exact output for a fixture; unicode stays unescaped.
- An error-hierarchy test: every error is a `ToolslimError`.

## Review

| Issue | Change |
|---|---|
| The first draft stored `extras` + `key_order`. Two parallel structures can drift apart, and re-creating key order is fiddly. | Replaced with `source` (the original item). Serialization patches a deep copy of it. Simpler and exactly reversible. |
| `frozen=True` with `dict` fields isn't deep immutability. | Documented; the pipeline deep-copies before each rule and tests compare fingerprints (review R9). |
| Is `fingerprint()` on every comparison too slow? | It's cached per instance (`functools.cached_property` doesn't work with slots; use a private field computed lazily via `object.__setattr__`). |
| `name` for opaque tools (OpenAI `{"type":"web_search_preview"}` has no name). | Use `name` if present, otherwise `type`, otherwise `"<unnamed>"`. |
