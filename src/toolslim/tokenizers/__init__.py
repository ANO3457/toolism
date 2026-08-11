"""Tokenizers and the ``get_tokenizer`` factory (design C4)."""

from __future__ import annotations

import os

from toolslim.errors import TokenizerError
from toolslim.tokenizers.anthropic_tokenizer import AnthropicTokenizer
from toolslim.tokenizers.base import TextTokenizer, Tokenizer
from toolslim.tokenizers.heuristic import HeuristicTokenizer
from toolslim.tokenizers.tiktoken_tokenizer import TiktokenTokenizer

__all__ = [
    "DEFAULT_TOKENIZER",
    "ENV_VAR",
    "AnthropicTokenizer",
    "HeuristicTokenizer",
    "TextTokenizer",
    "TiktokenTokenizer",
    "Tokenizer",
    "get_tokenizer",
]

DEFAULT_TOKENIZER = "tiktoken:o200k_base"
ENV_VAR = "TOOLSLIM_TOKENIZER"
_FORMS = "use 'heuristic', 'tiktoken:<encoding>' or 'anthropic:<model>'"


def get_tokenizer(spec: str | Tokenizer | None = None) -> Tokenizer:
    """Resolve a tokenizer.

    ``None`` means ``$TOOLSLIM_TOKENIZER`` if set, otherwise ``tiktoken:o200k_base``.
    A :class:`Tokenizer` instance is returned unchanged.
    """
    if spec is not None and not isinstance(spec, str):
        return spec
    text = (spec or os.environ.get(ENV_VAR) or DEFAULT_TOKENIZER).strip()
    if text == "heuristic":
        return HeuristicTokenizer()
    kind, _, argument = text.partition(":")
    if kind == "tiktoken":
        return TiktokenTokenizer(argument or "o200k_base")
    if kind == "anthropic":
        if not argument:
            raise TokenizerError(
                "the anthropic tokenizer needs a model", hint="e.g. anthropic:claude-sonnet-5"
            )
        return AnthropicTokenizer(argument)
    raise TokenizerError(f"unknown tokenizer {text!r}", hint=_FORMS)
