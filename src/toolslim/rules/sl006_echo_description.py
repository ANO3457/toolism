"""SL006 echo-description — drop property descriptions that only restate the property name."""

from __future__ import annotations

from typing import Any

from toolslim.rules._util import content_words
from toolslim.rules.base import RuleContext, Safety, SchemaRule
from toolslim.rules.registry import register_rule
from toolslim.schema import SchemaPath, property_name


@register_rule
class EchoDescription(SchemaRule):
    """``user_id: "The user ID."`` tells the model nothing the key ``user_id`` didn't. The match is
    exact on content words (case styles split, stop-words removed), so any extra word — "Unique
    user ID" — keeps the description. Tool-level descriptions are never touched."""

    id = "SL006"
    name = "echo-description"
    summary = "Drop property descriptions whose words only repeat the property name"
    safety = Safety.SAFE

    def transform(self, node: dict[str, Any], path: SchemaPath, ctx: RuleContext) -> Any:
        name = property_name(path)
        description = node.get("description")
        if name is None or not isinstance(description, str):
            return node
        words = content_words(description)
        if words and words == content_words(name):
            del node["description"]
        return node
