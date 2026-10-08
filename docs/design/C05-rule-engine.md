# C5 — Rule engine

## Responsibility

The contract every rule follows: registration, metadata, options, context. It makes "add a rule" a one-file change.

## Interface

```python
class Safety(IntEnum):
    SAFE = 0                 # validation-equivalent; only redundant information removed
    LOSSY_ANNOTATIONS = 1    # validation-equivalent; may drop non-redundant annotation text
    CHANGES_VALIDATION = 2   # may change accepted instances (reserved)

@dataclass(frozen=True)
class OptionSpec: type: type; default: Any; help: str

@dataclass(frozen=True)
class RuleContext:
    tool: ToolDef           # the tool being rewritten (original name etc.)
    dialect: Dialect
    strict: bool
    options: Mapping[str, Any]   # resolved: defaults overlaid with user values

class Rule(ABC):
    id: ClassVar[str]               # "SL001"
    name: ClassVar[str]             # "redundant-title"
    summary: ClassVar[str]          # one line, shown by `toolslim rules`
    safety: ClassVar[Safety]
    default_enabled: ClassVar[bool] = True
    reorders: ClassVar[bool] = False        # True only for tool-order rules (SL007)
    options: ClassVar[Mapping[str, OptionSpec]] = {}
    @abstractmethod
    def apply(self, tools: tuple[ToolDef, ...], options: Mapping[str, Any]) -> tuple[ToolDef, ...]

class ToolRule(Rule):           # per-tool; skips opaque tools
    def apply(...) -> tuple[ToolDef, ...]          # implemented: maps apply_tool
    @abstractmethod
    def apply_tool(self, tool: ToolDef, ctx: RuleContext) -> ToolDef

class SchemaRule(ToolRule):     # per-subschema
    def apply_tool(...) -> ToolDef                  # implemented: map_subschemas(schema, transform)
    @abstractmethod
    def transform(self, node: dict, path: SchemaPath, ctx: RuleContext) -> Any

# registry.py
def register_rule(cls: type[Rule]) -> type[Rule]   # decorator
def all_rules() -> tuple[type[Rule], ...]          # sorted by id; triggers discovery
def get_rule(key: str) -> type[Rule]               # by id ("SL001") or name ("redundant-title"), case-insensitive
def resolve_options(rule, user: Mapping[str, Any]) -> dict[str, Any]
def parse_option_assignment(text: str) -> tuple[str, str, Any]   # "SL101.max_chars=200"
```

## Behaviour & edge cases

**Discovery:** `toolslim.rules` imports every module named `sl[0-9][0-9][0-9]_*.py` in its package, in sorted order. Contributors drop in a file — no list to edit.

**Registration checks:**
- id matches `^SL\d{3}$`
- id and name are unique
- name is kebab-case
- `safety` is set
- `SL0xx` must be SAFE; `SL1xx` must be lossy (≥ LOSSY_ANNOTATIONS)
- Violations raise `RuleError` at import time, so a bad rule fails CI immediately.

**Rule contract** (enforced by the pipeline):
- Same number of tools out as in.
- Order unchanged unless `reorders`.
- Names unchanged.
- Opaque tools unchanged.
- Violations → `RuleError` naming the rule.

**Options:** values from the CLI arrive as strings and are coerced to `OptionSpec.type` (int, float, bool, str). Unknown option → `RuleError`.

## Tests

- Registry: discovery finds all shipped rules; a duplicate id or bad id raises; lookup by id and name.
- Option parsing / coercion / unknown-option errors.
- Contract enforcement: a deliberately broken test rule (drops a tool, renames one) raises `RuleError`.

## Review

| Issue | Change |
|---|---|
| Rules could import the pipeline or tokenizers and create cycles. | Rules get everything they need via `RuleContext`. The layering test forbids `rules → pipeline` and `rules → tokenizers`. |
| Do rules need to know about strict mode, or is it a pipeline concern? | Rules decide. Only the rule knows which keywords it touches. `ctx.strict` is provided. |
| An ID numbering scheme that encodes safety (`SL0xx` safe / `SL1xx` lossy) could drift from the declared `safety`. | Checked at registration time. |
| Auto-discovery via filesystem could import arbitrary files. | Only the package's own directory, with the strict filename pattern. |
