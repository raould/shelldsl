"""Shared types and rule registration for source checkers."""

import hashlib
from enum import Enum
from typing import Any, Dict, Tuple


class Severity(Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


RuleId = str
Message = str
Rule = Tuple[RuleId, Severity, Message, list[str]]
Diagnostic = Dict[str, Any]
RULES: Dict[RuleId, Rule] = {}


class RuleRegistrationError(ValueError):
    """Raised when a checker attempts to reuse a rule identifier."""


def rule_id_for_message(message: Message) -> RuleId:
    """Return the stable seven-character SHA-1 identifier for a message."""
    digest = hashlib.sha1(message.encode("utf-8")).hexdigest()
    return digest[:7]


def add_rule(severity: Severity, message: Message, alternatives: list[str]) -> Rule:
    """Register a rule whose identifier is derived from its unique message."""
    for existing_rule in RULES.values():
        if existing_rule[2] == message:
            raise RuleRegistrationError(
                "rule message already registered: %s" % message
            )

    rule_id = rule_id_for_message(message)
    if rule_id in RULES:
        raise RuleRegistrationError("rule id already registered: %s" % rule_id)

    rule = (rule_id, severity, message, alternatives or [])
    RULES[rule_id] = rule
    return rule


def make_diagnostic(
    filename: str,
    line: int,
    column: int,
    rule: Rule,
) -> Diagnostic:
    """Create the common diagnostic representation."""
    return {
        "rule_id": rule[0],
        "severity": rule[1],
        "filename": filename,
        "line": line,
        "column": column,
        "message": rule[2],
        "alternatives": rule[3]
    }


def format_diagnostic(diagnostic: Diagnostic) -> str:
    """Format a diagnostic for command-line output."""
    return "%s:%s:%s: [%s] [%s] disallowed: '%s'. alternatives: %s" % (
        diagnostic["filename"],
        diagnostic["line"],
        diagnostic["column"],
        diagnostic["rule_id"],
        diagnostic["severity"].value,
        diagnostic["message"],
        ",".join(diagnostic["alternatives"]),
    )
