"""Rule registration, discovery, lookup and options (design C5).

Rules live in ``toolslim/rules/slNNN_<name>.py`` and register themselves with
:func:`register_rule`. Adding a rule never requires editing a list.
"""

from __future__ import annotations

import importlib
import pkgutil
import re
from collections.abc import Mapping
from typing import Any, TypeVar

from toolslim.errors import RuleError
from toolslim.rules.base import Rule, Safety

__all__ = [
    "all_rules",
    "get_rule",
    "parse_option_assignment",
    "register_rule",
    "resolve_options",
]

_REGISTRY: dict[str, type[Rule]] = {}
_ID = re.compile(r"^SL[0-9]{3}$")
_NAME = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
_MODULE = re.compile(r"^sl[0-9]{3}_[a-z0-9_]+$")
_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}
_STATE = {"discovered": False}

R = TypeVar("R", bound=type[Rule])


def register_rule(cls: R) -> R:
    """Class decorator that validates a rule's metadata and adds it to the registry."""
    rule_id = getattr(cls, "id", None)
    name = getattr(cls, "name", None)
    if not isinstance(rule_id, str) or not _ID.match(rule_id):
        raise RuleError(f"{cls.__name__}: rule id must look like 'SL001', got {rule_id!r}")
    if not isinstance(name, str) or not _NAME.match(name):
        raise RuleError(f"{rule_id}: rule name must be kebab-case, got {name!r}")
    if not isinstance(getattr(cls, "summary", None), str) or not cls.summary.strip():
        raise RuleError(f"{rule_id}: rule needs a one-line summary")
    safety = getattr(cls, "safety", None)
    if not isinstance(safety, Safety):
        raise RuleError(f"{rule_id}: rule needs a Safety level")
    band = int(rule_id[2])
    if band not in {int(level) for level in Safety}:
        raise RuleError(f"{rule_id}: SL{band}xx is not a defined safety band (use SL0xx-SL2xx)")
    if band != int(safety):
        raise RuleError(
            f"{rule_id}: SL{band}xx ids are reserved for {Safety(band).label!r} rules, "
            f"but this rule declares {safety.label!r}"
        )
    existing = _REGISTRY.get(rule_id)
    if existing is not None and existing is not cls:
        raise RuleError(f"duplicate rule id {rule_id} ({existing.__name__} and {cls.__name__})")
    for other in _REGISTRY.values():
        if other.name == name and other is not cls:
            raise RuleError(f"duplicate rule name {name!r} ({other.id} and {rule_id})")
    for option, spec in cls.option_specs.items():
        if not isinstance(spec.default, spec.type):
            raise RuleError(
                f"{rule_id}: default for option {option!r} is not a {spec.type.__name__}"
            )
    _REGISTRY[rule_id] = cls
    return cls


def _discover() -> None:
    if _STATE["discovered"]:
        return
    package = importlib.import_module("toolslim.rules")
    for info in sorted(pkgutil.iter_modules(package.__path__), key=lambda m: m.name):
        if _MODULE.match(info.name):
            importlib.import_module(f"toolslim.rules.{info.name}")
    _STATE["discovered"] = True


def all_rules() -> tuple[type[Rule], ...]:
    """Every registered rule, sorted by id."""
    _discover()
    return tuple(sorted(_REGISTRY.values(), key=lambda rule: rule.id))


def get_rule(key: str) -> type[Rule]:
    """Look a rule up by id (``SL001``) or name (``redundant-title``), case-insensitively."""
    _discover()
    text = key.strip()
    rule = _REGISTRY.get(text.upper())
    if rule is not None:
        return rule
    for candidate in _REGISTRY.values():
        if candidate.name == text.lower():
            return candidate
    raise RuleError(f"unknown rule {key!r}", hint="run 'toolslim rules' to list rules")


def _coerce(rule: type[Rule], option: str, value: Any, expected: type) -> Any:
    if isinstance(value, str) and expected is not str:
        text = value.strip().lower()
        try:
            if expected is bool:
                if text in _TRUE:
                    return True
                if text in _FALSE:
                    return False
                raise ValueError(value)
            return expected(text)
        except ValueError:
            raise RuleError(
                f"{rule.id}: option {option!r} expects {expected.__name__}, got {value!r}"
            ) from None
    if isinstance(value, bool) and expected is not bool:
        raise RuleError(f"{rule.id}: option {option!r} expects {expected.__name__}, got a bool")
    if expected is float and isinstance(value, int):
        return float(value)
    if not isinstance(value, expected):
        raise RuleError(
            f"{rule.id}: option {option!r} expects {expected.__name__}, got {type(value).__name__}"
        )
    return value


def resolve_options(rule: type[Rule], user: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Defaults overlaid with ``user`` values, validated and coerced to each option's type."""
    resolved = {name: spec.default for name, spec in rule.option_specs.items()}
    for option, value in (user or {}).items():
        spec = rule.option_specs.get(option)
        if spec is None:
            known = ", ".join(sorted(rule.option_specs)) or "none"
            raise RuleError(f"{rule.id} has no option {option!r} (options: {known})")
        resolved[option] = _coerce(rule, option, value, spec.type)
    return resolved


def parse_option_assignment(text: str) -> tuple[str, str, str]:
    """Split ``"SL101.max_chars=200"`` into ``("SL101", "max_chars", "200")``."""
    target, sep, value = text.partition("=")
    rule_key, dot, option = target.strip().partition(".")
    if not sep or not dot or not rule_key or not option:
        raise RuleError(
            f"invalid option {text!r}", hint="use RULE.option=value, e.g. SL101.max_chars=200"
        )
    return rule_key, option.strip(), value.strip()
