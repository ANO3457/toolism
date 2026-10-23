"""SL104 dedupe-descriptions — drop property descriptions repeated in the tool description."""

from __future__ import annotations

from typing import Any

from toolism.rules.base import RuleContext, Safety, SchemaRule
from toolism.rules.registry import register_rule
from toolism.schema import SchemaPath, property_name


@register_rule
class DedupeDescriptions(SchemaRule):
    """Some servers repeat each property's description word for word in the tool description, so
    the model pays for the same text twice. Drop the property-level copy only when it appears
    verbatim (after whitespace trimming) in the tool description."""

    id = "SL104"
    name = "dedupe-descriptions"
    summary = "Drop property descriptions that appear verbatim in the tool description"
    safety = Safety.LOSSY_ANNOTATIONS

    def transform(self, node: dict[str, Any], path: SchemaPath, ctx: RuleContext) -> Any:
        description = node.get("description")
        if not isinstance(description, str) or not description.strip():
            return node
        if property_name(path) is None:
            return node
        tool_description = ctx.tool.description or ""
        if not tool_description:
            return node
        needle = description.strip()
        if needle and needle in tool_description:
            del node["description"]
        return node
