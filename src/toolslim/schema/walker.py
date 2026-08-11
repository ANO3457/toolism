"""Keyword-table-driven JSON Schema traversal (design C3, review R1).

Only *subschema positions* are visited. Instance data (``enum``, ``const``, ``default``,
``examples``), ``required`` lists and unknown/vendor keywords are never entered, so a property
named ``title`` is never confused with the ``title`` keyword and enum values are never rewritten.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

__all__ = [
    "SchemaPath",
    "defs_name",
    "iter_subschemas",
    "map_subschemas",
    "property_name",
]

SchemaPath = tuple[str | int, ...]

# A single subschema.
SINGLE_KEYWORDS = frozenset(
    {
        "additionalProperties",
        "not",
        "if",
        "then",
        "else",
        "contains",
        "propertyNames",
        "unevaluatedItems",
        "unevaluatedProperties",
        "additionalItems",
        "contentSchema",
    }
)
# An array of subschemas.
ARRAY_KEYWORDS = frozenset({"allOf", "anyOf", "oneOf", "prefixItems"})
# An object whose values are subschemas.
MAP_KEYWORDS = frozenset(
    {"properties", "patternProperties", "$defs", "definitions", "dependentSchemas"}
)
# ``items`` is a single subschema (object/bool) or, before 2020-12, an array of them.
# ``dependencies`` (draft <= 7) maps to a subschema *or* an array of property names.

_DEFS_KEYWORDS = ("$defs", "definitions")


def _is_schema(value: Any) -> bool:
    return isinstance(value, (dict, bool))


def _child_positions(node: dict[str, Any]) -> Iterator[tuple[SchemaPath, Any]]:
    """Yield ``(relative path, subschema)`` for every direct subschema of ``node``."""
    for key, value in node.items():
        if (key in SINGLE_KEYWORDS or key == "items") and _is_schema(value):
            yield (key,), value
        elif (key in ARRAY_KEYWORDS or key == "items") and isinstance(value, list):
            for index, item in enumerate(value):
                if _is_schema(item):
                    yield (key, index), item
        elif (key in MAP_KEYWORDS or key == "dependencies") and isinstance(value, dict):
            for name, item in value.items():
                if _is_schema(item):
                    yield (key, name), item


def iter_subschemas(
    schema: Any, path: SchemaPath = ()
) -> Iterator[tuple[SchemaPath, dict[str, Any]]]:
    """Pre-order iteration over every *object* subschema (boolean schemas are skipped)."""
    if not isinstance(schema, dict):
        return
    yield path, schema
    for rel, child in _child_positions(schema):
        yield from iter_subschemas(child, path + rel)


def map_subschemas(
    schema: Any, fn: Callable[[dict[str, Any], SchemaPath], Any], path: SchemaPath = ()
) -> Any:
    """Rebuild ``schema`` bottom-up, calling ``fn(node, path)`` on every object subschema.

    Children are rebuilt before their parent, so ``fn`` sees already-transformed children.
    ``fn`` receives a *new* dict it may modify and return, or it may return any JSON value
    (e.g. ``True``) to replace the node. The input is never mutated; values outside subschema
    positions are carried over by reference.
    """
    if not isinstance(schema, dict):
        return schema
    rebuilt: dict[str, Any] = {}
    for key, value in schema.items():
        if (key in SINGLE_KEYWORDS or key == "items") and _is_schema(value):
            rebuilt[key] = map_subschemas(value, fn, (*path, key))
        elif (key in ARRAY_KEYWORDS or key == "items") and isinstance(value, list):
            rebuilt[key] = [
                map_subschemas(item, fn, (*path, key, index)) if _is_schema(item) else item
                for index, item in enumerate(value)
            ]
        elif (key in MAP_KEYWORDS or key == "dependencies") and isinstance(value, dict):
            rebuilt[key] = {
                name: map_subschemas(item, fn, (*path, key, name)) if _is_schema(item) else item
                for name, item in value.items()
            }
        else:
            rebuilt[key] = value
    return fn(rebuilt, path)


def property_name(path: SchemaPath) -> str | None:
    """The property name if ``path`` points at ``properties/<name>``, else ``None``."""
    if len(path) >= 2 and path[-2] == "properties" and isinstance(path[-1], str):
        return path[-1]
    return None


def defs_name(path: SchemaPath) -> str | None:
    """The definition key if ``path`` points at ``$defs/<name>`` or ``definitions/<name>``."""
    if len(path) >= 2 and path[-2] in _DEFS_KEYWORDS and isinstance(path[-1], str):
        return path[-1]
    return None
