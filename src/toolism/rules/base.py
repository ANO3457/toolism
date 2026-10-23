"""The rule contract (design C5).

Three base classes, from most to least general:

* :class:`Rule` — transforms the whole tuple of tools (needed for tool-order rules).
* :class:`ToolRule` — rewrites one tool at a time; opaque tools are skipped automatically.
* :class:`SchemaRule` — rewrites one subschema at a time via the keyword-aware walker.

Rules must be pure: never mutate inputs, return the same object when there is nothing to do.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, ClassVar

from toolism.errors import RuleError
from toolism.models import ToolDef
from toolism.schema import Dialect, SchemaPath, detect_dialect, map_subschemas

__all__ = ["OptionSpec", "Rule", "RuleContext", "Safety", "SchemaRule", "ToolRule"]


class Safety(IntEnum):
    """How much a rule is allowed to change. Levels are cumulative."""

    SAFE = 0
    """Validation-equivalent, and only provably redundant information is removed."""
    LOSSY_ANNOTATIONS = 1
    """Validation-equivalent, but may drop non-redundant annotation text (e.g. examples)."""
    CHANGES_VALIDATION = 2
    """May change which tool calls validate. Reserved; no shipped rule uses it."""

    @property
    def label(self) -> str:
        return _LABELS[self]

    @classmethod
    def parse(cls, value: str | Safety) -> Safety:
        """Accept a :class:`Safety`, a CLI label (``safe``, ``annotations``, ``validation``)
        or an enum name."""
        if isinstance(value, Safety):
            return value
        text = value.strip().lower()
        for level, label in _LABELS.items():
            if text in (label, level.name.lower()):
                return level
        choices = ", ".join(_LABELS.values())
        raise RuleError(f"unknown safety level {value!r}", hint=f"choose one of: {choices}")


_LABELS = {
    Safety.SAFE: "safe",
    Safety.LOSSY_ANNOTATIONS: "annotations",
    Safety.CHANGES_VALIDATION: "validation",
}


@dataclass(frozen=True)
class OptionSpec:
    """One configurable option of a rule."""

    type: type
    default: Any
    help: str


@dataclass(frozen=True)
class RuleContext:
    """Everything a rule may know about the tool it is rewriting."""

    tool: ToolDef
    dialect: Dialect
    strict: bool
    options: Mapping[str, Any] = field(default_factory=dict)


class Rule(ABC):
    """Base class for every rule. Subclasses set the class attributes and are registered with
    :func:`toolism.rules.registry.register_rule`."""

    id: ClassVar[str]
    """``SL`` + 3 digits. The hundreds digit encodes the safety level (``SL0xx`` = safe)."""
    name: ClassVar[str]
    """kebab-case, unique."""
    summary: ClassVar[str]
    """One line shown by ``toolism rules``."""
    safety: ClassVar[Safety]
    default_enabled: ClassVar[bool] = True
    reorders: ClassVar[bool] = False
    """``True`` only for rules that change tool order (they must not change tool content)."""
    option_specs: ClassVar[Mapping[str, OptionSpec]] = {}

    @abstractmethod
    def apply(self, tools: tuple[ToolDef, ...], options: Mapping[str, Any]) -> tuple[ToolDef, ...]:
        """Return the rewritten tools (same length; same order unless :attr:`reorders`)."""

    def __repr__(self) -> str:
        return f"<{self.id} {self.name}>"


class ToolRule(Rule):
    """A rule that rewrites tools one at a time. Opaque tools are passed through."""

    def apply(self, tools: tuple[ToolDef, ...], options: Mapping[str, Any]) -> tuple[ToolDef, ...]:
        rewritten: list[ToolDef] = []
        for tool in tools:
            if tool.opaque:
                rewritten.append(tool)
                continue
            context = RuleContext(
                tool=tool,
                dialect=detect_dialect(tool.input_schema),
                strict=tool.strict,
                options=options,
            )
            rewritten.append(self.apply_tool(tool, context))
        return tuple(rewritten)

    @abstractmethod
    def apply_tool(self, tool: ToolDef, ctx: RuleContext) -> ToolDef:
        """Return the rewritten tool, or ``tool`` itself when nothing changes."""


class SchemaRule(ToolRule):
    """A rule that rewrites individual subschemas of a tool's input schema."""

    def apply_tool(self, tool: ToolDef, ctx: RuleContext) -> ToolDef:
        if tool.input_schema is None:
            return tool
        new_schema = map_subschemas(
            tool.input_schema, lambda node, path: self.transform(node, path, ctx)
        )
        if new_schema == tool.input_schema:
            return tool
        return tool.replace(input_schema=new_schema)

    @abstractmethod
    def transform(self, node: dict[str, Any], path: SchemaPath, ctx: RuleContext) -> Any:
        """Rewrite one object subschema. ``node`` is a fresh dict that may be modified.

        Children have already been transformed (post-order). Return the node, or any JSON value
        to replace it.
        """
