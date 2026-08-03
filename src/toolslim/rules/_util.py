"""Small helpers shared by rules. Not a rule module (its name does not match ``slNNN_*``)."""

from __future__ import annotations

import re

__all__ = ["content_words", "norm"]

_NON_ALNUM = re.compile(r"[^0-9a-z]")
_CAMEL_LOWER_UPPER = re.compile(r"([a-z0-9])([A-Z])")
_CAMEL_ACRONYM = re.compile(r"([A-Z]+)([A-Z][a-z])")
_POSSESSIVE = re.compile(r"'s\b")
_WORDS = re.compile(r"[A-Za-z]+|[0-9]+")

STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "for",
        "to",
        "this",
        "that",
        "is",
        "value",
        "field",
        "param",
        "parameter",
        "argument",
        "arg",
        "property",
        "given",
        "specified",
        "input",
    }
)


def norm(text: str) -> str:
    """Lowercase and keep only ASCII letters and digits: ``"User Id"`` → ``"userid"``."""
    return _NON_ALNUM.sub("", text.lower())


def content_words(text: str) -> frozenset[str]:
    """Lowercased words of ``text`` with snake/kebab/camel case split and stop-words removed."""
    text = _POSSESSIVE.sub("", text)
    text = _CAMEL_ACRONYM.sub(r"\1 \2", _CAMEL_LOWER_UPPER.sub(r"\1 \2", text))
    return frozenset(word.lower() for word in _WORDS.findall(text)) - STOP_WORDS
