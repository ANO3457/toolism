"""The public API (architecture §9): everything in ``__all__`` resolves, lazily."""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import toolslim
from toolslim.tokenizers import HeuristicTokenizer

FIXTURE = Path(__file__).parent / "fixtures" / "formats" / "mcp_tools.json"

ANTHROPIC = [
    {
        "name": "get_weather",
        "description": "Get the weather.",
        "input_schema": {
            "type": "object",
            "title": "get_weatherArguments",
            "properties": {"city": {"type": "string", "title": "City"}},
            "required": ["city"],
        },
    }
]


@pytest.mark.parametrize("name", toolslim.__all__)
def test_every_public_name_resolves(name: str) -> None:
    assert getattr(toolslim, name) is not None
    assert name in dir(toolslim)


def test_no_submodule_shadows_a_public_name() -> None:
    """Importing ``toolslim.x`` binds ``x`` on the package, hiding a lazy function ``x``."""
    package = Path(toolslim.__file__).parent
    submodules = {p.stem for p in package.glob("*.py")} | {
        p.name for p in package.iterdir() if (p / "__init__.py").exists()
    }
    assert not submodules & set(toolslim.__all__)
    importlib.import_module("toolslim.measurement")
    importlib.import_module("toolslim.pipeline")
    assert callable(toolslim.measure)
    assert callable(toolslim.slim)


def test_unknown_attribute() -> None:
    with pytest.raises(AttributeError, match="no attribute 'nope'"):
        _ = toolslim.nope  # type: ignore[attr-defined]


def test_import_is_lazy() -> None:
    code = (
        "import json, sys, toolslim; "
        "print(json.dumps(sorted(m for m in sys.modules if m.startswith('toolslim'))))"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], check=True, capture_output=True, text=True, encoding="utf-8"
    )
    assert json.loads(out.stdout) == ["toolslim", "toolslim.__about__"]


def test_documented_workflow(tmp_path: Path) -> None:
    toolset = toolslim.load(FIXTURE)
    report = toolslim.measure(toolset, tokenizer="heuristic")
    assert report.total > 0
    result = toolslim.slim(toolset, tokenizer="heuristic")
    assert result.report.after <= report.total
    out = tmp_path / "slim.json"
    toolslim.dump(result.toolset, out)
    assert toolslim.loads(out.read_text(encoding="utf-8")).format is toolslim.ToolFormat.MCP
    assert [r.id for r in toolslim.list_rules()][:2] == ["SL001", "SL002"]


def test_slim_tools_keeps_shape_and_returns_fresh_objects() -> None:
    first: Any = toolslim.slim_tools(ANTHROPIC)
    assert isinstance(first, list)
    assert first[0]["input_schema"] == {
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"],
    }
    first[0]["name"] = "mutated"
    second = toolslim.slim_tools(ANTHROPIC)
    assert second[0]["name"] == "get_weather"  # cache is not affected by caller mutation
    assert ANTHROPIC[0]["input_schema"]["title"] == "get_weatherArguments"  # input untouched


def test_slim_tools_passes_options_and_handles_uncacheable_settings() -> None:
    kept = toolslim.slim_tools(ANTHROPIC, disable=["SL001"])
    assert kept[0]["input_schema"]["title"] == "get_weatherArguments"
    uncached = toolslim.slim_tools(ANTHROPIC, tokenizer=HeuristicTokenizer())
    assert uncached == toolslim.slim_tools(ANTHROPIC)
