from __future__ import annotations

import pytest

from toolism import errors
from toolism.models import ToolDef, ToolFormat, ToolSet, canonical_json


def make_tool(**kw: object) -> ToolDef:
    base: dict[str, object] = {
        "name": "search",
        "description": "Search documents.",
        "input_schema": {"type": "object", "properties": {"q": {"type": "string"}}},
    }
    base.update(kw)
    return ToolDef(**base)  # type: ignore[arg-type]


def test_replace_returns_new_object_and_keeps_source() -> None:
    tool = make_tool(source={"name": "search", "x-extra": 1})
    new = tool.replace(description="Find documents.")
    assert new is not tool
    assert new.description == "Find documents."
    assert tool.description == "Search documents."
    assert new.source == {"name": "search", "x-extra": 1}


def test_fingerprint_ignores_key_order_but_detects_changes() -> None:
    a = make_tool(input_schema={"type": "object", "properties": {"q": {"type": "string"}}})
    b = make_tool(input_schema={"properties": {"q": {"type": "string"}}, "type": "object"})
    assert a.fingerprint() == b.fingerprint()
    assert a.fingerprint() != a.replace(description="x").fingerprint()
    assert a.fingerprint() != a.replace(name="other").fingerprint()
    assert a.fingerprint() != a.replace(input_schema={"type": "object"}).fingerprint()
    # cached value is stable
    assert a.fingerprint() == a.fingerprint()


def test_fingerprint_distinguishes_absent_description_from_empty() -> None:
    assert make_tool(description=None).fingerprint() != make_tool(description="").fingerprint()


def test_render_is_compact_ordered_and_unicode() -> None:
    tool = ToolDef(
        name="t",
        description="Größe — café",
        input_schema={"type": "object", "properties": {}},
    )
    assert tool.render() == (
        '{"name":"t","description":"Größe — café","parameters":{"type":"object","properties":{}}}'
    )


def test_render_omits_absent_fields_and_opaque_renders_empty() -> None:
    assert ToolDef(name="t").render() == '{"name":"t"}'
    assert ToolDef(name="web_search", opaque=True).render() == ""


def test_equality_ignores_source_and_hash_uses_fingerprint() -> None:
    a = make_tool(source={"a": 1})
    b = make_tool(source={"b": 2})
    assert a == b
    assert hash(a) == hash(b)
    assert len({a, b}) == 1


def test_toolset_helpers() -> None:
    t1 = make_tool()
    t2 = ToolDef(name="web_search", opaque=True)
    ts = ToolSet(tools=(t1, t2), format=ToolFormat.OPENAI_RESPONSES)
    assert len(ts) == 2
    assert list(ts) == [t1, t2]
    assert ts.function_tools() == (t1,)
    ts2 = ts.replace_tools([t1])
    assert ts2.tools == (t1,)
    assert ts.tools == (t1, t2)
    assert ts2.format is ToolFormat.OPENAI_RESPONSES


def test_toolformat_str() -> None:
    assert str(ToolFormat.MCP) == "mcp"
    assert ToolFormat("anthropic") is ToolFormat.ANTHROPIC


def test_canonical_json_sorted_and_compact() -> None:
    assert canonical_json({"b": 1, "a": [1, 2]}) == '{"a":[1,2],"b":1}'


@pytest.mark.parametrize(
    "cls",
    [
        errors.FormatError,
        errors.TokenizerError,
        errors.TokenizerUnavailable,
        errors.RuleError,
        errors.LoaderError,
        errors.BaselineError,
    ],
)
def test_error_hierarchy(cls: type[errors.ToolismError]) -> None:
    err = cls("boom", hint="try this")
    assert isinstance(err, errors.ToolismError)
    assert err.message == "boom"
    assert err.hint == "try this"
    assert str(err) == "boom"


def test_missing_extra_error_names_the_extra() -> None:
    err = errors.MissingExtraError("Verification", "verify")
    assert err.extra == "verify"
    assert err.hint == "pip install 'toolism[verify]'"
    assert isinstance(err, errors.ToolismError)
