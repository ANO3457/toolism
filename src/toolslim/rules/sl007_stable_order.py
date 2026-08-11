"""SL007 stable-order — sort tools by name so prompt-cache prefixes stay stable (off by default)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from toolslim.models import ToolDef
from toolslim.rules.base import Rule, Safety
from toolslim.rules.registry import register_rule


@register_rule
class StableOrder(Rule):
    """Saves no tokens by itself. Agents that assemble tools from several MCP servers often send
    them in a different order on each request, which breaks provider prompt caching (cached reads
    cost ~10% of normal input). Off by default because tool order can be intentional."""

    id = "SL007"
    name = "stable-order"
    summary = "Sort tools by name (0 tokens saved; keeps prompt-cache prefixes stable)"
    safety = Safety.SAFE
    default_enabled = False
    reorders = True

    def apply(self, tools: tuple[ToolDef, ...], options: Mapping[str, Any]) -> tuple[ToolDef, ...]:
        ordered = tuple(sorted(tools, key=lambda tool: tool.name))
        return tools if ordered == tools else ordered
