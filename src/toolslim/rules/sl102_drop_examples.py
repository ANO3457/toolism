"""SL102 drop-examples — remove ``examples`` / ``example`` keywords (lossy, opt-in)."""

from __future__ import annotations

from typing import Any

from toolslim.rules.base import RuleContext, Safety, SchemaRule
from toolslim.rules.registry import register_rule
from toolslim.schema import SchemaPath


@register_rule
class DropExamples(SchemaRule):
    """Examples are annotations: dropping them never changes validation, but they can help the
    model produce well-formed arguments — measure before and after on your own evals."""

    id = "SL102"
    name = "drop-examples"
    summary = "Remove examples / example keywords from schemas"
    safety = Safety.LOSSY_ANNOTATIONS

    def transform(self, node: dict[str, Any], path: SchemaPath, ctx: RuleContext) -> Any:
        node.pop("examples", None)
        node.pop("example", None)
        return node
