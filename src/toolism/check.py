"""Baseline files and token budgets for CI (design C10).

The check measures what you ship (it does not slim first) and compares it with a committed
baseline: total growth (percentage and/or absolute), an absolute total cap, and a per-tool cap.
"""

from __future__ import annotations

import io
import json
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from rich.console import Console
from rich.table import Table
from rich.text import Text

from toolism.__about__ import __version__
from toolism.errors import BaselineError
from toolism.measurement import TokenReport

__all__ = [
    "BASELINE_VERSION",
    "Baseline",
    "Budget",
    "CheckResult",
    "ToolDelta",
    "baseline_from_report",
    "load_baseline",
    "parse_increase",
    "render_check",
    "run_check",
    "save_baseline",
]

BASELINE_VERSION = 1
TOP_N = 25


@dataclass(frozen=True)
class Baseline:
    tokenizer: str
    total: int
    tools: dict[str, int]
    toolism_version: str
    version: int = BASELINE_VERSION


@dataclass(frozen=True)
class Budget:
    max_increase_pct: float | None = None
    max_increase_abs: int | None = None
    max_total: int | None = None
    max_tool: int | None = None


@dataclass(frozen=True)
class ToolDelta:
    name: str
    before: int | None  # None: tool was added
    after: int | None  # None: tool was removed

    @property
    def change(self) -> int:
        return (self.after or 0) - (self.before or 0)


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    violations: tuple[str, ...]
    current: TokenReport
    baseline: Baseline | None
    delta_total: int | None
    deltas: tuple[ToolDelta, ...]
    notes: tuple[str, ...] = ()


def _per_tool(report: TokenReport) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for tool in report.tools:
        totals[tool.name] += tool.tokens
    return dict(totals)


def baseline_from_report(report: TokenReport) -> Baseline:
    return Baseline(
        tokenizer=report.tokenizer,
        total=report.total,
        tools=dict(sorted(_per_tool(report).items())),
        toolism_version=__version__,
    )


def save_baseline(path: str | os.PathLike[str], report: TokenReport) -> Baseline:
    baseline = baseline_from_report(report)
    payload = {
        "toolism_baseline": BASELINE_VERSION,
        "toolism_version": baseline.toolism_version,
        "tokenizer": baseline.tokenizer,
        "total_tokens": baseline.total,
        "tools": baseline.tools,
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return baseline


def load_baseline(path: str | os.PathLike[str]) -> Baseline:
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise BaselineError(
            f"baseline not found: {source}", hint="create it with --update-baseline"
        ) from None
    except (OSError, ValueError) as exc:
        raise BaselineError(f"cannot read baseline {source}: {exc}") from exc
    if not isinstance(data, dict) or data.get("toolism_baseline") != BASELINE_VERSION:
        raise BaselineError(
            f"{source} is not a toolism baseline (version {BASELINE_VERSION})",
            hint="regenerate it with --update-baseline",
        )
    tools = data.get("tools")
    total = data.get("total_tokens")
    tokenizer = data.get("tokenizer")
    if (
        not isinstance(tools, dict)
        or not all(isinstance(k, str) and isinstance(v, int) for k, v in tools.items())
        or not isinstance(total, int)
        or not isinstance(tokenizer, str)
    ):
        raise BaselineError(f"{source} is malformed", hint="regenerate it with --update-baseline")
    return Baseline(
        tokenizer=tokenizer,
        total=total,
        tools=dict(tools),
        toolism_version=str(data.get("toolism_version", "unknown")),
    )


def parse_increase(text: str) -> tuple[float | None, int | None]:
    """``"10%"`` → ``(10.0, None)``; ``"500"`` → ``(None, 500)``. Raises ``ValueError``."""
    value = text.strip()
    try:
        if value.endswith("%"):
            pct = float(value[:-1])
            if pct < 0:
                raise ValueError
            return pct, None
        absolute = int(value)
        if absolute < 0:
            raise ValueError
        return None, absolute
    except ValueError:
        raise ValueError(
            f"invalid increase {text!r}: use a percentage like 10% or tokens like 500"
        ) from None


def _deltas(baseline: Baseline, report: TokenReport) -> tuple[ToolDelta, ...]:
    now = _per_tool(report)
    names = sorted(set(baseline.tools) | set(now))
    deltas = [
        ToolDelta(name, baseline.tools.get(name), now.get(name))
        for name in names
        if baseline.tools.get(name) != now.get(name)
    ]
    return tuple(sorted(deltas, key=lambda d: (-abs(d.change), d.name)))


def _growth_violation(delta: int, base_total: int, budget: Budget) -> str | None:
    """Growth is allowed up to the *larger* of the percentage and absolute allowances.

    The absolute allowance is a floor for small tool sets, where 10% of 40 tokens is noise.
    """
    allowances: list[float] = []
    labels: list[str] = []
    if budget.max_increase_pct is not None:
        allowances.append(base_total * budget.max_increase_pct / 100.0)
        labels.append(f"{budget.max_increase_pct:g}%")
    if budget.max_increase_abs is not None:
        allowances.append(float(budget.max_increase_abs))
        labels.append(f"{budget.max_increase_abs:,} tokens")
    if not allowances or delta <= max(allowances):
        return None
    actual = f"+{100.0 * delta / base_total:.1f}%" if base_total else "new"
    allowed = " or ".join(labels) + (", whichever is larger" if len(labels) > 1 else "")
    return f"total grew by {delta:,} tokens ({actual}), over the allowed {allowed}"


def run_check(
    report: TokenReport,
    baseline: Baseline | None,
    budget: Budget,
    *,
    allow_tokenizer_change: bool = False,
) -> CheckResult:
    """Compare ``report`` with ``baseline`` under ``budget``. Collects every violation."""
    violations: list[str] = []
    notes: list[str] = []
    enforce_growth = baseline is not None
    if baseline is not None and baseline.tokenizer != report.tokenizer:
        if not allow_tokenizer_change:
            raise BaselineError(
                f"baseline was measured with {baseline.tokenizer} but this run uses "
                f"{report.tokenizer}",
                hint="use the same --tokenizer, or pass --allow-tokenizer-change and update "
                "the baseline",
            )
        enforce_growth = False
        notes.append(
            f"Tokenizer changed ({baseline.tokenizer} → {report.tokenizer}); "
            "growth budgets were not enforced. Update the baseline."
        )

    names = [tool.name for tool in report.tools]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        notes.append(
            f"Duplicate tool names are summed per name: {', '.join(duplicates)}. "
            "Most clients reject duplicate names."
        )

    delta_total = report.total - baseline.total if baseline is not None else None
    if enforce_growth and baseline is not None and delta_total is not None and delta_total > 0:
        violation = _growth_violation(delta_total, baseline.total, budget)
        if violation:
            violations.append(violation)
    if budget.max_total is not None and report.total > budget.max_total:
        violations.append(f"total is {report.total:,} tokens, over the cap of {budget.max_total:,}")
    if budget.max_tool is not None:
        for tool in sorted(report.tools, key=lambda t: (-t.tokens, t.name)):
            if tool.tokens > budget.max_tool:
                violations.append(
                    f"tool {tool.name!r} is {tool.tokens:,} tokens, over the per-tool cap of "
                    f"{budget.max_tool:,}"
                )
    return CheckResult(
        ok=not violations,
        violations=tuple(violations),
        current=report,
        baseline=baseline,
        delta_total=delta_total,
        deltas=_deltas(baseline, report) if baseline is not None else (),
        notes=tuple(notes),
    )


# ------------------------------------------------------------------ rendering


def _fmt(value: int | None) -> str:
    return "—" if value is None else f"{value:,}"


def _change(value: int) -> str:
    return f"+{value:,}" if value > 0 else f"−{-value:,}" if value < 0 else "0"


def _summary(result: CheckResult) -> str:
    report, baseline = result.current, result.baseline
    line = f"Total: {report.total:,} tokens across {report.tool_count} tools"
    if baseline is not None and result.delta_total is not None:
        pct = 100.0 * result.delta_total / baseline.total if baseline.total else 0.0
        signed = f"{pct:+.1f}%".replace("-", "−")
        line += f" (baseline {baseline.total:,}, {_change(result.delta_total)}, {signed})"
    approx = " (approximate)" if report.approximate else ""
    return f"{line} — {report.tokenizer}{approx}"


def _check_dict(result: CheckResult) -> dict[str, Any]:
    return {
        "toolism_report": 1,
        "kind": "check",
        "ok": result.ok,
        "violations": list(result.violations),
        "tokenizer": result.current.tokenizer,
        "total_tokens": result.current.total,
        "baseline_tokens": result.baseline.total if result.baseline else None,
        "delta_tokens": result.delta_total,
        "tools": [
            {"name": d.name, "before": d.before, "after": d.after, "change": d.change}
            for d in result.deltas
        ],
        "notes": list(result.notes),
    }


def render_check(
    result: CheckResult,
    fmt: Literal["table", "markdown", "json"] = "table",
    *,
    width: int = 100,
    color: bool = False,
) -> str:
    if fmt == "json":
        return json.dumps(_check_dict(result), indent=2, ensure_ascii=False) + "\n"
    status = "passed" if result.ok else "failed"
    shown = result.deltas[:TOP_N]
    if fmt == "markdown":
        icon = "✅" if result.ok else "❌"
        parts = [f"### {icon} toolism — tool token budget {status}", "", _summary(result), ""]
        if result.violations:
            parts += ["**Violations**", "", *[f"- {v}" for v in result.violations], ""]
        if shown:
            parts += [
                "| Tool | Baseline | Now | Change |",
                "| --- | ---: | ---: | ---: |",
                *[
                    f"| `{d.name}` | {_fmt(d.before)} | {_fmt(d.after)} | {_change(d.change)} |"
                    for d in shown
                ],
                "",
            ]
        parts += list(result.notes)
        return "\n".join(parts).rstrip() + "\n"

    headline = Text("toolism check ")
    headline.append(status.upper(), style="bold green" if result.ok else "bold red")
    renderables: list[Any] = [headline, Text(_summary(result))]
    renderables += [Text(f"  ✗ {v}", style="red") for v in result.violations]
    if shown:
        table = Table(title="Changed tools", title_justify="left")
        table.add_column("Tool")
        for column in ("Baseline", "Now", "Change"):
            table.add_column(column, justify="right")
        for d in shown:
            table.add_row(d.name, _fmt(d.before), _fmt(d.after), _change(d.change))
        renderables.append(table)
    renderables += [Text(note) for note in result.notes]
    buffer = io.StringIO()
    console = Console(
        file=buffer,
        width=width,
        color_system="standard" if color else None,
        force_terminal=color,
        highlight=False,
    )
    for item in renderables:
        console.print(item)
    return buffer.getvalue()
