"""SL003 null-default — drop ``"default": null`` on optional properties."""

from __future__ import annotations

from typing import Any

from toolslim.rules.base import RuleContext, Safety, SchemaRule
from toolslim.rules.registry import register_rule
from toolslim.schema import SchemaPath


@register_rule
class NullDefault(SchemaRule):
    """``default`` is an annotation with no effect on validation. On a property that is not
    ``required``, ``default: null`` only restates "you may leave this out", which the missing
    ``required`` entry already says. Skipped for strict tools (every property is required there)."""

    id = "SL003"
    name = "null-default"
    summary = "Drop default: null on properties that are not required"
    safety = Safety.SAFE

    def transform(self, node: dict[str, Any], path: SchemaPath, ctx: RuleContext) -> Any:
        properties = node.get("properties")
        if ctx.strict or not isinstance(properties, dict):
            return node
        required = node.get("required")
        required_names = set(required) if isinstance(required, list) else set()
        changed = False
        rewritten: dict[str, Any] = {}
        for name, subschema in properties.items():
            if (
                name not in required_names
                and isinstance(subschema, dict)
                and "default" in subschema
                and subschema["default"] is None
            ):
                subschema = {k: v for k, v in subschema.items() if k != "default"}
                changed = True
            rewritten[name] = subschema
        if changed:
            node["properties"] = rewritten
        return node
