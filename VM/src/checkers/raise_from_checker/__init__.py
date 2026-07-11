"""Checker for exception chaining with `from`."""

import tokenize
from typing import List

from checkers._framework import Diagnostic, Severity, add_rule, make_diagnostic
from checkers._support import tokens

RULE = add_rule(Severity.ERROR, "raise from exception chaining", ["raise the original error"])


def check_source(source: str, filename: str = "<string>") -> List[Diagnostic]:
    diagnostics = []
    token_list = tokens(source)
    saw_raise_on_line = False
    for index in range(len(token_list)):
        current = token_list[index]
        if current.type == tokenize.NEWLINE:
            saw_raise_on_line = False
        elif current.type == tokenize.NAME and current.string == "raise":
            saw_raise_on_line = True
        elif (saw_raise_on_line and current.type == tokenize.NAME and
                current.string == "from"):
            diagnostics.append(make_diagnostic(filename, current.start[0], current.start[1] + 1, RULE))
    return diagnostics
