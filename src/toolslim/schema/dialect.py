"""JSON Schema dialect detection (design C3, review R2)."""

from __future__ import annotations

from enum import IntEnum
from typing import Any

__all__ = ["Dialect", "detect_dialect", "known_dialect", "ref_siblings_apply"]


class Dialect(IntEnum):
    """JSON Schema drafts, ordered by age."""

    DRAFT4 = 4
    DRAFT6 = 6
    DRAFT7 = 7
    DRAFT2019_09 = 2019
    DRAFT2020_12 = 2020


_MARKERS: tuple[tuple[str, Dialect], ...] = (
    ("draft-04", Dialect.DRAFT4),
    ("draft-06", Dialect.DRAFT6),
    ("draft-07", Dialect.DRAFT7),
    ("2019-09", Dialect.DRAFT2019_09),
    ("2020-12", Dialect.DRAFT2020_12),
)

DEFAULT_DIALECT = Dialect.DRAFT2020_12


def known_dialect(schema: Any) -> Dialect | None:
    """The dialect named by ``$schema`` if it is a known JSON Schema draft URI, else ``None``."""
    if not isinstance(schema, dict):
        return None
    uri = schema.get("$schema")
    if not isinstance(uri, str) or "json-schema.org" not in uri:
        return None
    for marker, dialect in _MARKERS:
        if marker in uri:
            return dialect
    return None


def detect_dialect(schema: Any) -> Dialect:
    """The dialect a validator would use: ``$schema`` if known, otherwise draft 2020-12."""
    return known_dialect(schema) or DEFAULT_DIALECT


def ref_siblings_apply(dialect: Dialect) -> bool:
    """Whether keywords next to ``$ref`` are evaluated (2019-09+) or ignored (draft <= 7)."""
    return dialect >= Dialect.DRAFT2019_09
