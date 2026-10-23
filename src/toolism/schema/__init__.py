"""JSON Schema utilities: keyword-aware traversal, dialects and ``$ref`` analysis (design C3)."""

from __future__ import annotations

from toolism.schema.dialect import Dialect, detect_dialect, known_dialect, ref_siblings_apply
from toolism.schema.refs import (
    DefRef,
    DefUsage,
    def_usage,
    is_recursive,
    iter_refs,
    parse_def_ref,
    uses_dynamic_scope,
)
from toolism.schema.walker import (
    SchemaPath,
    defs_name,
    iter_subschemas,
    map_subschemas,
    property_name,
)

__all__ = [
    "DefRef",
    "DefUsage",
    "Dialect",
    "SchemaPath",
    "def_usage",
    "defs_name",
    "detect_dialect",
    "is_recursive",
    "iter_refs",
    "iter_subschemas",
    "known_dialect",
    "map_subschemas",
    "parse_def_ref",
    "property_name",
    "ref_siblings_apply",
    "uses_dynamic_scope",
]
