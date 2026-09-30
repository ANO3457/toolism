from __future__ import annotations

import functools

import pytest


@functools.cache
def tiktoken_available() -> bool:
    """Whether the o200k_base vocabulary loads here (needs network or a pre-seeded cache)."""
    try:
        import tiktoken

        tiktoken.get_encoding("o200k_base")
    except Exception:
        return False
    return True


requires_tiktoken = pytest.mark.skipif(
    not tiktoken_available(), reason="tiktoken vocabulary not available (offline)"
)
