"""Tokenizer protocol and the shared base for local, text-based tokenizers (design C4)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from toolism.models import ToolDef

__all__ = ["TextTokenizer", "Tokenizer"]

_CACHE_LIMIT = 4096


@runtime_checkable
class Tokenizer(Protocol):
    """Counts the tokens a model reads for tool definitions."""

    name: str
    """Stable identifier, e.g. ``"tiktoken:o200k_base"``. Recorded in every report and baseline."""
    approximate: bool
    """``True`` unless counts come from the provider itself for that provider's models."""
    local: bool
    """``False`` if counting makes network calls (unsuitable for per-rule attribution)."""

    def count_tool(self, tool: ToolDef) -> int: ...

    def count_tools(self, tools: Sequence[ToolDef]) -> int: ...


class TextTokenizer(ABC):
    """Base for local tokenizers that count the text of :meth:`ToolDef.render`.

    Counts are cached by tool fingerprint (bounded, FIFO eviction).
    """

    name: str
    approximate: bool = True
    local: bool = True

    def __init__(self) -> None:
        self._cache: dict[str, int] = {}

    @abstractmethod
    def count_text(self, text: str) -> int:
        """Number of tokens in ``text``."""

    def count_tool(self, tool: ToolDef) -> int:
        if tool.opaque:
            return 0
        key = tool.fingerprint()
        cached = self._cache.get(key)
        if cached is None:
            cached = self.count_text(tool.render())
            if len(self._cache) >= _CACHE_LIMIT:
                del self._cache[next(iter(self._cache))]
            self._cache[key] = cached
        return cached

    def count_tools(self, tools: Sequence[ToolDef]) -> int:
        return sum(self.count_tool(tool) for tool in tools)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.name}>"
