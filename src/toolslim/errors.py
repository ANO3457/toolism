"""Exception hierarchy. Every error toolslim raises on purpose is a :class:`ToolslimError`."""

from __future__ import annotations


class ToolslimError(Exception):
    """Base class for all toolslim errors.

    ``hint`` is an optional one-line suggestion the CLI prints under the error.
    """

    def __init__(self, message: str, *, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint


class FormatError(ToolslimError):
    """Input is not valid JSON, has no tool list, or mixes tool formats."""


class TokenizerError(ToolslimError):
    """Unknown or malformed tokenizer spec."""


class TokenizerUnavailable(TokenizerError):
    """A known tokenizer that cannot be used here (missing package, offline vocabulary, no key)."""


class RuleError(ToolslimError):
    """Unknown rule, invalid option, rule registration problem or rule contract violation."""


class MissingExtraError(ToolslimError):
    """An optional dependency is not installed."""

    def __init__(self, feature: str, extra: str) -> None:
        super().__init__(
            f"{feature} needs an optional dependency that is not installed",
            hint=f"pip install 'toolslim[{extra}]'",
        )
        self.extra = extra


class LoaderError(ToolslimError):
    """An MCP server could not be started or did not list its tools."""


class BaselineError(ToolslimError):
    """A baseline file is missing, malformed or incompatible."""
