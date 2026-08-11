"""SL101 max-description-length — truncate long descriptions (lossy, opt-in)."""

from __future__ import annotations

import re
from typing import Any

from toolslim.errors import RuleError
from toolslim.models import ToolDef
from toolslim.rules.base import OptionSpec, RuleContext, Safety, ToolRule
from toolslim.rules.registry import register_rule
from toolslim.schema import SchemaPath, map_subschemas

_SENTENCE_END = re.compile(r"[.!?](?=\s)|\n")
_MIN_SENTENCE_FRACTION = 0.4
ELLIPSIS = "…"


def truncate(text: str, limit: int) -> str:
    """Cut ``text`` to at most ``limit`` characters.

    Prefers the last sentence end (if it keeps at least 40% of the limit); otherwise cuts at the
    last space and appends an ellipsis.
    """
    if len(text) <= limit:
        return text
    window = text[:limit]
    ends = [m.end() for m in _SENTENCE_END.finditer(window)]
    if ends and ends[-1] >= limit * _MIN_SENTENCE_FRACTION:
        return text[: ends[-1]].rstrip()
    cut = window.rfind(" ")
    if cut <= 0:
        cut = limit - 1
    return text[:cut].rstrip() + ELLIPSIS


@register_rule
class MaxDescriptionLength(ToolRule):
    """Long descriptions (pasted API docs, examples, caveats) are often the biggest part of a tool
    definition. Truncating them loses information the model might use, so this rule is lossy and
    opt-in. Tool-level descriptions are only truncated with ``include_tool=true``."""

    id = "SL101"
    name = "max-description-length"
    summary = "Truncate descriptions longer than max_chars at a sentence boundary"
    safety = Safety.LOSSY_ANNOTATIONS
    option_specs = {  # noqa: RUF012
        "max_chars": OptionSpec(int, 300, "maximum characters per description"),
        "include_tool": OptionSpec(bool, False, "also truncate the tool-level description"),
    }

    def apply_tool(self, tool: ToolDef, ctx: RuleContext) -> ToolDef:
        limit = ctx.options.get("max_chars", 300)
        if limit < 2:
            raise RuleError(f"{self.id}: max_chars must be at least 2, got {limit}")
        description = tool.description
        if ctx.options.get("include_tool", False) and isinstance(description, str):
            description = truncate(description, limit)

        def shorten(node: dict[str, Any], path: SchemaPath) -> Any:
            value = node.get("description")
            if isinstance(value, str):
                node["description"] = truncate(value, limit)
            return node

        schema = map_subschemas(tool.input_schema, shorten)
        if description == tool.description and schema == tool.input_schema:
            return tool
        return tool.replace(description=description, input_schema=schema)
