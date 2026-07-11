"""Reject True and False names at the portable boundary."""

import tokenize
from typing import List

from checkers._framework import Diagnostic, Severity, add_rule, make_diagnostic
from checkers._support import tokens

RULE = add_rule(
    Severity.ERROR,
    "True or False constant",
    ["integer 0 or 1"],
)


def check_source(source: str, filename: str = "<string>") -> List[Diagnostic]:
    diagnostics = []
    for token in tokens(source):
        if token.type == tokenize.NAME and token.string in ("True", "False"):
            diagnostics.append(
                make_diagnostic(filename, token.start[0], token.start[1] + 1, RULE)
            )
    return diagnostics
