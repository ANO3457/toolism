"""SL002 nullable-anyof — ``anyOf: [{type: X}, {type: null}]`` → ``type: [X, "null"]``."""

from __future__ import annotations

from typing import Any

from toolslim.rules.base import RuleContext, Safety, SchemaRule
from toolslim.rules.registry import register_rule
from toolslim.schema import SchemaPath

_OVERLAPPING = {frozenset({"integer", "number"})}


def _branch_types(branch: Any) -> list[str] | None:
    """Types of a branch that is exactly ``{"type": ...}``, else ``None``."""
    if not isinstance(branch, dict) or set(branch) != {"type"}:
        return None
    value = branch["type"]
    types = [value] if isinstance(value, str) else value
    if not isinstance(types, list) or not types or not all(isinstance(t, str) for t in types):
        return None
    return types


def _overlap(a: list[str], b: list[str]) -> bool:
    return any(x == y or frozenset({x, y}) in _OVERLAPPING for x in a for y in b)


@register_rule
class NullableAnyOf(SchemaRule):
    """``Optional[X]`` in Pydantic becomes ``anyOf`` of two one-keyword branches. A ``type`` array
    accepts exactly the same instances and is shorter. For ``oneOf`` the rewrite is only equivalent
    when no instance can match two branches, so overlapping types (``integer``/``number``) are left
    alone. Note: rewriting to plain ``X`` would reject an explicit ``null`` — never do that."""

    id = "SL002"
    name = "nullable-anyof"
    summary = "Rewrite anyOf/oneOf of bare {type} branches as a type array"
    safety = Safety.SAFE

    def transform(self, node: dict[str, Any], path: SchemaPath, ctx: RuleContext) -> Any:
        if ("anyOf" in node) == ("oneOf" in node) or "type" in node:
            return node
        key = "anyOf" if "anyOf" in node else "oneOf"
        branches = node[key]
        if not isinstance(branches, list) or not branches:
            return node
        per_branch: list[list[str]] = []
        for branch in branches:
            types = _branch_types(branch)
            if types is None:
                return node
            if key == "oneOf" and any(_overlap(types, seen) for seen in per_branch):
                return node
            per_branch.append(types)
        merged: list[str] = []
        for types in per_branch:
            merged.extend(t for t in types if t not in merged)
        rewritten: dict[str, Any] = {}
        for name, value in node.items():
            if name == key:
                rewritten["type"] = merged[0] if len(merged) == 1 else merged
            else:
                rewritten[name] = value
        return rewritten
