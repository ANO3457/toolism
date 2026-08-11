"""toolslim — measure and safely slim the token cost of LLM tool and MCP schemas.

>>> import toolslim
>>> toolset = toolslim.load("tools.json")            # OpenAI, Anthropic or MCP JSON
>>> toolslim.measure(toolset, tokenizer="heuristic").total
>>> result = toolslim.slim(toolset, level="safe")
>>> toolslim.dump(result.toolset, "tools.slim.json")  # same format and envelope as the input
>>> tools = toolslim.slim_tools(my_tool_dicts)         # one call for agent code

Attributes load lazily, so ``import toolslim`` stays cheap.
"""

from __future__ import annotations

import importlib
import json
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from toolslim.__about__ import __version__

if TYPE_CHECKING:
    from toolslim.errors import (
        BaselineError,
        FormatError,
        LoaderError,
        MissingExtraError,
        RuleError,
        TokenizerError,
        TokenizerUnavailable,
        ToolslimError,
    )
    from toolslim.formats import parse, serialize
    from toolslim.io import dump, dumps, load, loads
    from toolslim.loaders.mcp import load_mcp_stdio
    from toolslim.measurement import TokenReport, measure
    from toolslim.models import ToolDef, ToolFormat, ToolSet
    from toolslim.pipeline import SlimReport, SlimResult, slim
    from toolslim.rules import Rule, Safety

__all__ = [
    "BaselineError",
    "FormatError",
    "LoaderError",
    "MissingExtraError",
    "Rule",
    "RuleError",
    "Safety",
    "SlimReport",
    "SlimResult",
    "TokenReport",
    "TokenizerError",
    "TokenizerUnavailable",
    "ToolDef",
    "ToolFormat",
    "ToolSet",
    "ToolslimError",
    "__version__",
    "dump",
    "dumps",
    "list_rules",
    "load",
    "load_mcp_stdio",
    "loads",
    "measure",
    "parse",
    "serialize",
    "slim",
    "slim_tools",
]

_LAZY = {
    "BaselineError": "toolslim.errors",
    "FormatError": "toolslim.errors",
    "LoaderError": "toolslim.errors",
    "MissingExtraError": "toolslim.errors",
    "RuleError": "toolslim.errors",
    "TokenizerError": "toolslim.errors",
    "TokenizerUnavailable": "toolslim.errors",
    "ToolslimError": "toolslim.errors",
    "parse": "toolslim.formats",
    "serialize": "toolslim.formats",
    "dump": "toolslim.io",
    "dumps": "toolslim.io",
    "load": "toolslim.io",
    "loads": "toolslim.io",
    "load_mcp_stdio": "toolslim.loaders.mcp",
    "TokenReport": "toolslim.measurement",
    "measure": "toolslim.measurement",
    "ToolDef": "toolslim.models",
    "ToolFormat": "toolslim.models",
    "ToolSet": "toolslim.models",
    "SlimReport": "toolslim.pipeline",
    "SlimResult": "toolslim.pipeline",
    "slim": "toolslim.pipeline",
    "Rule": "toolslim.rules",
    "Safety": "toolslim.rules",
}


def __getattr__(name: str) -> Any:
    module = _LAZY.get(name)
    if module is None:
        raise AttributeError(f"module 'toolslim' has no attribute {name!r}")
    value = getattr(importlib.import_module(module), name)
    globals()[name] = value  # later lookups skip __getattr__
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))


def list_rules() -> tuple[type[Rule], ...]:
    """Every available rule class, sorted by id (``rule.id``, ``rule.name``, ``rule.summary``)."""
    from toolslim.rules import all_rules

    return all_rules()


@lru_cache(maxsize=128)
def _slim_cached(document: str, settings: str) -> str:
    from toolslim.formats import parse, serialize
    from toolslim.pipeline import slim

    result = slim(parse(json.loads(document)), **json.loads(settings))
    return json.dumps(serialize(result.toolset), ensure_ascii=False)


def slim_tools(
    tools: Any, *, level: str = "safe", tokenizer: Any = "heuristic", **kwargs: Any
) -> Any:
    """Slim a tool list (or any supported document) and return it in the same shape.

    Meant for agent code that builds its tools on every request: results are cached by input,
    and every call returns fresh objects you may mutate. ``kwargs`` are passed to
    :func:`toolslim.slim` (``enable``, ``disable``, ``options``, ``verify``...). The default
    tokenizer is the offline heuristic: the counts only feed the (discarded) report.
    """
    settings = {"level": level, "tokenizer": tokenizer, **kwargs}
    try:
        key = json.dumps(settings, sort_keys=True)
        document = json.dumps(tools, ensure_ascii=False)
    except (TypeError, ValueError):  # e.g. a Tokenizer instance: run uncached
        from toolslim.formats import parse, serialize
        from toolslim.pipeline import slim

        return serialize(slim(parse(tools), **settings).toolset)
    return json.loads(_slim_cached(document, key))
