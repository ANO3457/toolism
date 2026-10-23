"""A dependency-free, deterministic token estimator (design C4).

It splits text roughly the way GPT-style pre-tokenizers do and charges each piece a small fixed
cost. It is not a real tokenizer: use it offline, or as the cheap attribution tokenizer. The
benchmark publishes its error against ``o200k_base`` (bench/RESULTS.md).
"""

from __future__ import annotations

import math
import re

from toolism.tokenizers.base import TextTokenizer

__all__ = ["HeuristicTokenizer"]

# camelCase / PascalCase / ACRONYM words, other-script letter runs, digit groups,
# underscores, whitespace runs, punctuation runs.
_PIECES = re.compile(
    r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|[^\W\d_]+|\d{1,3}|_+|\s+|[^\w\s]+",
    re.UNICODE,
)

WORD_CHARS = 10
"""ASCII letters per token for long words (most words up to this length are one token)."""
OTHER_SCRIPT_CHARS = 1.5
"""Characters per token for non-ASCII letter runs (CJK, Cyrillic, ...)."""
PUNCT_CHARS = 4.0
"""Characters per token in punctuation runs (``":"``, ``","`` and ``{"`` are single tokens)."""


class HeuristicTokenizer(TextTokenizer):
    """Offline approximation of a modern BPE tokenizer."""

    name = "heuristic"
    approximate = True
    local = True

    def count_text(self, text: str) -> int:
        total = 0
        for match in _PIECES.finditer(text):
            piece = match.group()
            first = piece[0]
            if first.isascii() and first.isalpha():
                total += 1 + (len(piece) - 1) // WORD_CHARS
            elif first.isalpha():
                total += math.ceil(len(piece) / OTHER_SCRIPT_CHARS)
            elif first.isdigit():
                total += 1
            elif first == "_":
                continue  # merges into the neighbouring word
            elif first.isspace():
                if piece != " ":
                    total += 1  # newlines, indentation (a single space joins the next word)
            else:
                total += math.ceil(len(piece) / PUNCT_CHARS)
        return total
