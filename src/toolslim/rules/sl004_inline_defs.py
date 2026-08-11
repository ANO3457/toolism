"""SL004 inline-defs — inline single-use ``$defs`` and delete unused ones."""

from __future__ import annotations

import copy
from typing import Any

from toolslim.models import ToolDef
from toolslim.rules.base import RuleContext, Safety, ToolRule
from toolslim.rules.registry import register_rule
from toolslim.schema import (
    DefRef,
    DefUsage,
    SchemaPath,
    def_usage,
    is_recursive,
    iter_refs,
    ref_siblings_apply,
    uses_dynamic_scope,
)

# Keywords that never affect validation: a collision on these is resolved in favour of the
# reference site (its description is more specific than the shared definition's).
_ANNOTATIONS = frozenset(
    {
        "title",
        "description",
        "default",
        "examples",
        "deprecated",
        "readOnly",
        "writeOnly",
        "$comment",
    }
)
_UNMOVABLE = frozenset({"$schema", "$id"})
_MAX_STEPS = 1000


def _get(schema: Any, path: SchemaPath) -> Any:
    node = schema
    for segment in path:
        node = node[segment]
    return node


def _remove_def(schema: dict[str, Any], target: DefRef) -> None:
    container = schema[target.container]
    del container[target.name]
    if not container:
        del schema[target.container]


@register_rule
class InlineDefs(ToolRule):
    """Generators put every nested model in ``$defs`` and reference it, even when it is used once.
    Inlining removes the ``$defs`` wrapper and the ``$ref`` string. Conservative by design
    (architecture review R2): never inlines recursive, pinned or multi-use definitions, never when
    other JSON pointers exist, never ``$ref`` siblings under draft <= 7, and never when keywords
    other than annotations would collide."""

    id = "SL004"
    name = "inline-defs"
    summary = "Inline $defs used exactly once and delete unused $defs"
    safety = Safety.SAFE

    def apply_tool(self, tool: ToolDef, ctx: RuleContext) -> ToolDef:
        schema = tool.input_schema
        if not isinstance(schema, dict) or uses_dynamic_scope(schema):
            return tool
        if "$id" in schema and any(not ref.startswith("#") for _, ref in iter_refs(schema)):
            return tool
        working: dict[str, Any] = copy.deepcopy(schema)
        changed = False
        for _ in range(_MAX_STEPS):
            usage = def_usage(working)
            if not (self._delete_unused(working, usage) or self._inline_one(working, usage, ctx)):
                break
            changed = True
        return tool.replace(input_schema=working) if changed else tool

    @staticmethod
    def _delete_unused(schema: dict[str, Any], usage: DefUsage) -> bool:
        unused = [d for d in usage.defs if usage.counts[d] == 0 and d not in usage.pinned]
        for target in unused:
            _remove_def(schema, target)
        return bool(unused)

    @staticmethod
    def _inline_one(schema: dict[str, Any], usage: DefUsage, ctx: RuleContext) -> bool:
        if usage.foreign:
            return False
        siblings_apply = ref_siblings_apply(ctx.dialect)
        for target in sorted(usage.defs):
            body = usage.defs[target]
            if (
                usage.counts[target] != 1
                or target in usage.pinned
                or not isinstance(body, dict)
                or _UNMOVABLE & set(body)
                or is_recursive(usage, target)
            ):
                continue
            site_path = usage.sites[target][0]
            site = _get(schema, site_path)
            siblings = {k: v for k, v in site.items() if k != "$ref"}
            if siblings and not siblings_apply:
                continue
            if any(key not in _ANNOTATIONS for key in set(siblings) & set(body)):
                continue
            merged: dict[str, Any] = {}
            for key, value in site.items():
                if key == "$ref":
                    merged.update({k: v for k, v in body.items() if k not in siblings})
                else:
                    merged[key] = value
            if site_path:
                _get(schema, site_path[:-1])[site_path[-1]] = merged
            else:
                schema.clear()
                schema.update(merged)
            _remove_def(schema, target)
            return True
        return False
