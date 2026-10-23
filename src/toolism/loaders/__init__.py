"""Tool sources other than JSON files. Each loader imports its optional dependency lazily."""

from __future__ import annotations

__all__ = ["load_mcp_stdio"]


def __getattr__(name: str) -> object:
    if name == "load_mcp_stdio":
        from toolism.loaders.mcp import load_mcp_stdio

        return load_mcp_stdio
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
