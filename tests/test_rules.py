"""Fixture-driven tests for every shipped rule (design C6).

Each ``tests/fixtures/rules/SLxxx.json`` holds a list of cases::

    {"name": ..., "tool": {"name", "description"?, "schema"?}, "strict"?: bool,
     "options"?: {...}, "expected_schema"?: ..., "expected_description"?: ...,
     "verify"?: "skip-ok"}

Missing ``expected_*`` keys mean "unchanged", and then the rule must return the very same object.
For every case that changes a schema, the runner proves the change with bidirectional
property-based equivalence (needs the ``verify`` extra).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from toolism.models import ToolDef
from toolism.rules import Safety, all_rules, get_rule, resolve_options
from toolism.verify import Verdict, check_equivalence, verify_available

FIXTURES = Path(__file__).parent / "fixtures" / "rules"


def _cases() -> list[Any]:
    params = []
    for path in sorted(FIXTURES.glob("SL*.json")):
        rule_id = path.stem
        for case in json.loads(path.read_text(encoding="utf-8")):
            params.append(pytest.param(rule_id, case, id=f"{rule_id}: {case['name']}"))
    return params


def _tool(case: dict[str, Any]) -> ToolDef:
    spec = case["tool"]
    return ToolDef(
        name=spec.get("name", "tool"),
        description=spec.get("description"),
        input_schema=copy.deepcopy(spec.get("schema")),
        strict=case.get("strict", False),
    )


def _ordered(value: Any) -> str:
    """Key-order-sensitive rendering, so fixtures also lock where keys end up."""
    return json.dumps(value, ensure_ascii=False)


@pytest.mark.parametrize(("rule_id", "case"), _cases())
def test_rule_fixture(rule_id: str, case: dict[str, Any]) -> None:
    rule_cls = get_rule(rule_id)
    rule = rule_cls()
    tool = _tool(case)
    before = copy.deepcopy((tool.description, tool.input_schema))
    options = resolve_options(rule_cls, case.get("options"))

    (out,) = rule.apply((tool,), options)

    assert (tool.description, tool.input_schema) == before, "rule mutated its input"
    expected_schema = case.get("expected_schema", case["tool"].get("schema"))
    expected_description = case.get("expected_description", case["tool"].get("description"))
    assert _ordered(out.input_schema) == _ordered(expected_schema)
    assert out.description == expected_description
    if "expected_schema" not in case and "expected_description" not in case:
        assert out is tool, "a rule with nothing to do must return the same object"

    # Idempotence: a second application changes nothing.
    (again,) = rule.apply((out,), options)
    assert again.fingerprint() == out.fingerprint()

    if out.input_schema != tool.input_schema and verify_available():
        result = check_equivalence(tool.input_schema, out.input_schema)
        assert result.verdict is not Verdict.COUNTEREXAMPLE, result
        if case.get("verify") != "skip-ok":
            assert result.verdict is Verdict.EQUIVALENT, result


def test_every_shipped_rule_has_fixtures_or_a_dedicated_test() -> None:
    with_fixtures = {p.stem for p in FIXTURES.glob("SL*.json")}
    dedicated = {"SL007"}  # tool-order rule: tested below
    missing = {r.id for r in all_rules()} - with_fixtures - dedicated
    assert not missing, f"rules without tests: {sorted(missing)}"


def test_catalogue_metadata() -> None:
    rules = {r.id: r for r in all_rules()}
    assert list(rules) == sorted(rules)
    assert set(rules) >= {f"SL00{i}" for i in range(1, 10)} | {"SL101", "SL102"}
    for rule in rules.values():
        assert rule.summary, rule.id
        assert len(rule.summary) <= 90, rule.id
        assert rule.__doc__, f"{rule.id} needs a docstring explaining why it is safe"
        if rule.safety is Safety.SAFE:
            assert rule.id.startswith("SL0")
    off_by_default = {r.id for r in rules.values() if not r.default_enabled}
    assert off_by_default == {"SL007"}  # lossy rules are gated by --level, not by this flag


# ----------------------------------------------------------------- SL007


def test_stable_order_sorts_and_is_noop_when_sorted() -> None:
    rule = get_rule("stable-order")()
    a, b, c = (ToolDef(name=n) for n in "abc")
    assert rule.apply((c, a, b), {}) == (a, b, c)
    already = (a, b, c)
    assert rule.apply(already, {}) is already
    assert rule.reorders
    assert not rule.default_enabled


# -------------------------------------------------- rule-specific edge cases


def test_sl101_rejects_nonsense_limit() -> None:
    from toolism.errors import RuleError

    rule_cls = get_rule("SL101")
    tool = ToolDef(name="t", description="x" * 50, input_schema={"type": "object"})
    with pytest.raises(RuleError, match="at least 2"):
        rule_cls().apply((tool,), resolve_options(rule_cls, {"max_chars": 1}))


def test_sl101_truncate_without_spaces() -> None:
    from toolism.rules.sl101_max_description_length import truncate

    assert truncate("x" * 10, 5) == "xxxx…"
    assert len(truncate("word " * 40, 37)) <= 37


def test_opaque_tools_are_never_touched() -> None:
    opaque = ToolDef(name="web_search", opaque=True, source={"type": "web_search_20250305"})
    for rule_cls in all_rules():
        rule = rule_cls()
        assert rule.apply((opaque,), resolve_options(rule_cls))[0] is opaque


def test_schemaless_tools_are_fine() -> None:
    bare = ToolDef(name="ping", description="Ping.")
    for rule_cls in all_rules():
        out = rule_cls().apply((bare,), resolve_options(rule_cls))[0]
        assert out.input_schema is None
