"""The rule engine and the shipped rule catalogue (designs C5, C6).

Rules are discovered from modules named ``slNNN_<name>.py`` in this package.
"""

from __future__ import annotations

from toolism.rules.base import OptionSpec, Rule, RuleContext, Safety, SchemaRule, ToolRule
from toolism.rules.registry import (
    all_rules,
    get_rule,
    parse_option_assignment,
    register_rule,
    resolve_options,
)

__all__ = [
    "OptionSpec",
    "Rule",
    "RuleContext",
    "Safety",
    "SchemaRule",
    "ToolRule",
    "all_rules",
    "get_rule",
    "parse_option_assignment",
    "register_rule",
    "resolve_options",
]
