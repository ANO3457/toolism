"""SL009 schema-uri — drop the root ``$schema`` URI when the schema means the same without it."""

from __future__ import annotations

from typing import Any

from toolslim.models import ToolDef
from toolslim.rules.base import RuleContext, Safety, ToolRule
from toolslim.rules.registry import register_rule
from toolslim.schema import Dialect, iter_subschemas, known_dialect

_DIALECT_SENSITIVE = frozenset(
    {"additionalItems", "dependencies", "$recursiveRef", "$recursiveAnchor"}
)
# Keywords that may sit next to $ref without changing validation in any dialect.
_REF_NEUTRAL_SIBLINGS = frozenset(
    {
        "$ref",
        "$schema",
        "$defs",
        "definitions",
        "$comment",
        "title",
        "description",
        "default",
        "examples",
        "deprecated",
        "readOnly",
        "writeOnly",
    }
)


def _dialect_invariant(schema: dict[str, Any]) -> bool:
    """Whether ``schema`` validates identically under its declared dialect and 2020-12."""
    for _, node in iter_subschemas(schema):
        if _DIALECT_SENSITIVE & set(node):
            return False
        if isinstance(node.get("items"), list):
            return False
        if isinstance(node.get("exclusiveMinimum"), bool) or isinstance(
            node.get("exclusiveMaximum"), bool
        ):
            return False
        if "$ref" in node and not set(node) <= _REF_NEUTRAL_SIBLINGS:
            return False
    return True


@register_rule
class SchemaUri(ToolRule):
    """zod-to-json-schema and many MCP servers add ``"$schema": "http://json-schema.org/draft-07/
    schema#"`` to every tool — 10-15 tokens each that the model has no use for. Without
    ``$schema`` validators assume 2020-12, so the URI is only dropped when nothing in the schema
    behaves differently between the declared draft and 2020-12. Draft-04 is never touched."""

    id = "SL009"
    name = "schema-uri"
    summary = "Drop the root $schema URI when the schema is dialect-invariant"
    safety = Safety.SAFE

    def apply_tool(self, tool: ToolDef, ctx: RuleContext) -> ToolDef:
        schema = tool.input_schema
        if not isinstance(schema, dict) or "$schema" not in schema:
            return tool
        dialect = known_dialect(schema)
        if dialect is None or dialect is Dialect.DRAFT4 or not _dialect_invariant(schema):
            return tool
        return tool.replace(input_schema={k: v for k, v in schema.items() if k != "$schema"})
