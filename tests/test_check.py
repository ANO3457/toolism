from __future__ import annotations

import json
from pathlib import Path

import pytest

from toolism.check import (
    Baseline,
    Budget,
    baseline_from_report,
    load_baseline,
    parse_increase,
    render_check,
    run_check,
    save_baseline,
)
from toolism.errors import BaselineError
from toolism.measurement import TokenReport, ToolCount


def report(total: int, **tools: int) -> TokenReport:
    counts = tuple(ToolCount(n, t) for n, t in tools.items())
    return TokenReport(
        tokenizer="heuristic",
        approximate=True,
        total=total,
        tool_count=len(counts),
        tools=counts,
    )


BASE = Baseline(tokenizer="heuristic", total=1000, tools={"a": 600, "b": 400}, toolism_version="x")


# -------------------------------------------------------------------- budgets


@pytest.mark.parametrize(
    ("text", "expected"),
    [("10%", (10.0, None)), ("2.5%", (2.5, None)), ("500", (None, 500)), (" 0 ", (None, 0))],
)
def test_parse_increase(text: str, expected: tuple[float | None, int | None]) -> None:
    assert parse_increase(text) == expected


@pytest.mark.parametrize("text", ["ten", "-5", "-1%", "%", "1.5"])
def test_parse_increase_rejects(text: str) -> None:
    with pytest.raises(ValueError, match="invalid increase"):
        parse_increase(text)


def test_pct_budget_boundary_is_inclusive() -> None:
    assert run_check(report(1100, a=700, b=400), BASE, Budget(max_increase_pct=10)).ok
    result = run_check(report(1101, a=701, b=400), BASE, Budget(max_increase_pct=10))
    assert not result.ok
    assert result.violations == ("total grew by 101 tokens (+10.1%), over the allowed 10%",)


def test_abs_budget_boundary_is_inclusive() -> None:
    assert run_check(report(1500, a=1100, b=400), BASE, Budget(max_increase_abs=500)).ok
    result = run_check(report(1501, a=1101, b=400), BASE, Budget(max_increase_abs=500))
    assert result.violations == ("total grew by 501 tokens (+50.1%), over the allowed 500 tokens",)


def test_absolute_allowance_is_a_floor_for_percentages() -> None:
    both = Budget(max_increase_pct=10, max_increase_abs=300)
    # 25% growth is over 10% but within the 300-token floor
    assert run_check(report(1250, a=850, b=400), BASE, both).ok
    # on a large baseline the percentage is the larger allowance
    big = Baseline(tokenizer="heuristic", total=10_000, tools={"a": 10_000}, toolism_version="x")
    assert run_check(report(11_000, a=11_000), big, both).ok
    result = run_check(report(1301, a=901, b=400), BASE, both)
    assert result.violations == (
        "total grew by 301 tokens (+30.1%), over the allowed 10% or 300 tokens, "
        "whichever is larger",
    )


def test_decreases_always_pass() -> None:
    result = run_check(report(10, a=10), BASE, Budget(max_increase_pct=0, max_increase_abs=0))
    assert result.ok
    assert result.delta_total == -990


def test_caps_work_without_baseline_and_collect_all_violations() -> None:
    result = run_check(report(900, a=600, b=300), None, Budget(max_total=800, max_tool=250))
    assert not result.ok
    assert result.violations == (
        "total is 900 tokens, over the cap of 800",
        "tool 'a' is 600 tokens, over the per-tool cap of 250",
        "tool 'b' is 300 tokens, over the per-tool cap of 250",
    )
    assert result.delta_total is None
    assert result.deltas == ()


def test_zero_baseline_pct_growth() -> None:
    empty = Baseline(tokenizer="heuristic", total=0, tools={}, toolism_version="x")
    result = run_check(report(5, a=5), empty, Budget(max_increase_pct=10))
    assert result.violations == ("total grew by 5 tokens (new), over the allowed 10%",)


def test_deltas_list_added_removed_and_changed() -> None:
    result = run_check(report(1050, a=650, c=400), BASE, Budget())
    assert [(d.name, d.before, d.after, d.change) for d in result.deltas] == [
        ("b", 400, None, -400),
        ("c", None, 400, 400),
        ("a", 600, 650, 50),
    ]


def test_tokenizer_mismatch() -> None:
    other = TokenReport(
        tokenizer="tiktoken:o200k_base",
        approximate=True,
        total=5000,
        tool_count=1,
        tools=(ToolCount("a", 5000),),
    )
    with pytest.raises(BaselineError, match="baseline was measured with heuristic") as info:
        run_check(other, BASE, Budget(max_increase_pct=1))
    assert info.value.hint is not None
    result = run_check(other, BASE, Budget(max_increase_pct=1), allow_tokenizer_change=True)
    assert result.ok
    assert "growth budgets were not enforced" in result.notes[0]


# ------------------------------------------------------------------ baselines


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    path = tmp_path / ".toolism" / "baseline.json"
    saved = save_baseline(path, report(1000, b=400, a=600))
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["toolism_baseline"] == 1
    assert list(data["tools"]) == ["a", "b"]  # sorted for stable diffs
    loaded = load_baseline(path)
    assert loaded == saved
    assert loaded.total == 1000


def test_duplicate_tool_names_are_summed() -> None:
    dup = TokenReport(
        tokenizer="heuristic",
        approximate=True,
        total=30,
        tool_count=2,
        tools=(ToolCount("a", 10), ToolCount("a", 20)),
    )
    assert baseline_from_report(dup).tools == {"a": 30}
    assert "Duplicate tool names are summed per name: a." in run_check(dup, None, Budget()).notes[0]


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (None, "baseline not found"),
        ("{not json", "cannot read baseline"),
        ('{"toolism_baseline": 2}', "is not a toolism baseline"),
        ('{"toolism_baseline": 1, "tools": [], "total_tokens": 1, "tokenizer": "x"}', "malformed"),
        (
            '{"toolism_baseline": 1, "tools": {"a": "1"}, "total_tokens": 1, "tokenizer": "x"}',
            "malformed",
        ),
    ],
)
def test_load_baseline_errors(tmp_path: Path, content: str | None, message: str) -> None:
    path = tmp_path / "baseline.json"
    if content is not None:
        path.write_text(content, encoding="utf-8")
    with pytest.raises(BaselineError, match=message):
        load_baseline(path)


# ------------------------------------------------------------------ rendering


def test_render_check_formats() -> None:
    failed = run_check(report(1200, a=800, b=400), BASE, Budget(max_increase_pct=10))
    md = render_check(failed, "markdown")
    assert md.startswith("### ❌ toolism — tool token budget failed")
    assert "**Violations**" in md
    assert "| `a` | 600 | 800 | +200 |" in md
    assert "(baseline 1,000, +200, +20.0%)" in md
    table = render_check(failed, "table")
    assert "toolism check FAILED" in table
    assert "✗ total grew by 200 tokens" in table
    data = json.loads(render_check(failed, "json"))
    assert data["ok"] is False
    assert data["delta_tokens"] == 200
    assert data["tools"][0] == {"name": "a", "before": 600, "after": 800, "change": 200}

    passed = run_check(report(1000, a=600, b=400), BASE, Budget(max_increase_pct=10))
    assert render_check(passed, "markdown").startswith("### ✅ toolism — tool token budget passed")
    assert "Changed tools" not in render_check(passed, "table")
    assert "\x1b[" in render_check(passed, "table", color=True)
