from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar

import pytest

from toolslim.errors import RuleError
from toolslim.models import ToolDef
from toolslim.rules import (
    OptionSpec,
    Rule,
    RuleContext,
    Safety,
    SchemaRule,
    ToolRule,
    get_rule,
    parse_option_assignment,
    register_rule,
    resolve_options,
)
from toolslim.rules import registry as registry_module
from toolslim.schema import Dialect, SchemaPath


@pytest.fixture
def isolated_registry(monkeypatch: pytest.MonkeyPatch) -> dict[str, type[Rule]]:
    """A private, already-'discovered' registry so tests don't see or pollute the real one."""
    fresh: dict[str, type[Rule]] = {}
    monkeypatch.setattr(registry_module, "_REGISTRY", fresh)
    monkeypatch.setitem(registry_module._STATE, "discovered", True)
    return fresh


def _rule(rule_id: str = "SL900", name: str = "test-rule", **attrs: Any) -> type[Rule]:
    class _Test(ToolRule):
        summary = "a test rule"
        safety = Safety.SAFE

        def apply_tool(self, tool: ToolDef, ctx: RuleContext) -> ToolDef:
            return tool

    _Test.id = rule_id
    _Test.name = name
    for key, value in attrs.items():
        setattr(_Test, key, value)
    return _Test


# -------------------------------------------------------------------- Safety


@pytest.mark.parametrize(
    ("text", "level"),
    [
        ("safe", Safety.SAFE),
        ("SAFE", Safety.SAFE),
        ("annotations", Safety.LOSSY_ANNOTATIONS),
        ("lossy_annotations", Safety.LOSSY_ANNOTATIONS),
        ("validation", Safety.CHANGES_VALIDATION),
        (Safety.SAFE, Safety.SAFE),
    ],
)
def test_safety_parse(text: str | Safety, level: Safety) -> None:
    assert Safety.parse(text) is level


def test_safety_parse_error_and_labels() -> None:
    with pytest.raises(RuleError, match="unknown safety level") as info:
        Safety.parse("yolo")
    assert info.value.hint == "choose one of: safe, annotations, validation"
    assert Safety.LOSSY_ANNOTATIONS.label == "annotations"


# ------------------------------------------------------------------ registry


def test_register_and_lookup(isolated_registry: dict[str, type[Rule]]) -> None:
    rule = register_rule(_rule("SL001", "my-rule"))
    assert isolated_registry == {"SL001": rule}
    assert get_rule("SL001") is rule
    assert get_rule("sl001") is rule
    assert get_rule("My-Rule") is rule
    assert register_rule(rule) is rule  # re-registering the same class is a no-op
    with pytest.raises(RuleError, match="unknown rule") as info:
        get_rule("SL999")
    assert info.value.hint == "run 'toolslim rules' to list rules"


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (lambda: _rule("X1", "a"), "must look like"),
        (lambda: _rule("SL001", "Not_Kebab"), "kebab-case"),
        (lambda: _rule("SL001", "ok", summary=" "), "summary"),
        (lambda: _rule("SL001", "ok", safety="safe"), "Safety level"),
        (lambda: _rule("SL001", "ok", safety=Safety.LOSSY_ANNOTATIONS), "reserved for 'safe'"),
        (lambda: _rule("SL101", "ok", safety=Safety.SAFE), "reserved for 'annotations'"),
        (lambda: _rule("SL901", "ok"), "not a defined safety band"),
        (
            lambda: _rule("SL001", "ok", option_specs={"n": OptionSpec(int, "ten", "a number")}),
            "default for option",
        ),
    ],
)
def test_register_rejects_bad_metadata(
    isolated_registry: dict[str, type[Rule]], factory: Any, message: str
) -> None:
    with pytest.raises(RuleError, match=message):
        register_rule(factory())


def test_register_rejects_duplicates(isolated_registry: dict[str, type[Rule]]) -> None:
    register_rule(_rule("SL001", "one"))
    with pytest.raises(RuleError, match="duplicate rule id"):
        register_rule(_rule("SL001", "two"))
    with pytest.raises(RuleError, match="duplicate rule name"):
        register_rule(_rule("SL002", "one"))


# ------------------------------------------------------------------- options

OPTS = {
    "max_chars": OptionSpec(int, 300, "limit"),
    "ratio": OptionSpec(float, 0.5, "ratio"),
    "include_tool": OptionSpec(bool, False, "flag"),
    "suffix": OptionSpec(str, "…", "text"),
}


def test_resolve_options_defaults_and_coercion(isolated_registry: dict[str, type[Rule]]) -> None:
    rule = register_rule(_rule("SL101", "opts", option_specs=OPTS, safety=Safety.LOSSY_ANNOTATIONS))
    assert resolve_options(rule) == {
        "max_chars": 300,
        "ratio": 0.5,
        "include_tool": False,
        "suffix": "…",
    }
    resolved = resolve_options(
        rule, {"max_chars": "200", "ratio": 1, "include_tool": "yes", "suffix": "..."}
    )
    assert resolved == {"max_chars": 200, "ratio": 1.0, "include_tool": True, "suffix": "..."}
    assert resolve_options(rule, {"include_tool": "off"})["include_tool"] is False


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({"nope": 1}, "has no option 'nope'"),
        ({"max_chars": "lots"}, "expects int"),
        ({"include_tool": "maybe"}, "expects bool"),
        ({"max_chars": True}, "got a bool"),
        ({"max_chars": 2.5}, "got float"),
    ],
)
def test_resolve_options_errors(
    isolated_registry: dict[str, type[Rule]], values: dict[str, Any], message: str
) -> None:
    rule = register_rule(_rule("SL101", "opts", option_specs=OPTS, safety=Safety.LOSSY_ANNOTATIONS))
    with pytest.raises(RuleError, match=message):
        resolve_options(rule, values)


def test_parse_option_assignment() -> None:
    assert parse_option_assignment("SL101.max_chars=200") == ("SL101", "max_chars", "200")
    assert parse_option_assignment(" drop-examples.x = y ") == ("drop-examples", "x", "y")
    for bad in ("SL101=3", "SL101.max", ".x=1", "SL101.=1"):
        with pytest.raises(RuleError, match="invalid option"):
            parse_option_assignment(bad)


# ------------------------------------------------------------- base classes


class UpperDescriptions(ToolRule):
    id = "SL900"
    name = "upper"
    summary = "uppercase descriptions"
    safety = Safety.SAFE

    def apply_tool(self, tool: ToolDef, ctx: RuleContext) -> ToolDef:
        seen.append(ctx)
        return tool.replace(description=(tool.description or "").upper())


seen: list[RuleContext] = []


def test_tool_rule_skips_opaque_and_builds_context() -> None:
    seen.clear()
    tools = (
        ToolDef(
            name="a",
            description="x",
            input_schema={"$schema": "http://json-schema.org/draft-07/schema#"},
            strict=True,
        ),
        ToolDef(name="web", opaque=True),
    )
    out = UpperDescriptions().apply(tools, {"k": 1})
    assert out[0].description == "X"
    assert out[1] is tools[1]
    assert len(seen) == 1
    assert seen[0].dialect is Dialect.DRAFT7
    assert seen[0].strict is True
    assert seen[0].options == {"k": 1}
    assert repr(UpperDescriptions()) == "<SL900 upper>"


class DropTitles(SchemaRule):
    id = "SL901"
    name = "drop-titles"
    summary = "drop all titles"
    safety = Safety.SAFE
    paths: ClassVar[list[SchemaPath]] = []

    def transform(self, node: dict[str, Any], path: SchemaPath, ctx: RuleContext) -> Any:
        self.paths.append(path)
        node.pop("title", None)
        return node


def test_schema_rule_rewrites_and_returns_same_object_when_unchanged() -> None:
    tool = ToolDef(
        name="a",
        input_schema={"type": "object", "title": "A", "properties": {"x": {"title": "X"}}},
    )
    new = DropTitles().apply_tool(tool, RuleContext(tool, Dialect.DRAFT2020_12, False))
    assert new.input_schema == {"type": "object", "properties": {"x": {}}}
    assert tool.input_schema["title"] == "A"  # input untouched
    again = DropTitles().apply_tool(new, RuleContext(new, Dialect.DRAFT2020_12, False))
    assert again is new
    no_schema = ToolDef(name="b")
    assert DropTitles().apply_tool(no_schema, RuleContext(no_schema, Dialect.DRAFT7, False)) is (
        no_schema
    )


def test_rule_apply_signature_is_tuple_in_tuple_out() -> None:
    class Reverse(Rule):
        id = "SL902"
        name = "reverse"
        summary = "reverse order"
        safety = Safety.SAFE
        reorders = True

        def apply(
            self, tools: tuple[ToolDef, ...], options: Mapping[str, Any]
        ) -> tuple[ToolDef, ...]:
            return tuple(reversed(tools))

    a, b = ToolDef(name="a"), ToolDef(name="b")
    assert Reverse().apply((a, b), {}) == (b, a)
