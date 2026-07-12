"""Checker for floor division."""

from typing import List

from checkers._framework import Diagnostic, Severity, add_rule, make_diagnostic
from checkers._support import tokens

RULE = add_rule(
    Severity.ERROR,
    "floor division",
    ["vm_sdk.int_div", "int division"],
)


def check_source(source: str, filename: str = "<string>") -> List[Diagnostic]:
    diagnostics = []
    for token in tokens(source):
        if token.string == "//":
            diagnostics.append(make_diagnostic(filename, token.start[0], token.start[1] + 1, RULE))
    return diagnostics
