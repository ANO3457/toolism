"""OpenAI's tiktoken encodings (design C4). Imported lazily."""

from __future__ import annotations

from typing import Any

from toolslim.errors import TokenizerUnavailable
from toolslim.tokenizers.base import TextTokenizer

__all__ = ["TiktokenTokenizer"]

_OFFLINE_HINT = (
    "use '--tokenizer heuristic', or pre-seed the vocabulary and set TIKTOKEN_CACHE_DIR "
    "(see https://github.com/openai/tiktoken)"
)


class TiktokenTokenizer(TextTokenizer):
    """Counts with a tiktoken encoding such as ``o200k_base`` (GPT-4o / GPT-5 family)."""

    approximate = True
    local = True

    def __init__(self, encoding: str = "o200k_base") -> None:
        super().__init__()
        self.encoding_name = encoding
        self.name = f"tiktoken:{encoding}"
        self._encoding = self._load(encoding)

    @staticmethod
    def _load(encoding: str) -> Any:
        try:
            import tiktoken
        except ImportError as exc:  # pragma: no cover - tiktoken is a core dependency
            raise TokenizerUnavailable(
                "the tiktoken package is not installed", hint="pip install tiktoken"
            ) from exc
        try:
            return tiktoken.get_encoding(encoding)
        except ValueError as exc:
            raise TokenizerUnavailable(f"unknown tiktoken encoding {encoding!r}") from exc
        except Exception as exc:  # network / proxy / cache errors while fetching the vocabulary
            raise TokenizerUnavailable(
                f"could not load the tiktoken vocabulary for {encoding!r}: {exc}",
                hint=_OFFLINE_HINT,
            ) from exc

    def count_text(self, text: str) -> int:
        return len(self._encoding.encode(text, disallowed_special=()))
