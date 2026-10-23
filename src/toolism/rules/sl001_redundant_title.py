"""SL001 redundant-title — drop ``title`` keywords that only repeat a name the model sees."""

from __future__ import annotations

from typing import Any

from toolism.rules._util import norm
from toolism.rules.base import RuleContext, Safety, SchemaRule
from toolism.rules.registry import register_rule
from toolism.schema import SchemaPath, defs_name, property_name

# Suffixes generators append to a tool's argument model (FastMCP: "search_eventsArguments").
_ROOT_SUFFIXES = (
    "",
    "arguments",
    "args",
    "input",
    "inputs",
    "params",
    "parameters",
    "request",
    "schema",
)


@register_rule
class RedundantTitle(SchemaRule):
    """``title`` is an annotation. Pydantic and FastMCP add one to every property and model, set to
    the property name ("User Id" for ``user_id``) or the model/function name — information the
    model already has from the property key or tool name. Informative titles are kept."""

    id = "SL001"
    name = "redundant-title"
    summary = "Drop titles that only repeat the property, $defs key or tool name"
    safety = Safety.SAFE

    def transform(self, node: dict[str, Any], path: SchemaPath, ctx: RuleContext) -> Any:
        title = node.get("title")
        if not isinstance(title, str):
            return node
        normalized = norm(title)
        if not path:
            tool = norm(ctx.tool.name)
            redundant = any(normalized == tool + suffix for suffix in _ROOT_SUFFIXES)
        else:
            owner = property_name(path) or defs_name(path)
            redundant = owner is not None and normalized == norm(owner)
        if redundant:
            del node["title"]
        return node
