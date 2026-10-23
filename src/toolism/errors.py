"""Exception hierarchy. Every error toolism raises on purpose is a :class:`ToolismError`."""

from __future__ import annotations


class ToolismError(Exception):
    """Base class for all toolism errors.

    ``hint`` is an optional one-line suggestion the CLI prints under the error.
    """

    def __init__(self, message: str, *, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint


class FormatError(ToolismError):
    """Input is not valid JSON, has no tool list, or mixes tool formats."""


class TokenizerError(ToolismError):
    """Unknown or malformed tokenizer spec."""


class TokenizerUnavailable(TokenizerError):
    """A known tokenizer that cannot be used here (missing package, offline vocabulary, no key)."""


class RuleError(ToolismError):
    """Unknown rule, invalid option, rule registration problem or rule contract violation."""


class MissingExtraError(ToolismError):
    """An optional dependency is not installed."""

    def __init__(self, feature: str, extra: str) -> None:
        super().__init__(
            f"{feature} needs an optional dependency that is not installed",
            hint=f"pip install 'toolism[{extra}]'",
        )
        self.extra = extra


class LoaderError(ToolismError):
    """An MCP server could not be started or did not list its tools."""


class BaselineError(ToolismError):
    """A baseline file is missing, malformed or incompatible."""
