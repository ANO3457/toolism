"""``$ref`` / ``$defs`` analysis (design C3).

Only same-document pointers of the exact form ``#/$defs/<name>`` or ``#/definitions/<name>`` are
treated as definition references. Anything else is *foreign*; a foreign pointer that reaches inside
a definition (``#/$defs/A/properties/b``) *pins* that definition so it is never inlined or deleted.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import unquote

from toolslim.schema.dialect import Dialect, detect_dialect
from toolslim.schema.walker import SchemaPath, iter_subschemas

__all__ = [
    "DefRef",
    "DefUsage",
    "def_usage",
    "is_recursive",
    "iter_refs",
    "parse_def_ref",
    "uses_dynamic_scope",
]

DEF_CONTAINERS = ("$defs", "definitions")
_DYNAMIC_KEYWORDS = (
    "$anchor",
    "$dynamicRef",
    "$dynamicAnchor",
    "$recursiveRef",
    "$recursiveAnchor",
)


@dataclass(frozen=True, order=True)
class DefRef:
    """A root-level definition: ``container`` is ``$defs`` or ``definitions``."""

    container: str
    name: str

    @property
    def pointer(self) -> str:
        escaped = self.name.replace("~", "~0").replace("/", "~1")
        return f"#/{self.container}/{escaped}"


def _pointer_tokens(ref: str) -> list[str] | None:
    """Split a same-document JSON pointer ``#/a/b`` into unescaped tokens (RFC 6901)."""
    if not ref.startswith("#/"):
        return None
    tokens = unquote(ref[1:]).split("/")[1:]
    return [t.replace("~1", "/").replace("~0", "~") for t in tokens]


def parse_def_ref(ref: Any) -> DefRef | None:
    """``"#/$defs/Name"`` → ``DefRef("$defs", "Name")``; anything else → ``None``."""
    if not isinstance(ref, str):
        return None
    tokens = _pointer_tokens(ref)
    if tokens is None or len(tokens) != 2 or tokens[0] not in DEF_CONTAINERS:
        return None
    return DefRef(tokens[0], tokens[1])


def iter_refs(schema: Any) -> Iterator[tuple[SchemaPath, str]]:
    """Yield ``(path of the node holding $ref, ref string)`` for every ``$ref`` in subschemas."""
    for path, node in iter_subschemas(schema):
        ref = node.get("$ref")
        if isinstance(ref, str):
            yield path, ref


@dataclass
class DefUsage:
    """How root-level definitions are used inside one schema."""

    defs: dict[DefRef, Any] = field(default_factory=dict)
    counts: Counter[DefRef] = field(default_factory=Counter)
    sites: dict[DefRef, list[SchemaPath]] = field(default_factory=dict)
    pinned: set[DefRef] = field(default_factory=set)
    foreign: list[str] = field(default_factory=list)
    graph: dict[DefRef, set[DefRef]] = field(default_factory=dict)


def _owner(path: SchemaPath, defs: dict[DefRef, Any]) -> DefRef | None:
    if len(path) >= 2 and path[0] in DEF_CONTAINERS and isinstance(path[1], str):
        ref = DefRef(str(path[0]), path[1])
        if ref in defs:
            return ref
    return None


def def_usage(schema: Any) -> DefUsage:
    """Count exact references to each root-level definition and find pinned/foreign refs."""
    usage = DefUsage()
    if not isinstance(schema, dict):
        return usage
    for container in DEF_CONTAINERS:
        block = schema.get(container)
        if isinstance(block, dict):
            for name, value in block.items():
                usage.defs[DefRef(container, name)] = value
    usage.graph = {definition: set() for definition in usage.defs}

    for path, ref in iter_refs(schema):
        target = parse_def_ref(ref)
        if target is not None:
            usage.counts[target] += 1
            usage.sites.setdefault(target, []).append(path)
            owner = _owner(path, usage.defs)
            if owner is not None:
                usage.graph[owner].add(target)
            continue
        usage.foreign.append(ref)
        tokens = _pointer_tokens(ref)
        if tokens and len(tokens) >= 2 and tokens[0] in DEF_CONTAINERS:
            usage.pinned.add(DefRef(tokens[0], tokens[1]))
        elif tokens is not None and len(tokens) == 1 and tokens[0] in DEF_CONTAINERS:
            usage.pinned.update(d for d in usage.defs if d.container == tokens[0])
    return usage


def is_recursive(usage: DefUsage, target: DefRef) -> bool:
    """Whether ``target`` can reach itself through definition-to-definition references."""
    stack = list(usage.graph.get(target, ()))
    seen: set[DefRef] = set()
    while stack:
        current = stack.pop()
        if current == target:
            return True
        if current in seen:
            continue
        seen.add(current)
        stack.extend(usage.graph.get(current, ()))
    return False


def uses_dynamic_scope(schema: Any) -> bool:
    """Whether ref resolution could depend on anything but the root document.

    True for a nested ``$id`` (or draft-04 nested ``id``), anchors, and dynamic/recursive refs.
    A root-level ``$id`` alone is harmless for ``#/...`` pointers and is ignored.
    """
    draft4 = detect_dialect(schema) is Dialect.DRAFT4
    for path, node in iter_subschemas(schema):
        if any(key in node for key in _DYNAMIC_KEYWORDS):
            return True
        if path and ("$id" in node or (draft4 and isinstance(node.get("id"), str))):
            return True
    return False
