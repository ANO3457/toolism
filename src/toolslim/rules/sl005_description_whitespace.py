"""SL005 description-whitespace — dedent docstrings and collapse redundant whitespace."""

from __future__ import annotations

import re
from typing import Any

from toolslim.models import ToolDef
from toolslim.rules.base import RuleContext, Safety, ToolRule
from toolslim.rules.registry import register_rule
from toolslim.schema import SchemaPath, map_subschemas

_SPACE_RUNS = re.compile(r" {2,}")
_BLANK_RUNS = re.compile(r"\n{3,}")


def clean_whitespace(text: str) -> str:
    """Docstring-style cleanup that changes whitespace only (tabs are left untouched)."""
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    if not lines:
        return ""
    first, rest = lines[0].lstrip(" "), lines[1:]
    indents = [len(line) - len(line.lstrip(" ")) for line in rest if line]
    common = min(indents, default=0)
    cleaned = []
    for line in [first, *(line[common:] for line in rest)]:
        lead = len(line) - len(line.lstrip(" "))
        cleaned.append(" " * lead + _SPACE_RUNS.sub(" ", line[lead:]))
    return _BLANK_RUNS.sub("\n\n", "\n".join(cleaned))


@register_rule
class DescriptionWhitespace(ToolRule):
    """Python docstrings arrive indented, with blank lines and trailing spaces. Every whitespace
    token costs input tokens. Only whitespace changes; leading indentation that marks nested list
    structure is kept."""

    id = "SL005"
    name = "description-whitespace"
    summary = "Dedent docstrings, strip trailing spaces, collapse blank lines and space runs"
    safety = Safety.SAFE

    def apply_tool(self, tool: ToolDef, ctx: RuleContext) -> ToolDef:
        description = tool.description
        if isinstance(description, str):
            description = clean_whitespace(description)

        def clean_node(node: dict[str, Any], path: SchemaPath) -> Any:
            value = node.get("description")
            if isinstance(value, str):
                node["description"] = clean_whitespace(value)
            return node

        schema = map_subschemas(tool.input_schema, clean_node)
        if description == tool.description and schema == tool.input_schema:
            return tool
        return tool.replace(description=description, input_schema=schema)
