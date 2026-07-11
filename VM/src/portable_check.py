#!/usr/bin/env python3
"""Minimal source checker for prohibited print usage.

This checker is intentionally small and standalone. It accepts source text
without importing or executing the source under inspection.
"""

import io
import os
import sys
import tokenize
from enum import Enum
from typing import Any, Dict, List, Tuple


class Severity(Enum):
    """Diagnostic severity levels emitted by the checker."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


RuleId = str
Message = str
Rule = Tuple[RuleId, Severity, Message]
Diagnostic = Dict[str, Any]

RULES: Dict[RuleId, Rule] = {}


class RuleRegistrationError(ValueError):
    """Raised when a checker rule cannot be registered."""


def add_rule(rule_id: RuleId, severity: Severity, message: Message) -> Rule:
    """Register a rule and reject every reused rule identifier."""
    if rule_id in RULES:
        raise RuleRegistrationError(
            "rule id already registered: %s" % rule_id
        )
    rule: Rule = (rule_id, severity, message)
    RULES[rule_id] = rule
    return rule


PRINT_RULE: Rule = add_rule(
    "P001",
    Severity.ERROR,
    "prohibited print usage",
)


def make_diagnostic(filename: str, token: Any, rule: Rule = PRINT_RULE) -> Diagnostic:
    """Return one deterministic diagnostic for a print token."""
    return {
        "rule_id": rule[0],
        "severity": rule[1],
        "filename": filename,
        "line": token.start[0],
        "column": token.start[1] + 1,
        "message": rule[2],
    }


def check_print(source: str, filename: str = "<string>") -> List[Diagnostic]:
    """Return P001 diagnostics for print syntax in source text.

    The tokenizer ignores comments and string contents, so source such as
    ``message = "print("`` does not produce a false positive. Both Python 2
    print statements and Python 3-style print calls are reported.
    """
    diagnostics: List[Diagnostic] = []
    reader = io.StringIO(source).readline

    try:
        tokens = tokenize.generate_tokens(reader)
        for token in tokens:
            if token.type == tokenize.NAME and token.string == "print":
                diagnostics.append(make_diagnostic(filename, token))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # Tokenization may fail for incomplete source. Any print tokens found
        # before the failure remain useful and are returned.
        pass

    return diagnostics


def format_diagnostic(diagnostic: Diagnostic) -> str:
    """Format one diagnostic for command-line output."""
    return "%s:%s:%s: %s %s %s" % (
        diagnostic["filename"],
        diagnostic["line"],
        diagnostic["column"],
        diagnostic["rule_id"],
        diagnostic["severity"].value,
        diagnostic["message"],
    )


def check_file(filename: str) -> List[Diagnostic]:
    """Read and check one source file without executing it."""
    handle = open(filename, "r")
    try:
        source = handle.read()
    finally:
        handle.close()
    return check_print(source, filename)


def source_is_portable(source: str, filename: str = "<string>") -> bool:
    """Return whether source has no error-severity print diagnostics."""
    diagnostics = check_print(source, filename)
    for diagnostic in diagnostics:
        if diagnostic["severity"] == Severity.ERROR:
            return False
    return True


def main(arguments: List[str]) -> int:
    """Check files named in arguments and return a process status."""
    if len(arguments) == 0:
        sys.stderr.write("usage: portable_check.py SOURCE...\n")
        return 2

    found_error = 0
    index = 0
    while index < len(arguments):
        filename = arguments[index]
        if not os.path.isfile(filename):
            sys.stderr.write("error: file not found: %s\n" % filename)
            found_error = 1
            index = index + 1
            continue

        diagnostics = check_file(filename)
        for diagnostic in diagnostics:
            sys.stdout.write(format_diagnostic(diagnostic) + "\n")
        if len(diagnostics) != 0:
            found_error = 1
        index = index + 1

    return found_error


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
