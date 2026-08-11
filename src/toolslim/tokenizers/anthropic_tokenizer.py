"""Ground-truth counts from Anthropic's ``count_tokens`` endpoint (design C4).

* ``count_tools(T)`` = tokens(request with T) − tokens(request without tools). It includes the fixed
  tool-use preamble once.
* ``count_tool(t)`` = tokens(request with [t]) − tokens(request with a minimal probe tool): the
  *marginal* cost of one tool, excluding the preamble.

Sends tool definitions to Anthropic — only used when the user asks for it explicitly.
"""

from __future__ import annotations

import os
import re
from collections.abc import Sequence
from typing import Any

from toolslim.errors import TokenizerUnavailable
from toolslim.models import ToolDef

__all__ = ["AnthropicTokenizer"]

_PROBE: dict[str, Any] = {"name": "x", "input_schema": {"type": "object"}}
_MESSAGES = [{"role": "user", "content": "."}]
_INVALID_NAME_CHARS = re.compile(r"[^a-zA-Z0-9_-]")


def to_anthropic_tool(tool: ToolDef) -> dict[str, Any]:
    """Convert any tool to the Anthropic wire shape used for counting."""
    schema = tool.input_schema if isinstance(tool.input_schema, dict) else {"type": "object"}
    item: dict[str, Any] = {"name": _INVALID_NAME_CHARS.sub("_", tool.name)[:128] or "tool"}
    if tool.description is not None:
        item["description"] = tool.description
    item["input_schema"] = schema
    return item


class AnthropicTokenizer:
    """Counts with ``client.messages.count_tokens`` for a given Claude model."""

    approximate = False
    local = False

    def __init__(self, model: str, client: Any = None) -> None:
        self.model = model
        self.name = f"anthropic:{model}"
        self._client = client if client is not None else self._make_client()
        self._cache: dict[str, int] = {}
        self._baseline: int | None = None
        self._probe: int | None = None

    @staticmethod
    def _make_client() -> Any:
        try:
            import anthropic
        except ImportError as exc:
            raise TokenizerUnavailable(
                "the anthropic tokenizer needs the anthropic package",
                hint="pip install 'toolslim[anthropic]'",
            ) from exc
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise TokenizerUnavailable(
                "ANTHROPIC_API_KEY is not set", hint="export ANTHROPIC_API_KEY=... or pick another"
            )
        return anthropic.Anthropic()

    def _count(self, tools: list[dict[str, Any]]) -> int:
        kwargs: dict[str, Any] = {"model": self.model, "messages": _MESSAGES}
        if tools:
            kwargs["tools"] = tools
        try:
            return int(self._client.messages.count_tokens(**kwargs).input_tokens)
        except Exception as exc:
            raise TokenizerUnavailable(f"Anthropic count_tokens failed: {exc}") from exc

    def _baseline_tokens(self) -> int:
        if self._baseline is None:
            self._baseline = self._count([])
        return self._baseline

    def _probe_tokens(self) -> int:
        if self._probe is None:
            self._probe = self._count([_PROBE])
        return self._probe

    def count_tool(self, tool: ToolDef) -> int:
        if tool.opaque:
            return 0
        key = tool.fingerprint()
        if key not in self._cache:
            marginal = self._count([to_anthropic_tool(tool)]) - self._probe_tokens()
            self._cache[key] = max(marginal, 0)
        return self._cache[key]

    def count_tools(self, tools: Sequence[ToolDef]) -> int:
        items = [to_anthropic_tool(t) for t in tools if not t.opaque]
        if not items:
            return 0
        return self._count(items) - self._baseline_tokens()

    def __repr__(self) -> str:
        return f"<AnthropicTokenizer {self.name}>"
